"""Parse official FSSAI PDFs and build a local FAISS vector index."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from pypdf import PdfReader

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

def regulation_id_for(filename: str) -> str:
    n = filename.lower().replace("_", " ").replace("-", " ")
    if "advertising" in n or "claims" in n or n.startswith("ac"):
        return "AC2018"
    if "labelling" in n or "labeling" in n or "display" in n or n.startswith("ld"):
        return "LD2020"
    return "OTHER"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def parse_pdfs(input_dir: Path):
    from langchain_core.documents import Document
    docs = []
    pdfs = sorted(input_dir.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDF files found in {input_dir}. Download official FSSAI PDFs first; see docs/regulatory_source_register.csv")
    for pdf in pdfs:
        reader = PdfReader(str(pdf))
        reg_id = regulation_id_for(pdf.name)
        checksum = sha256_file(pdf)
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            if text:
                docs.append(Document(page_content=text, metadata={
                    "source": pdf.name, "page": page_num, "regulation_id": reg_id,
                    "sha256": checksum, "source_type": "official_pdf_needs_version_review"
                }))
    if not docs:
        raise ValueError("PDFs were found, but no text could be extracted. Use OCR on scanned PDFs and re-run ingestion.")
    return docs

def build_index(input_dir: Path, output_dir: Path, chunk_size: int = 900, chunk_overlap: int = 150) -> int:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    from langchain_community.embeddings import HuggingFaceEmbeddings
    pages = parse_pdfs(input_dir)
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, add_start_index=True, separators=["\n\n", "\n", ". ", " ", ""])
    chunks = splitter.split_documents(pages)
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"chunk_{i:06d}"
        # Record a visible clause-like heading when present, but do not treat it as verified legal metadata.
        m = re.search(r"(?im)^\s*((?:regulation|schedule|chapter|section)\s+[\w()./-]+[^\n]{0,100})", chunk.page_content)
        if m:
            chunk.metadata["heading_candidate"] = m.group(1).strip()
    embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME, encode_kwargs={"normalize_embeddings": True})
    vectorstore = FAISS.from_documents(chunks, embeddings)
    output_dir.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(output_dir / "index"))
    manifest = {
        "embedding_model": MODEL_NAME, "pdf_count": len(list(input_dir.glob('*.pdf'))),
        "page_count_with_text": len(pages), "chunk_count": len(chunks),
        "sources": sorted({d.metadata['source'] for d in pages}),
        "warning": "Verify consolidated versions and amendments; extracted heading_candidate is not a verified clause citation."
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return len(chunks)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default="data/raw")
    ap.add_argument("--output-dir", default="data/processed")
    ap.add_argument("--chunk-size", type=int, default=900)
    ap.add_argument("--chunk-overlap", type=int, default=150)
    args = ap.parse_args()
    count = build_index(Path(args.input_dir), Path(args.output_dir), args.chunk_size, args.chunk_overlap)
    print(f"Built FAISS index with {count} chunks. Review data/processed/manifest.json and document versions.")
if __name__ == "__main__": main()
