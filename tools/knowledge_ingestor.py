from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pathlib import Path
import json

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

def chunk_documents(docs, chunk_size=750, chunk_overlap=100):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " "]
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

if __name__ == "__main__":
    docs = ingest_documents("data/knowledge_base")
    print(f"Loaded {len(docs)} documents")

    chunks = chunk_documents(docs)
    print(f"Split into {len(chunks)} chunks")

    save_chunks(chunks, "data/chunks/chunks.json")
    print("Chunks saved to data/chunks/chunks.json")