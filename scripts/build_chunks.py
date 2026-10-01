import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))


def main() -> None:
    from app.ingestion.pipeline import build_processed_corpus

    parser = argparse.ArgumentParser(description="Build processed chunks from raw documents.")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--chunks-output", type=Path, default=Path("data/processed/chunks.jsonl"))
    parser.add_argument(
        "--documents-output",
        type=Path,
        default=Path("data/processed/documents.jsonl"),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit documents for a quick smoke test.",
    )
    args = parser.parse_args()

    document_count, chunk_count = build_processed_corpus(
        args.raw_dir,
        chunks_output_path=args.chunks_output,
        documents_output_path=args.documents_output,
        limit=args.limit,
    )
    print(f"Wrote {document_count} documents to {args.documents_output}")
    print(f"Wrote {chunk_count} chunks to {args.chunks_output}")


if __name__ == "__main__":
    main()
