from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pathlib import Path
from typing import List, Dict
import argparse
import json
import os

def ingest_documents(directory: str):
    all_docs = []
    for file in Path(directory).glob("*"):
        if file.suffix == ".pdf":
            reader = PdfReader(str(file))
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            all_docs.append({
                "page_content": text,
                "metadata": {"source": str(file)}
            })
        elif file.suffix in [".md", ".txt"]:
            with open(file, 'r', encoding='utf-8') as f:
                text = f.read()
            all_docs.append({
                "page_content": text,
                "metadata": {"source": str(file)}
            })
    return all_docs


def ingest_files(file_paths: List[Path]) -> List[Dict]:
    docs: List[Dict] = []
    for file in file_paths:
        if file.suffix.lower() == ".pdf":
            reader = PdfReader(str(file))
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            docs.append({
                "page_content": text,
                "metadata": {"source": str(file)}
            })
        elif file.suffix.lower() in [".md", ".txt"]:
            with open(file, 'r', encoding='utf-8') as f:
                text = f.read()
            docs.append({
                "page_content": text,
                "metadata": {"source": str(file)}
            })
    return docs

def chunk_documents(docs, chunk_size=1000, chunk_overlap=200):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    texts = [doc["page_content"] for doc in docs]
    metadatas = [doc["metadata"] for doc in docs]
    chunks = splitter.create_documents(texts, metadatas=metadatas)
    return chunks

def save_chunks(chunks, output_file: str):
    with open(output_file, "w") as f:
        json.dump(
            [{"content": c.page_content, "metadata": c.metadata} for c in chunks],
            f,
            indent=2
        )


def load_existing_sources(chunks_path: str) -> List[str]:
    if not os.path.exists(chunks_path):
        return []
    try:
        with open(chunks_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        sources = []
        for item in data:
            meta = item.get("metadata", {})
            src = meta.get("source")
            if src:
                sources.append(src)
        return list(set(sources))
    except Exception:
        return []


def collect_data_md_files(base_dir: str = "data") -> List[Path]:
    base = Path(base_dir)
    candidates: List[Path] = []
    # Top-level listings
    candidates.extend(base.glob("*.md"))
    # Article markdowns under each source/articles
    for src in ["the_ringer", "action_network", "clutchpoints", "nba_com"]:
        articles_dir = base / src / "articles"
        if articles_dir.exists():
            candidates.extend(articles_dir.glob("*.md"))
    # Knowledge base PDFs/texts
    kb_dir = base / "knowledge_base"
    if kb_dir.exists():
        candidates.extend(kb_dir.glob("*.pdf"))
        candidates.extend(kb_dir.glob("*.md"))
        candidates.extend(kb_dir.glob("*.txt"))
    return candidates

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest and chunk documents")
    parser.add_argument("--from-data", action="store_true", help="Collect appropriate files from data directory (listings, articles, knowledge_base)")
    parser.add_argument("--output", default="data/chunks/chunks.json", help="Output chunks JSON path")
    parser.add_argument("--force", action="store_true", help="Ignore existing chunks and rebuild from scratch")
    args = parser.parse_args()

    output_path = args.output
    existing_sources = [] if args.force else load_existing_sources(output_path)

    if args.from_data:
        file_paths = collect_data_md_files("data")
        # Filter out already-chunked sources
        file_paths = [p for p in file_paths if str(p) not in existing_sources]
        docs = ingest_files(file_paths)
        print(f"Loaded {len(docs)} documents from data")
    else:
        docs = ingest_documents("data/knowledge_base")
        if not args.force:
            # Filter out already-chunked sources
            docs = [d for d in docs if d["metadata"].get("source") not in existing_sources]
        print(f"Loaded {len(docs)} documents from knowledge_base")

    chunks = chunk_documents(docs)
    print(f"Split into {len(chunks)} new chunks")

    # If we are not forcing and file exists, append to existing
    if os.path.exists(output_path) and not args.force:
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []
        merged = existing + [{"content": c.page_content, "metadata": c.metadata} for c in chunks]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)
    else:
        save_chunks(chunks, output_path)

    print(f"Chunks saved to {output_path}")