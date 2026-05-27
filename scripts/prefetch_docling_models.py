#!/usr/bin/env python3
"""Prefetch Docling models used by the default PDF parsing pipeline.

This script downloads model artifacts ahead of time so first agent calls do not
block on lazy model downloads.
"""

from __future__ import annotations

import os
import argparse
import inspect
import logging
from pathlib import Path
from dotenv import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prefetch Docling model artifacts for offline usage and faster startup."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Directory for downloaded artifacts. Defaults to Docling cache "
            "(usually ~/.cache/docling/models)."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if artifacts already exist.",
    )
    parser.add_argument(
        "--with-easyocr",
        action="store_true",
        help="Also download EasyOCR models in addition to RapidOCR models.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download all Docling built-in model families (large download).",
    )
    return parser.parse_args()


def _download_models_compat(
    output_dir: Path | None,
    force: bool,
    flags: dict[str, bool],
) -> Path:
    from docling.utils.model_downloader import download_models

    supported = inspect.signature(download_models).parameters
    kwargs = {
        "output_dir": output_dir,
        "force": force,
        "progress": True,
    }

    for key, value in flags.items():
        if key in supported:
            kwargs[key] = value
        elif value:
            logging.info(
                "Skipping unsupported model flag on this Docling version: %s", key
            )

    return download_models(**kwargs)


def _download_default_pdf_models(output_dir: Path | None, force: bool) -> Path:
    return _download_models_compat(
        output_dir=output_dir,
        force=force,
        flags={
            "with_layout": True,
            "with_tableformer": True,
            "with_tableformer_v2": False,
            "with_code_formula": True,
            "with_picture_classifier": True,
            "with_smolvlm": False,
            "with_granitedocling": False,
            "with_granitedocling_mlx": False,
            "with_granitedocling_2stage": False,
            "with_smoldocling": False,
            "with_smoldocling_mlx": False,
            "with_granite_vision": False,
            "with_granite_chart_extraction": False,
            "with_granite_chart_extraction_v4": False,
            "with_rapidocr": True,
            "with_easyocr": False,
        },
    )


def _download_all_models(output_dir: Path | None, force: bool) -> Path:
    return _download_models_compat(
        output_dir=output_dir,
        force=force,
        flags={
            "with_layout": True,
            "with_tableformer": True,
            "with_tableformer_v2": True,
            "with_code_formula": True,
            "with_picture_classifier": True,
            "with_smolvlm": True,
            "with_granitedocling": True,
            "with_granitedocling_mlx": True,
            "with_granitedocling_2stage": True,
            "with_smoldocling": True,
            "with_smoldocling_mlx": True,
            "with_granite_vision": True,
            "with_granite_chart_extraction": True,
            "with_granite_chart_extraction_v4": True,
            "with_rapidocr": True,
            "with_easyocr": True,
        },
    )


def _download_easyocr(output_dir: Path | None, force: bool) -> Path:
    return _download_models_compat(
        output_dir=output_dir,
        force=force,
        flags={
            "with_layout": False,
            "with_tableformer": False,
            "with_tableformer_v2": False,
            "with_code_formula": False,
            "with_picture_classifier": False,
            "with_smolvlm": False,
            "with_granitedocling": False,
            "with_granitedocling_mlx": False,
            "with_granitedocling_2stage": False,
            "with_smoldocling": False,
            "with_smoldocling_mlx": False,
            "with_granite_vision": False,
            "with_granite_chart_extraction": False,
            "with_granite_chart_extraction_v4": False,
            "with_rapidocr": False,
            "with_easyocr": True,
        },
    )


def main() -> int:
    load_dotenv()
    print("HF_API_KEY", os.getenv("HF_API_KEY")[:5])
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        if args.all:
            target_dir = _download_all_models(
                output_dir=args.output_dir,
                force=args.force,
            )
        else:
            target_dir = _download_default_pdf_models(
                output_dir=args.output_dir,
                force=args.force,
            )
            if args.with_easyocr:
                # Trigger EasyOCR artifacts in a second pass without redownloading defaults.
                target_dir = _download_easyocr(
                    output_dir=args.output_dir,
                    force=args.force,
                )
    except ImportError:
        print(
            "Docling is not installed in this environment. Install it first, for example:"
        )
        print("  uv add docling")
        return 1

    print("\nDocling model prefetch complete.")
    print(f"Artifacts directory: {target_dir}")
    print("Use this same environment/cache when running the agent parser.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())