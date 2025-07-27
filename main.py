import os, re, json
from collections import Counter
from refinedoc.refined_document import RefinedDocument
from pypdf import PdfReader
import fitz

def is_date(text):
    return bool(re.search(r"\b(?:\d{1,2}[-/ ])?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[ ,\-]?\d{2,4}\b", text, re.I)) or \
           bool(re.match(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", text)) or \
           bool(re.match(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", text))

def normalize(text):

    text = re.sub(r"(\b\w{1,3}\b)\s+\1(?:\s+\1)+", r"\1", text)
    # Fix patterns like "quest f quest f quest"
    text = re.sub(r"(\b\w{4,}\b)\s+\w{1,3}\s+\1(?:\s+\w{1,3}\s+\1)+", r"\1", text)
    # Fix patterns like "Request f quest f quest"
    text = re.sub(r"(\b\w{4,}\b)\s+\w{1,3}\s+(\w{4,})(?:\s+\w{1,3}\s+\2)+", r"\1 \2", text)
    
    # Remove any remaining single-letter repetitions with spaces
    text = re.sub(r"(\b\w\b)(?:\s+\1)+", r"\1", text)
    
    # Existing normalization
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\.{2,}", ".", text)
    return text.strip()

def is_valid_text(text):
    if not text or len(text.strip()) < 4:
        return False
    if re.fullmatch(r"\d+(\.\d+)+", text):  # version numbers like 1.0.3
        return False
    if is_date(text):
        return False
    if len(text.split()) <= 1 and len(text.strip()) < 6:
        return False
    
    # Enhanced check for corrupted repeating patterns
    # Check for repeating words with small variations
    words = text.split()
    if len(words) > 3:
        # Check if first few words repeat with small variations
        first_part = " ".join(words[:3])
        if first_part.lower() in " ".join(words[3:6]).lower():
            return False
        # Check for alternating word patterns
        if len(words) > 5 and words[0] == words[2] and words[1] == words[3]:
            return False
    
    # Check for text that looks like corrupted concatenation
    if re.search(r"\b\w{1,3}\s+\w{4,}\s+\w{1,3}\s+\w{4,}\b", text):
        if len(set(text.split())) < len(text.split()) / 2:
            return False
    
    return True

def find_headers_footers(pdf_path):
    reader = PdfReader(pdf_path)
    content = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            if lines:
                content.append(lines)

    if not content or len(content) < 2:
        return set(), set()  # skip header/footer detection if too few pages

    try:
        rd = RefinedDocument(content=content)

        def flatten(pages):
            return {normalize(x).lower() for page in pages for x in page if x.strip()}

        return flatten(rd.headers), flatten(rd.footers)
    except Exception as e:
        print(f"⚠️ RefineDoc failed: {e}")
        return set(), set()

def extract_outline(pdf_path):
    headers, footers = find_headers_footers(pdf_path)
    doc = fitz.open(pdf_path)
    result = {"title": "", "outline": []}
    seen_blocks = set()

    # 1. Built-in TOC
    toc = doc.get_toc()
    if toc:
        result["title"] = doc.metadata.get("title", "")
        for level, title, page in toc:
            result["outline"].append({
                "level": f"H{level}",
                "text": normalize(title),
                "page": page
            })
        return result

    # 2. Collect text spans
    spans = []
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" not in block or not block["lines"]:
                continue

            lines = []
            font_sizes = []
            for line in block["lines"]:
                line_text = " ".join(span["text"] for span in line["spans"]).strip()
                if line_text:
                    lines.append(line_text)
                    sizes = [span.get("size", 0) for span in line["spans"]]
                    if sizes:
                        font_sizes.append(sum(sizes) / len(sizes))

            block_text = normalize(" ".join(lines))
            if not is_valid_text(block_text):
                continue

            key = (block_text.lower(), page.number)
            if key in seen_blocks:
                continue
            seen_blocks.add(key)

            avg_size = round(sum(font_sizes) / len(font_sizes), 1) if font_sizes else 0
            if block_text.lower() in headers or block_text.lower() in footers:
                continue
            if re.search(r"\.{4,}", block_text):
                continue

            spans.append({
                "text": block_text,
                "size": avg_size,
                "page": page.number + 1
            })

    if not spans:
        return result

    # 3. Font size hierarchy
    size_counts = Counter([s["size"] for s in spans])
    body_size = size_counts.most_common(1)[0][0]
    bigger = sorted([s for s in size_counts if s > body_size], reverse=True)
    size_to_level = {sz: f"H{min(i+1, 3)}" for i, sz in enumerate(bigger)}

    # 4. Title: pick biggest valid block from first 2 pages
    candidates = [
        s for s in spans if s["page"] <= 2 and s["size"] in bigger and len(s["text"].split()) >= 3 and not s["text"].isupper()
    ]
    if candidates:
        best = sorted(candidates, key=lambda s: (-s["size"], s["page"]))[0]
        result["title"] = best["text"] + " "

    seen_headings = set()
    for s in spans:
        text, size, page = s["text"], s["size"], s["page"]
        key = text.lower()
        if key in seen_headings:
            continue
        if not is_valid_text(text):
            continue
        if page <= 4 and "contents" in text.lower():
            continue

        level = None
        if size in size_to_level:
            level = size_to_level[size]
        elif re.match(r"^\d+(\.\d+)+\s+", text):
            dots = text.count(".")
            level = f"H{min(dots + 1, 3)}"

        if level:
            seen_headings.add(key)
            result["outline"].append({
                "level": level,
                "text": text,
                "page": page
            })

    return result

def process_all_pdfs(input_dir="input", output_dir="output"):
    os.makedirs(output_dir, exist_ok=True)
    for file in os.listdir(input_dir):
        if file.lower().endswith(".pdf"):
            inp = os.path.join(input_dir, file)
            out = os.path.join(output_dir, file.replace(".pdf", ".json"))
            print(f"📄 Processing {file} …")
            data = extract_outline(inp)
            with open(out, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"✅ Saved: {out}")

if __name__ == "__main__":
    process_all_pdfs("input", "output")
