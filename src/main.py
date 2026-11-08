"""Image & PDF OCR (Japanese + English) — Apify Actor.

Extracts text from images and PDFs given as direct URLs using Tesseract OCR.
PDFs with an embedded text layer are read directly (faster, exact); scanned pages are OCR'd.
Charges one "page-processed" event per page that returns text.
"""
import asyncio
import os
import re
import subprocess
import tempfile

import httpx
from apify import Actor
from PIL import Image, ImageFilter, ImageOps

MAX_BYTES = 100 * 1024 * 1024  # 100 MB per file
CJK = r'　-ヿ㐀-䶿一-鿿＀-￯'
LANGS = {'jpn+eng', 'jpn', 'eng', 'jpn_vert+jpn', 'chi_sim+eng', 'chi_tra+eng', 'kor+eng', 'deu+eng', 'fra+eng', 'spa+eng'}


def tidy(text: str) -> str:
    """Remove the spaces Tesseract inserts between CJK characters and trim blank lines."""
    text = re.sub(rf'(?<=[{CJK}]) (?=[{CJK}])', '', text)
    # Yen amounts never have decimals: "15.000円" is a misread comma.
    text = re.sub(r'(\d{1,3})\.(\d{3})(?=円)', r'\1,\2', text)
    lines = [ln.rstrip() for ln in text.splitlines()]
    out, blank = [], 0
    for ln in lines:
        blank = blank + 1 if not ln.strip() else 0
        if blank <= 1:
            out.append(ln)
    return '\n'.join(out).strip()


def preprocess(src: str, dst: str) -> None:
    im = Image.open(src)
    if getattr(im, 'n_frames', 1) > 1:
        im.seek(0)
    im = im.convert('L')
    w, h = im.size
    if max(w, h) < 1000:  # small photos/screenshots: upscale so characters are big enough
        im = im.resize((w * 2, h * 2), Image.LANCZOS)
    im = ImageOps.autocontrast(im.filter(ImageFilter.MedianFilter(3)))
    im.save(dst)


def best_ocr(raw: str, clean: str, lang: str, psm: int) -> tuple[str, float | None]:
    """OCR both the original and the denoised image and keep the more confident result."""
    results = [ocr(clean, lang, psm)]
    try:
        results.append(ocr(raw, lang, psm))
    except subprocess.CalledProcessError:
        pass
    return max(results, key=lambda r: (r[1] or 0))


def ocr(img: str, lang: str, psm: int) -> tuple[str, float | None]:
    base = img + '.out'
    subprocess.run(
        ['tesseract', img, base, '-l', lang, '--psm', str(psm), '-c', 'preserve_interword_spaces=1', 'txt', 'tsv'],
        capture_output=True, check=True,
    )
    text = open(base + '.txt', encoding='utf-8').read()
    confs = []
    for row in open(base + '.tsv', encoding='utf-8').read().splitlines()[1:]:
        parts = row.split('\t')
        if len(parts) >= 12 and parts[11].strip():
            try:
                c = float(parts[10])
                if c >= 0:
                    confs.append(c)
            except ValueError:
                pass
    return tidy(text), (round(sum(confs) / len(confs), 1) if confs else None)


def pdf_page_count(path: str) -> int:
    out = subprocess.run(['pdfinfo', path], capture_output=True, text=True, check=True).stdout
    m = re.search(r'^Pages:\s+(\d+)', out, re.M)
    return int(m.group(1)) if m else 0


