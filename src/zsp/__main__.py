"""Enables `python -m zsp`."""

import sys

from .cli.interface import main

if __name__ == "__main__":
    sys.exit(main())
