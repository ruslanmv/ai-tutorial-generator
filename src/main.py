# src/main.py
# ──────────────────────────────────────────────────────────────────────────────
"""
CLI entrypoint for the Tutorial Generator.

Usage:
  python -m src.main input_docs/my_tutorial.pdf                        # prints Markdown
  python -m src.main input_docs/another_article.html -o tutorial.md    # save to file
  python -m src.main input_docs/my_tutorial.pdf --json                 # full JSON payload
  python -m src.main https://en.wikipedia.org/wiki/Quantum_harmonic_oscillator
"""
import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

import requests

from src.workflows import run_workflow


def fetch_to_temp(source: str) -> Path:
    """
    Download a remote URL to a temporary file (PDF or HTML).
    Returns a Path to the downloaded file.
    """
    resp = requests.get(source)
    resp.raise_for_status()

    # Determine file type
    content_type = resp.headers.get("Content-Type", "").lower()
    if source.lower().endswith(".pdf") or "application/pdf" in content_type:
        suffix = ".pdf"
        mode = "wb"
        data = resp.content
    else:
        suffix = ".html"
        mode = "w"
        data = resp.text

    # Write to temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode=mode)
    tmp.write(data)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


async def process(source: str, output: Path | None, as_json: bool) -> None:
    """
    Download (if URL) or verify local path, run the workflow,
    and print or save results.
    """
    # Prepare input path
    if source.startswith(("http://", "https://")):
        path = fetch_to_temp(source)
    else:
        path = Path(source).expanduser().resolve()
        if not path.is_file():
            print(f"Error: file not found: {path}", file=sys.stderr)
            sys.exit(1)

    # Run workflow
    try:
        result = await run_workflow(str(path))
    except Exception as e:
        print(f"Workflow error: {e}", file=sys.stderr)
        sys.exit(1)

    # Output
    if as_json:
        print(json.dumps(result, indent=2))
    else:
        md = result.get("markdown", "")
        if output:
            try:
                output_path = Path(output)
                output_path.write_text(md, encoding="utf-8")
                print(f"Markdown written to {output_path}")
            except Exception as e:
                print(f"Failed to write file: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(md)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a tutorial from a local PDF/HTML file or a URL."
    )
    parser.add_argument(
        "source",
        help="Path to a PDF/HTML file or URL of a webpage",
    )
    parser.add_argument(
        "-o", "--output",
        help="File path to write markdown output",
        metavar="FILE"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON payload instead of just markdown"
    )
    args = parser.parse_args()

    try:
        asyncio.run(process(args.source, args.output, args.json))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
