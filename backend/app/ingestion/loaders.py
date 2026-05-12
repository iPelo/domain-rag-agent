from pathlib import Path

from app.ingestion.models import RawDocument


SUPPORTED_EXTENSIONS = {".html", ".htm", ".xml", ".txt", ".md"}
GERMAN_LAWS_DATASET = "bundestag/gesetze"


def load_local_documents(raw_dir: Path) -> list[RawDocument]:
    documents: list[RawDocument] = []
    for path in sorted(raw_dir.rglob("*")):
        if _should_skip_path(path):
            continue
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if _is_inside_german_laws_repo(path) and path.name != "index.md":
            continue

        if path.name == "index.md":
            document = _read_german_law_markdown(path, raw_dir)
        else:
            text, title = _read_text(path)
            document = RawDocument(
                source_id=_source_id(path, raw_dir),
                title=title or path.stem,
                text=text,
                source_path=str(path),
                metadata={
                    "file_name": path.name,
                    "extension": path.suffix.lower(),
                    "source_path": str(path),
                },
            )

        if not document.text.strip():
            continue
        documents.append(document)
    return documents


def _read_german_law_markdown(path: Path, raw_dir: Path) -> RawDocument:
    raw = path.read_text(encoding="utf-8", errors="replace")
    frontmatter, body = _split_frontmatter(raw)
    title = _first_markdown_heading(body) or frontmatter.get("Title") or path.parent.name
    slug = frontmatter.get("slug") or frontmatter.get("origslug") or path.parent.name
    law_code = frontmatter.get("jurabk") or slug.upper()

    return RawDocument(
        source_id=f"german-laws::{slug}",
        title=title,
        text=body.strip(),
        source_path=str(path),
        metadata={
            "dataset": GERMAN_LAWS_DATASET,
            "format": "markdown",
            "file_name": path.name,
            "extension": path.suffix.lower(),
            "source_path": str(path),
            "source_url": f"https://www.gesetze-im-internet.de/{slug}/",
            "law_code": law_code,
            "slug": slug,
            "origslug": frontmatter.get("origslug", slug),
        },
    )


def _split_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, raw

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return _parse_frontmatter(lines[1:index]), "\n".join(lines[index + 1 :])

    return {}, raw


def _parse_frontmatter(lines: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    current_key: str | None = None
    for line in lines:
        if line.startswith((" ", "\t")) and current_key:
            metadata[current_key] = f"{metadata[current_key]} {line.strip()}".strip()
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", maxsplit=1)
        current_key = key.strip()
        metadata[current_key] = value.strip()
    return metadata


def _first_markdown_heading(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _should_skip_path(path: Path) -> bool:
    return any(part.startswith(".") and part != "." for part in path.parts)


def _is_inside_german_laws_repo(path: Path) -> bool:
    return "german-laws" in path.parts


def _read_text(path: Path) -> tuple[str, str | None]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in {".html", ".htm", ".xml"}:
        from bs4 import BeautifulSoup

        parser = "xml" if path.suffix.lower() == ".xml" else "lxml"
        soup = BeautifulSoup(raw, parser)
        title = soup.title.get_text(" ", strip=True) if soup.title else None
        return soup.get_text("\n", strip=True), title
    first_line = next((line.strip() for line in raw.splitlines() if line.strip()), None)
    return raw, first_line


def _source_id(path: Path, raw_dir: Path) -> str:
    relative = path.relative_to(raw_dir)
    return relative.with_suffix("").as_posix().replace("/", "::")
