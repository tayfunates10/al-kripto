"""Safe configuration diagnostics entry point."""

from __future__ import annotations

import json

from al_kripto.config import load_settings


def main() -> None:
    """Print only redacted configuration information."""

    print(json.dumps(load_settings().redacted(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
