"""Curated subset of major German federal codes used for the development index.

Embedding the full 178k-chunk corpus with `bge-m3` is a ~1h job. For day-to-day
work we index ~30 of the most-cited federal codes instead: this still covers the
hand-test queries and the eval golden set, embeds in minutes, and uses the exact
same code path as a full build (`build_index.py --all`).
"""

from __future__ import annotations

# A hand-picked allow-list of the most-cited German codes.
# build_index.py uses it to index a small "curated" subset by default,
# so the dev index builds in minutes, not ~1h. The full corpus is only
# indexed when you pass --all (same code path, just no filter).
# Keyed by `slug` as it appears in `data/raw/german-laws/<letter>/<slug>/index.md`.
CURATED_LAW_SLUGS: frozenset[str] = frozenset(
    {
        "gg",  # Grundgesetz
        "bgb",  # Bürgerliches Gesetzbuch
        "stgb",  # Strafgesetzbuch
        "stpo",  # Strafprozessordnung
        "zpo",  # Zivilprozessordnung
        "hgb",  # Handelsgesetzbuch
        "ao_1977",  # Abgabenordnung
        "owig_1968",  # Ordnungswidrigkeitengesetz
        "gmbhg",  # GmbH-Gesetz
        "aktg",  # Aktiengesetz
        "estg",  # Einkommensteuergesetz
        "ustg_1980",  # Umsatzsteuergesetz
        "arbgg",  # Arbeitsgerichtsgesetz
        "betrvg",  # Betriebsverfassungsgesetz
        "kschg",  # Kündigungsschutzgesetz
        "bdsg_2018",  # Bundesdatenschutzgesetz
        "vwvfg",  # Verwaltungsverfahrensgesetz
        "vwgo",  # Verwaltungsgerichtsordnung
        "gvg",  # Gerichtsverfassungsgesetz
        "urhg",  # Urheberrechtsgesetz
        "patg",  # Patentgesetz
        "tvg",  # Tarifvertragsgesetz
        "stvg",  # Straßenverkehrsgesetz
        "inso",  # Insolvenzordnung
        "bbg_2009",  # Bundesbeamtengesetz
        "bbaug",  # Bundesbaugesetz
        "sgb_1",  # Sozialgesetzbuch I
        "sgb_2",  # Sozialgesetzbuch II
        "sgb_3",  # Sozialgesetzbuch III
        "sgb_5",  # Sozialgesetzbuch V
    }
)


# True if a chunk's `slug` is in the allow-list
# — used to filter the corpus to curated codes.
def is_curated_slug(slug: str | None) -> bool:
    return slug is not None and slug in CURATED_LAW_SLUGS
