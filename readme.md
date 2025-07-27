# 📄 Round 1A – PDF Outline Extractor

This repository contains our submission for **Round 1A** of the Adobe India Hackathon – *Connecting the Dots*.  
The task is to extract a structured outline from a given PDF including the **Title**, **H1**, **H2**, and **H3** headings, along with their respective page numbers, in a clean JSON format.

---

## 🧠 Problem Statement

Given a PDF (up to 50 pages), extract the following structure:
- **Title** of the document
- **Headings** (H1, H2, H3) with:
  - `level` (H1/H2/H3)
  - `text` (heading content)
  - `page` (page number)

The output should strictly follow the provided JSON format and should be produced quickly, with minimal model size and no internet access.

---

## ✅ Features

- Extracts `Title`, `H1`, `H2`, `H3` headings
- Outputs valid hierarchical JSON
- Works offline (no internet access)
- CPU-only, small model size (<200MB)
- Compatible with Docker on `linux/amd64`
- Processes PDF within 10 seconds (up to 50 pages)

---

## 📦 Dependencies

All dependencies are listed in `requirements.txt`:

```txt
PyMuPDF==1.23.19
pypdf==4.1.0
refinedoc==1.0.0

```
## 📁 Folder Structure

```plaintext
Round1A/
├── input/                    # Folder containing input PDFs
│   └── sample.pdf
├── output/                   # Folder where JSON outputs are saved
│   └── sample.json
├── main.py                   # Main script to run heading extraction
├── Dockerfile                # Docker configuration file
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation (this file)
