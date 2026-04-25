from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict

from PIL import Image


def create_debug_session_dir(base_dir: str = "debug") -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    session_dir = Path(base_dir) / ts
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def save_image_stages(session_dir: Path, stages: Dict[str, Image.Image]) -> None:
    for stage_name, img in stages.items():
        safe_name = stage_name.replace(" ", "_").lower()
        file_path = session_dir / f"{safe_name}.png"
        img.save(file_path)


def save_text_outputs(
    session_dir: Path,
    ocr_text: str,
    translated_text: str,
    normalized_ocr_text: str = "",
) -> None:
    (session_dir / "ocr.txt").write_text(ocr_text or "", encoding="utf-8")
    (session_dir / "ocr_normalized.txt").write_text(normalized_ocr_text or "", encoding="utf-8")
    (session_dir / "translated_hu.txt").write_text(translated_text or "", encoding="utf-8")
