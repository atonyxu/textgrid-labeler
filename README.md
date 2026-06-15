# TextGrid Labeler

A cross-platform GUI tool for viewing and annotating [Praat](https://www.fon.hum.uva.nl/praat/) TextGrid files alongside waveform audio. Built with Python + Tkinter.

## Features

| Feature | Description |
|---|---|
| **Open TextGrid** | Load `.TextGrid` files; auto-detects and loads same-name `.wav` in the same / parent / sibling `wav/` directory |
| **New TextGrid** | Create a new file from a template or with default words/phones tiers |
| **New from Current** | Clone the current file's tier structure with empty labels |
| **Save / Save As** | Save edits back to standard Praat-format TextGrid |
| **Undo / Redo** | Full undo/redo history (Ctrl+Z / Ctrl+Y) |
| **Recent Files** | Persistent list of recently opened files |
| **Project menu** | Quick-switch between all `.TextGrid` files in the current file's directory |
| **Layer selector** | Switch between multiple tiers (IntervalTier / TextTier) |
| **Search** | Enter a keyword, press Enter to find matching labels (substring); navigate with ◀ ▶ buttons; results highlighted in waveform and annotation bar |
| **Annotation list** | Right-side panel shows all intervals (Label / Start / Dur); click to jump and highlight |
| **Annotation bar** | Colored intervals with bold labels between timeline markers; search/selection highlighted |
| **Waveform display** | True-amplitude waveform rendering with dB ruler (right side) |
| **Time ruler** | Tick marks with seconds display above the waveform |
| **Scrollbar** | Navigate long audio; default view is 5 seconds |
| **Zoom / Scroll** | Mouse wheel to scroll, Ctrl+wheel to zoom (centered on cursor) |
| **Right-click play** | Right-click an interval to play that segment; playback cursor sweeps through waveform |
| **Drag boundaries** | Left-click and drag red annotation lines to adjust time boundaries |
| **Delete boundary** | Double-click a red boundary line to delete it and merge adjacent intervals |
| **Add boundary** | Double-click inside an interval → dialog for label → new boundary created |
| **Edit label** | Double-click a label in the annotation bar to edit its text |

## Requirements

- Python 3.8+
- [librosa](https://pypi.org/project/librosa/) (audio loading with high-precision float32)
- [soundfile](https://pypi.org/project/soundfile/) (audio read/write via libsndfile)
- [textgrid](https://pypi.org/project/textgrid/) (official Praat-TextGrid library)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Via package module
python -m textgrid_labeler

# Or directly via run script
python run.py path/to/file.TextGrid
```

You can also pass a `.TextGrid` file path as a command-line argument to open it directly.

### Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+N` | New TextGrid |
| `Ctrl+Shift+N` | New from Current |
| `Ctrl+O` | Open TextGrid |
| `Ctrl+W` | Open WAV |
| `Ctrl+S` | Save TextGrid |
| `Ctrl+Shift+S` | Save as New TextGrid |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |

### Mouse interactions

| Action | Result |
|---|---|
| Left-click near a red line | Start dragging the boundary |
| Drag a red line | Move the annotation boundary (constrained by neighbours) |
| Double-click a red line | Delete boundary and merge intervals (keeps left label) |
| Double-click inside an interval | Prompt for label → add new boundary |
| Double-click a label in annotation bar | Edit the label text |
| Right-click in an interval | Play that audio segment |
| Click an item in the annotation list | Jump to and highlight that interval |
| Mouse wheel | Scroll waveform |
| Ctrl + mouse wheel | Zoom in / out (centered on cursor) |

## Project structure

```
textgrid-labeler/
├── run.py                          # Entry point
├── pyproject.toml                  # Package metadata
├── template.TextGrid               # Template for New TextGrid
├── src/
│   └── textgrid_labeler/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py                  # Main class (combines all mixins)
│       ├── ui.py                   # Menu, toolbar, canvases, annotation list
│       ├── file_ops.py             # Open / save / recent files / new file
│       ├── view.py                 # Data loading, layer switching, list population
│       ├── drawing.py              # Waveform, annotation bar, ruler, dB scale
│       ├── events.py               # Mouse/keyboard events, drag, undo/redo
│       ├── search.py               # Search, navigation, result display
│       ├── playback.py             # Audio playback cursor
│       ├── audio.py                # WAV loading, playback
│       └── HELP.txt                # User guide (shown via Help menu)
```

## File format

TextGrid files are written in the standard Praat short-text format (UTF-8), compatible with Praat and other tools that read TextGrid files.

## Platform notes

- **Windows**: audio playback uses `winsound` (built-in)
- **macOS**: playback uses `afplay` (built-in)
- **Linux**: playback uses `paplay`, `aplay`, or `ffplay`

## Build

Pre-built executables for Windows, macOS, and Linux can be built with PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --paths src --name "TextGrid-Labeler" run.py
```

See `.github/workflows/build.yml` for the CI configuration that builds all four platforms (win-x86_64, macos-arm64, linux-x86_64, linux-arm64).
