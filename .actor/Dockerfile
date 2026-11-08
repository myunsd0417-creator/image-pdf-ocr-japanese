FROM apify/actor-python:3.12
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-jpn tesseract-ocr-jpn-vert tesseract-ocr-chi-sim tesseract-ocr-chi-tra \
    tesseract-ocr-kor tesseract-ocr-deu tesseract-ocr-fra tesseract-ocr-spa poppler-utils \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./
CMD ["python3", "-m", "src"]
