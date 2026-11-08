# Japanese OCR: Image, PDF, Receipt & Invoice to Text

[![Run on Apify](https://apify.com/ext/run-on-apify.png)](https://apify.com/mirumiru_miru17/image-pdf-ocr-japanese)

**Run it in the cloud with no setup: [apify.com/mirumiru_miru17/image-pdf-ocr-japanese](https://apify.com/mirumiru_miru17/image-pdf-ocr-japanese)**


Japanese OCR for images, scanned PDFs, receipts and invoices. Turn them into text. Paste direct links to your files and get the **full text**, **text per page** and an **OCR confidence score** for each file, plus a ready-to-download TXT file.

Built for **Japanese documents** (invoices, receipts, business cards, contracts, forms, vertical text) and works with English, Chinese, Korean, German, French and Spanish too.

No API key, no setup. **Pay only per page.**

## What it does

- **Images**: PNG, JPG, WEBP, TIFF, BMP. Photos and screenshots are cleaned up (noise removal, contrast, upscaling of small images) before OCR.
- **PDFs**: in **Auto** mode, pages that already contain text are read exactly from the PDF (fast, no OCR errors). Scanned pages are rendered at 300 DPI and OCR'd.
- **Japanese**: horizontal and **vertical (縦書き)** text. Removes the extra spaces OCR engines put between Japanese characters and fixes `15.000円` → `15,000円`.
- **Confidence score** per page, so you can flag pages that need a human check.

## Use cases

- Invoices and receipts → text for bookkeeping and data entry
- Scanned contracts and forms → searchable text
- Business cards, flyers and screenshots → copyable text
- Bulk OCR of many files in one run, or as a tool for AI agents through the Apify MCP server

## Input

| Field | Description |
| --- | --- |
| `fileUrls` | Direct links to images or PDFs, up to 100 MB each. |
| `language` | `jpn+eng` (default), `jpn`, `eng`, `jpn_vert+jpn` (vertical Japanese), `chi_sim+eng`, `chi_tra+eng`, `kor+eng`, `deu+eng`, `fra+eng`, `spa+eng`. |
| `pdfMode` | `auto` (default) or `ocr` to OCR every page. |
| `maxPagesPerFile` | Pages beyond this are skipped and **not charged** (default 50). |
| `maxFiles` | Safety limit (default 50). |

## Output

One dataset item per file:

```json
{
  "url": "https://example.com/invoice.pdf",
  "type": "pdf",
  "pageCount": 1,
  "averageConfidence": 91.6,
  "text": "請求書\n株式会社さくら商事御中\n請求日 : 2026年11月8日\n...\n合計金額  148,500円",
  "pages": [{ "page": 1, "method": "ocr", "confidence": 91.6, "text": "..." }]
}
```

Each file's text is also saved as `TEXT-1.txt`, `TEXT-2.txt`… in the key-value store.

## Pricing

Pay per page that returns text. Blank pages, skipped pages and files that fail to download are not charged. The Actor respects your maximum cost per run.

## Notes

- Uses Tesseract OCR 5. Accuracy depends on scan quality: clear, straight, 200–300 DPI scans work best. Handwriting is not supported.
- Only process documents you have the right to use.

## More tools from the same author

- [SEO Audit & AI Search Readiness Checker](https://apify.com/mirumiru_miru17/seo-ai-readiness-audit): full-site SEO audit, AI search readiness score and llms.txt generator
- [Bulk PageSpeed & Core Web Vitals Checker](https://apify.com/mirumiru_miru17/page-speed-core-web-vitals): Lighthouse scores, LCP/CLS/TBT and top fixes for a list of URLs
- [Audio & Video to Text Transcriber (Whisper)](https://apify.com/mirumiru_miru17/audio-video-transcriber): transcripts and SRT subtitles in Japanese and 90+ languages

---

## 日本語

画像やスキャンしたPDFから文字を読み取ってテキストにします。請求書・領収書・名刺・契約書などの日本語の書類に強く、縦書きにも対応しています。文字が埋め込まれたPDFはそのまま正確に読み取り、スキャンしたページだけをOCRします。ページごとのテキストと読み取りの信頼度、TXTファイルを出力します。APIキーは不要で、料金は1ページごとの従量課金です。

## License

MIT
