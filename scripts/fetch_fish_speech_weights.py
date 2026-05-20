"""Download the fish-speech model checkpoint into the project's data dir.

Idempotent: ``huggingface_hub.snapshot_download`` caches and only fetches
files that are missing or have changed. Safe to re-run.

Default target:
    ~/.local/share/ai-network/tts/checkpoints/s2-pro

Override with --target. Override the HF repo with --repo if you want a
different model variant.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

logger = logging.getLogger(__name__)


def _ai_network_home() -> Path:
    xdg = os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(xdg) / "ai-network"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--repo", default="fishaudio/s2-pro",
        help="HuggingFace repo id (default: fishaudio/s2-pro)",
    )
    parser.add_argument(
        "--target", type=Path, default=None,
        help="Local target dir (default: <ainet home>/tts/checkpoints/<model>)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    target = args.target or _ai_network_home() / "tts" / "checkpoints" / args.repo.split("/")[-1]
    target.mkdir(parents=True, exist_ok=True)

    logger.info("Fetching %s → %s", args.repo, target)
    snapshot_download(repo_id=args.repo, local_dir=str(target))
    logger.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