def pdf_text(path: str, page: int) -> str:
    r = subprocess.run(['pdftotext', '-layout', '-f', str(page), '-l', str(page), path, '-'], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ''


def pdf_render(path: str, page: int, tmp: str) -> str:
    prefix = os.path.join(tmp, f'p{page}')
    subprocess.run(['pdftoppm', '-r', '300', '-gray', '-png', '-singlefile', '-f', str(page), '-l', str(page), path, prefix],
                   capture_output=True, check=True)
    return prefix + '.png'


async def download(url: str, path: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
        async with client.stream('GET', url, headers={'User-Agent': 'Mozilla/5.0 (Apify Actor OCR)'}) as r:
            r.raise_for_status()
            ctype = r.headers.get('content-type', '')
            size = 0
            with open(path, 'wb') as f:
                async for chunk in r.aiter_bytes(1 << 20):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise ValueError('File is larger than 100 MB')
                    f.write(chunk)
    return ctype


def is_pdf(path: str, ctype: str, url: str) -> bool:
    with open(path, 'rb') as f:
        head = f.read(5)
    return head == b'%PDF-' or 'pdf' in ctype or url.lower().split('?')[0].endswith('.pdf')


async def main() -> None:
    async with Actor:
        inp = await Actor.get_input() or {}
        urls = []
        for u in inp.get('fileUrls') or []:
            u = u.get('url') if isinstance(u, dict) else u
            if isinstance(u, str) and u.strip().lower().startswith(('http://', 'https://')):
                urls.append(u.strip())
        urls = list(dict.fromkeys(urls))[: int(inp.get('maxFiles', 50))]
        lang = inp.get('language') or 'jpn+eng'
        if lang not in LANGS:
            lang = 'jpn+eng'
        psm = 5 if lang.startswith('jpn_vert') else 3
        max_pages = int(inp.get('maxPagesPerFile', 50))
        mode = inp.get('pdfMode') or 'auto'

        if not urls:
            await Actor.fail(status_message='Input "fileUrls" must contain at least one direct link to an image or PDF.')
            return

        cm = Actor.get_charging_manager()
        stop = False
        for idx, url in enumerate(urls, 1):
            if stop:
                break
            with tempfile.TemporaryDirectory() as tmp:
                src = os.path.join(tmp, 'file')
                try:
                    Actor.log.info(f'Downloading {url}')
                    ctype = await download(url, src)
                    pages = []
                    if is_pdf(src, ctype, url):
                        n = min(pdf_page_count(src), max_pages)
                        targets = [(p, 'pdf') for p in range(1, n + 1)]
                    else:
                        targets = [(1, 'image')]
                    for page, kind in targets:
                        allowed = cm.calculate_max_event_charge_count_within_limit('page-processed')
                        if allowed is not None and allowed < 1:
                            Actor.log.info('Spending limit reached — stopping.')
                            stop = True
                            break
                        method, conf = 'ocr', None
                        if kind == 'pdf':
                            embedded = pdf_text(src, page) if mode == 'auto' else ''
                            if len(embedded.strip()) >= 20:
                                text, method = tidy(embedded), 'embedded-text'
                            else:
                                img = await asyncio.to_thread(pdf_render, src, page, tmp)
                                clean = img + '.clean.png'
                                await asyncio.to_thread(preprocess, img, clean)
                                text, conf = await asyncio.to_thread(best_ocr, img, clean, lang, psm)
                        else:
                            clean = src + '.clean.png'
                            await asyncio.to_thread(preprocess, src, clean)
                            raw = src + '.png'
                            await asyncio.to_thread(lambda: Image.open(src).convert('L').save(raw))
                            text, conf = await asyncio.to_thread(best_ocr, raw, clean, lang, psm)
                        if text.strip():
                            await Actor.charge(event_name='page-processed')
                        pages.append({'page': page, 'method': method, 'confidence': conf, 'text': text})
                    full = '\n\n'.join(p['text'] for p in pages if p['text'])
                    confs = [p['confidence'] for p in pages if p['confidence'] is not None]
                    await Actor.set_value(f'TEXT-{idx}.txt', full, content_type='text/plain; charset=utf-8')
                    await Actor.push_data({
                        'url': url,
                        'type': 'pdf' if targets and targets[0][1] == 'pdf' else 'image',
                        'language': lang,
                        'pageCount': len(pages),
                        'chargedPages': sum(1 for p in pages if p['text'].strip()),
                        'averageConfidence': round(sum(confs) / len(confs), 1) if confs else None,
                        'text': full,
                        'pages': pages,
                        'textKey': f'TEXT-{idx}.txt',
                        'error': None,
                    })
                except Exception as e:  # continue with the next file
                    Actor.log.warning(f'Failed: {url} — {e}')
                    await Actor.push_data({'url': url, 'error': str(e)})
