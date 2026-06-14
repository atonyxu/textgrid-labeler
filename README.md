# TextGrid Labeler

A cross-platform GUI tool for viewing and annotating [Praat](https://www.fon.hum.uva.nl/praat/) TextGrid files alongside waveform audio. Built with Python + Tkinter.

## Features

| Feature | Description |
|---|---|
| **Open TextGrid** | Load `.TextGrid` files; auto-detects and loads the same-name `.wav` in the same directory |
| **Open WAV** | Load a waveform separately |
| **Save / Save As** | Save edits back to the standard Praat-format TextGrid file |
| **Layer selector** | Switch between multiple tiers (IntervalTier / TextTier) |
| **Search** | Find labels in the current tier; navigate results with ◀ ▶ buttons |
| **Annotation bar** | Yellow bold labels between timeline markers; search results highlighted |
| **Waveform display** | True-amplitude waveform rendering (not artificially boosted) |
| **Time ruler** | Tick marks with seconds display above the waveform |
| **Scrollbar** | Navigate long audio; default view is 5 seconds |
| **Zoom / Scroll** | Mouse wheel to scroll, Ctrl+wheel to zoom (centered on cursor) |
| **Right-click play** | Right-click an interval to play that segment (no external player window) |
| **Playback cursor** | Green vertical line sweeps through the waveform during playback |
| **Drag boundaries** | Left-click and drag red annotation lines to adjust time boundaries |
| **Double-click to add** | Double-click inside an interval → dialog for label → new boundary created |
| **Edit label** | Double-click a label in the annotation bar to edit its text |

## Requirements

- Python 3.8+
- [numpy](https://pypi.org/project/numpy/)
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
python run.py
```

### Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Open TextGrid |
| `Ctrl+W` | Open WAV |
| `Ctrl+S` | Save TextGrid |
| `Ctrl+Shift+S` | Save as New TextGrid |

### Mouse interactions

| Action | Result |
|---|---|
| Left-click near a red line | Start dragging the boundary |
| Drag a red line | Move the annotation boundary (constrained by neighbours) |
| Right-click in an interval | Play that audio segment |
| Double-click in an interval | Prompt for label → add new boundary |
| Double-click a label | Edit the label text |
| Mouse wheel | Scroll waveform |
| Ctrl + mouse wheel | Zoom in / out (centred on cursor) |

## File format

TextGrid files are written in the standard Praat short-text format (UTF-8), compatible with Praat and other tools that read TextGrid files.

## Platform notes

- **Windows**: audio playback uses `winsound` (built-in), no external player window
- **macOS**: playback uses `afplay` (built-in)
- **Linux**: playback uses `paplay`, `aplay`, or `ffplay` (whichever is available)
