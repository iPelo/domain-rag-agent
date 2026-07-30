from pathlib import Path

from app.ingestion.models import RawDocument

SUPPORTED_EXTENSIONS = {".html", ".htm", ".xml", ".txt", ".md"}
GERMAN_LAWS_DATASET = "bundestag/gesetze"


# Stage 1 of ingestion: walk the raw data folder and turn each supported
# file into a RawDocument. Receives the raw directory; returns one
# RawDocument per readable file. Special handling: inside the
# german-laws corpus only each law's `index.md` is read (the rest are
# skipped), hidden/dot files are ignored, and empty files are dropped.
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


# Parse one German-law markdown file. Pulls structured fields out of
# the YAML-style frontmatter (jurabk -> law_code like "BGB"; slug ->
# source_url) and uses the first markdown heading as the title. All
# of this lands in metadata for later retrieval + citation.
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


# Split a leading "---"-delimited frontmatter header from the document body. Returns
# (metadata dict, body). If there is no leading "---" block, metadata is empty.
def _split_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, raw

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return _parse_frontmatter(lines[1:index]), "\n".join(lines[index + 1 :])

    return {}, raw


# Turn "key: value" frontmatter lines into a dict. Indented
# continuation lines are appended to the previous key, so a
# value wrapped across two lines is joined back together.
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


# Read a non-markdown file into (text, title). HTML/XML are parsed with
# BeautifulSoup to strip tags; plain text uses its first non-empty line as a rough
# title.
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


# Build a stable id from the file's path relative to the raw dir (slashes ->
# "::"), so the same file always yields the same source_id across rebuilds.
def _source_id(path: Path, raw_dir: Path) -> str:
    relative = path.relative_to(raw_dir)
    return relative.with_suffix("").as_posix().replace("/", "::")
