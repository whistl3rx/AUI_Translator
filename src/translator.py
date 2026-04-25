from __future__ import annotations

import os
import re

import requests

from app_settings import load_app_settings
from config import (
    LIBRETRANSLATE_FORMAT,
    LIBRETRANSLATE_TIMEOUT_SECONDS,
    LIBRETRANSLATE_URL,
)


def _translate_with_libretranslate(text: str, source_language: str, target_language: str) -> str:
    payload = {
        "q": text,
        "source": source_language,
        "target": target_language,
        "format": LIBRETRANSLATE_FORMAT,
    }

    # Opcionális API kulcs (sajat LibreTranslate szervereknel hasznos).
    api_key = os.getenv("LIBRETRANSLATE_API_KEY", "").strip()
    if api_key:
        payload["api_key"] = api_key

    url = LIBRETRANSLATE_URL.strip()
    if not url:
        raise RuntimeError("A LIBRETRANSLATE_URL nincs beallitva.")

    response = _post_translate(url=url, payload=payload, timeout_seconds=LIBRETRANSLATE_TIMEOUT_SECONDS)

    data = response.json()
    translated = str(data.get("translatedText", "")).strip()
    if not translated:
        raise RuntimeError("LibreTranslate ures forditast adott vissza.")
    return translated


def translate_to_hungarian(text: str) -> str:
    if not text.strip():
        return ""
    settings = load_app_settings()
    return _translate_with_libretranslate(
        text=text,
        source_language=settings.source_language,
        target_language=settings.target_language,
    )


def normalize_ocr_text_for_translation(text: str) -> str:
    if not text.strip():
        return ""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = re.split(r"\n\s*\n+", normalized)
    normalized_paragraphs: list[str] = []

    for paragraph in paragraphs:
        lines = [line.strip() for line in paragraph.split("\n") if line.strip()]
        if not lines:
            continue
        normalized_paragraphs.append(_join_wrapped_lines(lines))

    merged_paragraphs = _merge_false_paragraph_breaks(normalized_paragraphs)
    return "\n\n".join(merged_paragraphs).strip()


def _post_translate(url: str, payload: dict, timeout_seconds: int) -> requests.Response:
    response = requests.post(url, json=payload, headers={"Accept": "application/json"}, timeout=timeout_seconds)
    if response.status_code >= 400:
        error_details = response.text.strip() or f"HTTP {response.status_code}"
        raise RuntimeError(f"LibreTranslate hiba: {error_details}")
    return response


def _join_wrapped_lines(lines: list[str]) -> str:
    merged = lines[0]
    for current in lines[1:]:
        previous = merged.rstrip()
        if previous.endswith("-"):
            merged = previous[:-1] + current
        else:
            merged = previous + " " + current

    # OCR jellegu karakter-csere: izolalt "|" gyakran "I" lenne.
    merged = re.sub(r"(?<!\w)\|(?!\w)", "I", merged)
    merged = re.sub(r"\s+", " ", merged).strip()
    return merged


def _merge_false_paragraph_breaks(paragraphs: list[str]) -> list[str]:
    if not paragraphs:
        return []

    result: list[str] = [paragraphs[0]]
    for current in paragraphs[1:]:
        previous = result[-1]
        if _should_merge_paragraphs(previous, current):
            result[-1] = f"{previous.rstrip()} {current.lstrip()}".strip()
        else:
            result.append(current)
    return result


def _should_merge_paragraphs(previous: str, current: str) -> bool:
    prev = previous.strip()
    curr = current.strip()
    if not prev or not curr:
        return False

    # Kulon kezelt blokkok (cim, alairas) maradjanak kulon.
    if curr.startswith("-"):
        return False
    if len(prev.split()) <= 3 and not re.search(r"[.!?…:;]$", prev):
        return False

    # Ha elozo blokk nem zarul mondatvegi irasjellel, nagy esellyel hamis tordeles.
    if not re.search(r"[.!?…:;]$", prev):
        return True

    # Tipikus folytatas kezdo szavak, amik OCR hamis bekezdest jeleznek.
    if re.match(r"^(the|a|an|and|but|or|so|because|if|when|while)\b", curr, re.IGNORECASE):
        return True

    return False
