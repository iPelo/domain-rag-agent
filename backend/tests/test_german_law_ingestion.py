from app.ingestion.chunking import chunk_document
from app.ingestion.loaders import load_local_documents
from app.ingestion.models import RawDocument


def test_loads_german_law_markdown_and_chunks_by_legal_heading(tmp_path) -> None:
    law_path = tmp_path / "german-laws" / "g" / "gg" / "index.md"
    law_path.parent.mkdir(parents=True)
    law_path.write_text(
        """---
Title: Grundgesetz fuer
  Deutschland
jurabk: GG
layout: default
origslug: gg
slug: gg

---

# Grundgesetz fuer Deutschland (GG)

Ausfertigungsdatum
:   1949-05-23

## I. - Die Grundrechte

### Art 5

(1) Jeder hat das Recht, seine Meinung frei zu aeussern.
""",
        encoding="utf-8",
    )

    documents = load_local_documents(tmp_path / "german-laws")

    assert len(documents) == 1
    document = documents[0]
    assert document.source_id == "german-laws::gg"
    assert document.title == "Grundgesetz fuer Deutschland (GG)"
    assert document.metadata["law_code"] == "GG"
    assert document.metadata["source_url"] == "https://www.gesetze-im-internet.de/gg/"

    chunks = list(chunk_document(document))

    art_5 = next(chunk for chunk in chunks if chunk.chunk_id == "german-laws::gg::art-5")
    assert art_5.metadata["citation"] == "GG Art 5"
    assert art_5.metadata["hierarchy"] == ["I. - Die Grundrechte", "Art 5"]
    assert art_5.text.startswith("I. - Die Grundrechte > Art 5")


def test_recursive_chunking_keeps_chunks_bounded() -> None:
    document = RawDocument(
        source_id="test",
        title="Test",
        text=(
            "Alpha beta gamma delta. "
            "Dieser lange Satz erzwingt eine neue rekursive Chunk-Grenze. "
            "Omega endet hier."
        ),
        source_path="test.md",
    )

    chunks = list(chunk_document(document, strategy="recursive", chunk_size=48, overlap=12))

    assert chunks
    assert all(len(chunk.text) <= 48 for chunk in chunks)
    assert len({chunk.text for chunk in chunks}) == len(chunks)
