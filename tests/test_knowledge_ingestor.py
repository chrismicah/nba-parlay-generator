import pytest
from tools.knowledge_ingestor import ingest_documents, chunk_documents, save_chunks
from pathlib import Path
import json
import os

def test_ingest_and_chunk():
    # Test document ingestion
    docs = ingest_documents("data/knowledge_base")
    assert len(docs) > 0, "Should load at least one document"
    assert "page_content" in docs[0], "Document should have page_content"

    # Test chunking
    chunks = chunk_documents(docs)
    assert len(chunks) > 0, "Should create at least one chunk"
    assert hasattr(chunks[0], "page_content"), "Chunk should have page_content"

def test_save_chunks(tmp_path):
    # Create test chunks
    docs = ingest_documents("data/knowledge_base")
    chunks = chunk_documents(docs)
    
    # Save chunks to temporary file
    test_output = tmp_path / "test_chunks.json"
    save_chunks(chunks, str(test_output))
    
    # Verify file exists and contains valid JSON
    assert test_output.exists(), "Output file should exist"
    with open(test_output) as f:
        data = json.load(f)
        assert isinstance(data, list), "Should be a list of chunks"
        assert len(data) > 0, "Should have at least one chunk"
        assert "content" in data[0], "Chunk should have content"
        assert "metadata" in data[0], "Chunk should have metadata"