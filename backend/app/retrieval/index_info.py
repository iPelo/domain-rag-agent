"""Which corpus subset the runtime index was built from."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Laws indexed by `make index`; `make index-all` indexes the whole corpus.
CURATED_LAW_SLUGS: frozenset[str] = frozenset(
    {
        "gg",
        "bgb",
        "stgb",
        "stpo",
        "zpo",
        "hgb",
        "ao_1977",
        "owig_1968",
        "gmbhg",
        "aktg",
        "estg",
        "ustg_1980",
        "arbgg",
        "betrvg",
        "kschg",
        "bdsg_2018",
        "vwvfg",
        "vwgo",
        "gvg",
        "urhg",
        "patg",
        "tvg",
        "stvg",
        "inso",
        "bbg_2009",
        "bbaug",
        "sgb_1",
        "sgb_2",
        "sgb_3",
        "sgb_5",
    }
)


def manifest_path(chunks_path: Path) -> Path:
    return chunks_path.with_name(f"{chunks_path.stem}.manifest.json")


def write_manifest(chunks_path: Path, manifest: dict[str, Any]) -> Path:
    path = manifest_path(chunks_path)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def describe_index(chunks_path: Path) -> dict[str, Any]:
    """Summarize the runtime chunk file and the scope it was built with.

    The scope comes from the manifest written by build_index.py. For older
    indexes without one, it is inferred from the law slugs in the chunk file.
    """
    slugs: set[str] = set()
    chunk_count = 0
    with chunks_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            chunk_count += 1
            slug = json.loads(line).get("metadata", {}).get("slug")
            if slug:
                slugs.add(str(slug))

    info: dict[str, Any] = {
        "chunks_path": str(chunks_path),
        "chunk_count": chunk_count,
        "law_count": len(slugs),
    }
    path = manifest_path(chunks_path)
    if path.exists():
        manifest = json.loads(path.read_text(encoding="utf-8"))
        info["scope"] = manifest.get("scope", "unknown")
        info["scope_source"] = "manifest"
        info["manifest"] = manifest
    else:
        info["scope"] = infer_scope(slugs)
        info["scope_source"] = "inferred from law slugs"
    return info


def infer_scope(slugs: set[str]) -> str:
    if slugs and slugs <= CURATED_LAW_SLUGS:
        return "curated" if slugs == CURATED_LAW_SLUGS else "curated (partial)"
    return "all"
