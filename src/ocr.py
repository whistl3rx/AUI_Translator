from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Dict

import pytesseract
from PIL import Image, ImageOps


@dataclass
class OcrResult:
    text: str


@dataclass
class PreprocessResult:
    final_image: Image.Image
    stages: Dict[str, Image.Image]


def configure_tesseract() -> None:
    custom_cmd = os.getenv("TESSERACT_CMD", "").strip()
    if custom_cmd:
        pytesseract.pytesseract.tesseract_cmd = custom_cmd


def preprocess_image_with_stages(
    image: Image.Image, use_grayscale: bool = True, use_autocontrast: bool = True
) -> PreprocessResult:
    stages: Dict[str, Image.Image] = {"raw": image.copy()}
    processed = image

    if use_grayscale:
        processed = ImageOps.grayscale(processed)
        stages["grayscale"] = processed.copy()

    if use_autocontrast:
        processed = ImageOps.autocontrast(processed)
        stages["autocontrast"] = processed.copy()

    stages["final"] = processed.copy()
    return PreprocessResult(final_image=processed, stages=stages)


def preprocess_image(image: Image.Image, use_grayscale: bool = True, use_autocontrast: bool = True) -> Image.Image:
    return preprocess_image_with_stages(
        image=image,
        use_grayscale=use_grayscale,
        use_autocontrast=use_autocontrast,
    ).final_image


def extract_text(image: Image.Image, lang: str = "eng") -> OcrResult:
    configure_tesseract()
    text = pytesseract.image_to_string(image, lang=lang)
    return OcrResult(text=text.strip())
