import os
import uuid
from pathlib import Path
from typing import Dict, List

from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance


# --- Configuration ---
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
QDRANT_COLLECTION_NAME = "sports_knowledge_base"
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
CHUNK_SIZE = 400
CHUNK_OVERLAP = 40

# Prefer detailed mapping; falls back to 0.7 if no match
SOURCE_RELEVANCE: Dict[str, float] = {
    "mathletics": 0.95,
    "the_logic_of_sports_betting": 0.92,
    "the_ringer": 0.88,
    "action_network": 0.85,
    "clutchpoints": 0.8,
    "nba_com": 0.78,
}


# --- Loaders and Embedding Model ---
embedder = SentenceTransformer(EMBED_MODEL_NAME)
qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
)


# --- Create collection if not exists ---
existing = [c.name for c in qdrant.get_collections().collections]
if QDRANT_COLLECTION_NAME not in existing:
    qdrant.recreate_collection(
        collection_name=QDRANT_COLLECTION_NAME,
        vectors_config=VectorParams(
            size=embedder.get_sentence_embedding_dimension(),
            distance=Distance.COSINE,
        ),
    )


def determine_source_name(file_path: Path) -> str:
    """Infer a normalized source name from path.

    - For data/{source}.md, returns {source}
    - For data/{source}/articles/*.md, returns {source}
    - For knowledge_base PDFs, maps common names to keys used in SOURCE_RELEVANCE
    """
    try:
        parts = file_path.parts
        if "data" in parts:
            idx = parts.index("data")
            # data/the_ringer/articles/foo.md → the_ringer
            if len(parts) > idx + 1 and parts[idx + 1] != "knowledge_base":
                return parts[idx + 1].lower().replace(" ", "_")
        # knowledge_base filenames
        stem = file_path.stem.lower()
        candidates = [
            "mathletics",
            "the_logic_of_sports_betting",
            "the_ringer",
            "action_network",
            "clutchpoints",
            "nba_com",
        ]
        for key in candidates:
            if key in stem:
                return key
        return stem
    except Exception:
        return file_path.stem.lower()


def relevance_for_source(source_name: str) -> float:
    for key, value in SOURCE_RELEVANCE.items():
        if key in source_name:
            return value
    return 0.7


# --- Ingest and Embed ---
def process_file(file_path: Path) -> None:
    loader = TextLoader(str(file_path), encoding="utf-8")
    docs = loader.load()
    chunks = text_splitter.split_documents(docs)

    source_name = determine_source_name(file_path)
    relevance = relevance_for_source(source_name)

    points: List[PointStruct] = []
    for i, chunk in enumerate(chunks):
        text = (chunk.page_content or "").strip()
        if not text:
            continue
        vector = embedder.encode(text).tolist()
        metadata = {
            "source": source_name,
            "source_relevance": relevance,
            "filename": file_path.name,
            "chunk_index": i,
            "page": chunk.metadata.get("page"),
            "text": text,
        }
        points.append(PointStruct(id=str(uuid.uuid4()), vector=vector, payload=metadata))

    if points:
        qdrant.upsert(collection_name=QDRANT_COLLECTION_NAME, points=points)
        print(f"✅ {file_path.name} — {len(points)} chunks embedded.")


if __name__ == "__main__":
    data_dir = Path("data")
    # Iterate markdown/text across data, skip large JSON in chunks dir
    for ext in (".md", ".txt"):
        for file in data_dir.rglob(f"*{ext}"):
            if "data/chunks/" in str(file):
                continue
            process_file(file)

    print("✅ Embedding complete.")


