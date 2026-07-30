import argparse
from pathlib import Path

import httpx


# Small helper to fetch a source file over HTTP and stream
# it to disk in chunks (so large downloads don't load
# fully into memory). Creates the parent folder if needed.
def download(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as response:
        response.raise_for_status()
        with output_path.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)


# CLI wrapper: `python scripts/download_german_law.py
# <url> <output>` saves under data/raw/.
def main() -> None:
    parser = argparse.ArgumentParser(description="Download a German law source file.")
    parser.add_argument("url", help="Source URL to download.")
    parser.add_argument("output", type=Path, help="Destination path under data/raw/.")
    args = parser.parse_args()

    download(args.url, args.output)


if __name__ == "__main__":
    main()
