# ──────────────────────────────────────────────────────────────────────────────
# src/main.py    —  CLI / batch entry‑point for *tutorial_generator*
# ──────────────────────────────────────────────────────────────────────────────
"""
Generate a Markdown tutorial from an **HTML** or **PDF** file.

Usage examples
──────────────
▶ python -m src.main ./input_docs/my_tutorial.pdf
▶ python -m src.main ./input_docs/page.html -o ./output/tutorial.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────────────────────
# Environment & logging
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")           # does nothing if the file is absent

logging.basicConfig(
    level=os.getenv("LOGLEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ──────────────────────────────────────────────────────────────────────────────
# Application imports
# ──────────────────────────────────────────────────────────────────────────────
try:
    # The workflow that runs every agent in sequence
    from src.workflows import run_workflow        # noqa: WPS433
except ImportError as exc:                         # pragma: no cover
    logging.critical("Cannot import workflow: %s", exc)
    sys.exit(1)


# =============================================================================
# ─── Helpers ─────────────────────────────────────────────────────────────────
# =============================================================================
def _positive_int(value: str) -> int:
    ivalue = int(value)
    if ivalue <= 0:  # noqa: WPS507
        raise argparse.ArgumentTypeError(f"{value} is not a positive integer")
    return ivalue


# =============================================================================
# ─── Async main coroutine ────────────────────────────────────────────────────
# =============================================================================
async def _async_main(argv: Optional[list[str]] = None) -> None:        # noqa: WPS231
    """
    Parse CLI arguments, launch the tutorial‑generation workflow,
    and print (or save) the resulting Markdown.
    """
    parser = argparse.ArgumentParser(
        prog="tutorial‑generator",
        description="Generate a Markdown tutorial from an HTML / PDF source file "
                    "using Granite / Watson‑x LLMs.",
    )
    parser.add_argument(
        "input",
        help="Path to the source file (HTML or PDF).",
        type=Path,
    )
    parser.add_argument(
        "-o", "--output",
        help="Path where the generated Markdown will be written. "
             "If omitted, the Markdown is printed to stdout.",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Return the full JSON produced by the workflow instead of plain Markdown.",
    )
    args = parser.parse_args(argv)

    input_path: Path = args.input.expanduser().resolve()
    if not input_path.is_file():
        logging.error("Input file not found: %s", input_path)
        sys.exit(2)

    logging.info("Processing %s …", input_path)
    try:
        result: Dict[str, Any] = await run_workflow(str(input_path))
    except Exception:                                                   # noqa: BLE001
        logging.exception("The workflow crashed")
        sys.exit(3)

    # Either entire JSON or just the "markdown" key
    output_text: str
    if args.json:
        output_text = json.dumps(result, indent=4, ensure_ascii=False)
    else:
        output_text = result.get("markdown", "")
        if not output_text:
            logging.warning("No 'markdown' field in workflow result — printing raw JSON.")
            output_text = json.dumps(result, indent=4, ensure_ascii=False)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_text, encoding="utf-8")
        logging.info("Markdown written to %s", args.output)
    else:
        print(output_text)


# =============================================================================
# ─── Module entry‑point for `python -m src.main` ─────────────────────────────
# =============================================================================
def main() -> None:                                      # noqa: D401  (simple wrapper)
    """Synchronous wrapper that launches the async CLI."""
    asyncio.run(_async_main())


if __name__ == "__main__":  # pragma: no cover
    main()
