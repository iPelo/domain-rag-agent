"""Law slugs included in the smaller development index."""

from __future__ import annotations

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


def is_curated_slug(slug: str | None) -> bool:
    return slug is not None and slug in CURATED_LAW_SLUGS
