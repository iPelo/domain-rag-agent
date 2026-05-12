import argparse
from pathlib import Path

import httpx


def download(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as response:
        response.raise_for_status()
        with output_path.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a German law source file.")
    parser.add_argument("url", help="Source URL to download.")
    parser.add_argument("output", type=Path, help="Destination path under data/raw/.")
    args = parser.parse_args()

    download(args.url, args.output)


if __name__ == "__main__":
    main()
