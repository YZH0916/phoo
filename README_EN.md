# Phoo - Keyboard-Driven File Classifier

[中文](README.md) | [日本語](README_JP.md)

> Just press a key and your files are sorted!

Phoo is a Python-based file classification tool. Press keyboard shortcuts to instantly sort images, videos, and Flash files into corresponding folders.

## Features

- **Keyboard-driven sorting**: Customizable hotkeys for instant file classification
- **Multi-format support**: Images (JPG/PNG/GIF/BMP/TIFF/ICO), Videos (MP4/AVI/MOV/WMV/FLV/MKV), Flash (SWF)
- **Copy / Move modes**: Safe copy mode (default) or move mode
- **Video thumbnail preview**: Extract first frame as thumbnail (requires opencv-python)
- **File info display**: Shows file type and shooting date (EXIF > filename parsing > file timestamp)
- **Smart date recognition**: Supports mainstream phone/APP naming formats (IMG_, VID_, Screenshot, mmexport, timestamps, etc.)
- **Undo**: Ctrl+Z to undo, supports multiple undo (session only)
- **Delete**: Delete key to remove current file (with confirmation)
- **Skip**: W key to skip and browse next file
- **Sorting**: By name, date, or size; ascending or descending
- **Subfolder scanning**: Optional recursive scanning
- **Config persistence**: Auto-saves settings between sessions
- **Duplicate protection**: Auto-rename on filename conflicts

## Quick Start

### Requirements

- Python 3.7+
- Windows / macOS / Linux

### Install Dependencies

```bash
pip install pillow pywin32
```

> Optional: Install `opencv-python` for video thumbnail preview
> ```bash
> pip install opencv-python
> ```

### Run

```bash
python phoo.py
```

## Shortcuts

| Shortcut | Action |
|----------|--------|
| `1` `2` `3` ... | Classify file to corresponding folder |
| `W` | Skip to next file |
| `Delete` | Delete current file (with confirmation) |
| `Ctrl+Z` | Undo last action |
| `Tab` | Toggle copy/move mode |

> Shortcuts can be customized in the settings panel.

## Build Standalone EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed phoo.py
```

The EXE file is generated in the `dist/` directory.

## Tech Stack

- Python 3
- Tkinter (GUI)
- Pillow (Image processing + EXIF reading)
- OpenCV (Optional, video thumbnails)

## License

[MIT License](LICENSE)

## Credits

Original project by [RxinnotRstar](https://github.com/RxinnotRstar). Maintained and enhanced by [YZH0916](https://github.com/YZH0916).
