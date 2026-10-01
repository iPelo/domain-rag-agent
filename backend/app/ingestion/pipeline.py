import json
from pathlib import Path

from app.ingestion.chunking import chunk_document
from app.ingestion.loaders import load_local_documents
from app.ingestion.models import DocumentChunk, RawDocument


def build_processed_corpus(
    raw_dir: Path,
    *,
    chunks_output_path: Path,
    documents_output_path: Path,
    limit: int | None = None,
) -> tuple[int, int]:
    chunks_output_path.parent.mkdir(parents=True, exist_ok=True)
    documents_output_path.parent.mkdir(parents=True, exist_ok=True)

    documents = load_local_documents(raw_dir)
    if limit is not None:
        documents = documents[:limit]

    chunk_count = 0
    with (
        documents_output_path.open("w", encoding="utf-8") as documents_handle,
        chunks_output_path.open("w", encoding="utf-8") as chunks_handle,
    ):
        for document in documents:
            documents_handle.write(
                json.dumps(_document_to_json(document), ensure_ascii=False) + "\n"
            )
            for chunk in chunk_document(document):
                chunks_handle.write(json.dumps(_chunk_to_json(chunk), ensure_ascii=False) + "\n")
                chunk_count += 1

    return len(documents), chunk_count


def build_processed_chunks(raw_dir: Path, output_path: Path) -> int:
    _, chunk_count = build_processed_corpus(
        raw_dir,
        chunks_output_path=output_path,
        documents_output_path=output_path.parent / "documents.jsonl",
    )
    return chunk_count


def _document_to_json(document: RawDocument) -> dict[str, object]:
    return {
        "source_id": document.source_id,
        "title": document.title,
        "source_path": document.source_path,
        "metadata": document.metadata,
    }


def _chunk_to_json(chunk: DocumentChunk) -> dict[str, object]:
    return {
        "chunk_id": chunk.chunk_id,
        "source_id": chunk.source_id,
        "title": chunk.title,
        "text": chunk.text,
        "start_char": chunk.start_char,
        "end_char": chunk.end_char,
        "metadata": chunk.metadata,
    }
