import sys
import os

if not getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from textgrid_labeler import TextGridLabeler


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else ""
    app = TextGridLabeler(filepath=path)
    app.run()
