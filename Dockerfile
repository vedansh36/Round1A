# Dockerfile for Round 1A - PDF Outline Extraction
FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /app

COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Entry point script (adjust the file name if needed)
ENTRYPOINT ["python", "main.py"]
