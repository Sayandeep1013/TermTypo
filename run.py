"""Launch TermTypo from the project root — adds client/ to path automatically."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "client"))

from termtypo.__main__ import main

if __name__ == "__main__":
    main()
