from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

import keyboard

from app_settings import load_app_settings
from config import AUTO_ELEVATE_TO_ADMIN, HOTKEY, TESSERACT_LANG, USE_AUTOCONTRAST, USE_GRAYSCALE
from debug_io import create_debug_session_dir, save_image_stages, save_text_outputs
from elevation import ensure_admin_or_relaunch, is_admin, is_windows
from ocr import extract_text, preprocess_image_with_stages
from translator import normalize_ocr_text_for_translation, translate_to_hungarian
from ui import RegionSelector, ensure_language_settings, show_result_window, start_background_task


@dataclass
class AppState:
    last_hash: str | None = None
    last_translated_text: str = ""
    last_bbox: tuple[int, int, int, int] | None = None


state = AppState()


def _image_hash(png_bytes: bytes) -> str:
    return hashlib.sha1(png_bytes).hexdigest()


def process_capture() -> None:
    selector = RegionSelector()
    bbox = selector.select_region()
    if not bbox:
        return

    image = selector.capture_region(bbox)
    with_bytes = image.tobytes()
    current_hash = _image_hash(with_bytes)

    if state.last_hash == current_hash:
        show_result_window(state.last_translated_text, state.last_bbox)
        return

    preprocess_result = preprocess_image_with_stages(
        image,
        use_grayscale=USE_GRAYSCALE,
        use_autocontrast=USE_AUTOCONTRAST,
    )
    ocr_result = extract_text(preprocess_result.final_image, lang=TESSERACT_LANG)
    normalized_text = normalize_ocr_text_for_translation(ocr_result.text)
    translated = translate_to_hungarian(normalized_text)

    settings = load_app_settings()
    if settings.debug_enabled:
        session_dir = create_debug_session_dir(settings.debug_dir)
        save_image_stages(session_dir, preprocess_result.stages)
        save_text_outputs(session_dir, ocr_result.text, translated, normalized_text)

    state.last_hash = current_hash
    state.last_translated_text = translated
    state.last_bbox = bbox

    show_result_window(translated, bbox)


def on_hotkey() -> None:
    start_background_task(process_capture)


def main() -> None:
    if not ensure_admin_or_relaunch():
        return

    ensure_language_settings()

    if is_windows() and AUTO_ELEVATE_TO_ADMIN:
        print(f"Admin mode: {'yes' if is_admin() else 'no'}")
    print(f"AUI Translator started. Hotkey: {HOTKEY}")
    print("Press F10 to select a region. Press ESC (in this terminal) or Ctrl+C to quit.")
    keyboard.add_hotkey(HOTKEY, on_hotkey, suppress=False)
    if is_windows():
        # ESC should only quit when the terminal has focus (non-global).
        import msvcrt

        try:
            while True:
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    if ch == "\x1b":  # ESC
                        break
                time.sleep(0.05)
        except KeyboardInterrupt:
            pass
        return

    # Fallback for non-Windows: quit only via Ctrl+C.
    try:
        while True:
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
