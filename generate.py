from pathlib import Path
import sys

# Allow running directly from a fresh checkout as well as after `pip install -e .`.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from content_factory.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
