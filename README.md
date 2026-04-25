# AUI Translator MVP (OCR -> Translation)

Simple in-game translation MVP:

1. Press `F10`
2. Select the on-screen text region
3. Run OCR (Tesseract) on the selected image
4. Normalize wrapped OCR lines into cleaner sentences
5. Translate through LibreTranslate
6. Show the result in a styled PyQt overlay window

## Requirements

- Windows 10/11
- Python 3.10+
- Installed [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
  - Recommended path: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Running LibreTranslate server (local or remote)

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

If Tesseract is not in `PATH`, set:

```bash
set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

Optional LibreTranslate API key (only if your server requires it):

PowerShell:

```bash
$env:LIBRETRANSLATE_API_KEY="your-key"
```

CMD:

```bash
set LIBRETRANSLATE_API_KEY=your-key
```

If you run LibreTranslate locally (for example on `http://127.0.0.1:5000`), API key is usually **not required**.

## First Run Language Setup

On first run (when `config.json` does not exist), the app opens a language picker dialog:

- left list: source language
- right list: target language

The selected `source_language` and `target_language` are saved to `config.json`.

## Runtime Configuration

Main runtime settings are in `src/config.py`:

- `LIBRETRANSLATE_URL` (default: `http://127.0.0.1:5000/translate`)
- `LIBRETRANSLATE_TIMEOUT_SECONDS`
- `AUTO_ELEVATE_TO_ADMIN` (relaunches as admin on Windows for more reliable global hotkeys)

UI/user preferences are persisted to `config.json` next to the app:

- window zoom
- text zoom
- zoom limits
- base text size
- source/target languages
- debug toggles (disabled by default)

## Run (from source)

```bash
python src/main.py
```

If `AUTO_ELEVATE_TO_ADMIN = True` and the app is not elevated, it relaunches with UAC prompt.

The app does **not** start LibreTranslate for you. Run it separately, for example:

```bash
libretranslate --load-only en,hu
```

## Usage

- `F10`: start region selection
- Drag with mouse to select text area
- Translation overlay appears near the selected region
- `Ctrl + Mouse Wheel`: window size zoom
- `Alt + Mouse Wheel`: text size zoom
- `Esc`: exit app

## Notes

- OCR output is cleaned before translation (line-wrap normalization).
- Debug outputs are stored under `debug/...` (configurable), including `ocr_normalized.txt`.

## Debugging (end-user)

By default, debug output is **disabled**. If you need to collect diagnostics:

1. Open `config.json` next to the app
2. Set:

```json
{
  "debug_enabled": true,
  "debug_dir": "debug"
}
```

Then reproduce the issue and share the generated debug folder.
- Styled PyQt overlay is always-on-top and draggable.

## Build (Windows, one-file)

Console-visible one-file build (recommended):

```bash
build_onefile.bat
```

Hidden-console one-file build:

```bash
build_onefile_windowed.bat
```

Output:

- `dist\AUI_Translator.exe`

## Build (Windows, one-dir, faster startup)

For faster startup in personal use:

```bash
build_onedir.bat
```

Output:

- `dist\AUI_Translator\AUI_Translator.exe`
- plus dependency/runtime folders next to it (Qt/runtime libs, etc.)
