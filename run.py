import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from textgrid_labeler import TextGridLabeler


if __name__ == "__main__":
    app = TextGridLabeler()
    app.run()
