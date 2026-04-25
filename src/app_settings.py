from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AppSettings:
    window_zoom_scale: float = 1.0
    text_zoom_scale: float = 1.0
    min_window_zoom_scale: float = 0.6
    max_window_zoom_scale: float = 1.8
    min_text_zoom_scale: float = 0.6
    max_text_zoom_scale: float = 2.2
    base_text_font_size: float = 25.0
    source_language: str = "auto"
    target_language: str = "hu"
    debug_enabled: bool = False
    debug_dir: str = "debug"


def load_app_settings() -> AppSettings:
    path = _settings_path()
    if not path.exists():
        return AppSettings()

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return AppSettings()

    settings = AppSettings(
        window_zoom_scale=float(raw.get("window_zoom_scale", 1.0)),
        text_zoom_scale=float(raw.get("text_zoom_scale", 1.0)),
        min_window_zoom_scale=float(raw.get("min_window_zoom_scale", 0.6)),
        max_window_zoom_scale=float(raw.get("max_window_zoom_scale", 1.8)),
        min_text_zoom_scale=float(raw.get("min_text_zoom_scale", 0.6)),
        max_text_zoom_scale=float(raw.get("max_text_zoom_scale", 2.2)),
        base_text_font_size=float(raw.get("base_text_font_size", 25.0)),
        source_language=str(raw.get("source_language", "auto")).strip().lower() or "auto",
        target_language=str(raw.get("target_language", "hu")).strip().lower() or "hu",
        debug_enabled=bool(raw.get("debug_enabled", False)),
        debug_dir=str(raw.get("debug_dir", "debug")).strip() or "debug",
    )
    _clamp_settings(settings)
    return settings


def save_app_settings(settings: AppSettings) -> None:
    _clamp_settings(settings)
    path = _settings_path()
    path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")


def settings_file_exists() -> bool:
    return _settings_path().exists()


def _settings_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "config.json"
    return Path(__file__).resolve().parent.parent / "config.json"


def _clamp_settings(settings: AppSettings) -> None:
    if settings.max_window_zoom_scale < settings.min_window_zoom_scale:
        settings.max_window_zoom_scale = settings.min_window_zoom_scale
    if settings.max_text_zoom_scale < settings.min_text_zoom_scale:
        settings.max_text_zoom_scale = settings.min_text_zoom_scale

    settings.window_zoom_scale = _clamp(
        settings.window_zoom_scale,
        settings.min_window_zoom_scale,
        settings.max_window_zoom_scale,
    )
    settings.text_zoom_scale = _clamp(
        settings.text_zoom_scale,
        settings.min_text_zoom_scale,
        settings.max_text_zoom_scale,
    )
    settings.base_text_font_size = max(8.0, settings.base_text_font_size)
    settings.source_language = (settings.source_language or "auto").strip().lower()
    settings.target_language = (settings.target_language or "hu").strip().lower()
    settings.debug_enabled = bool(settings.debug_enabled)
    settings.debug_dir = (settings.debug_dir or "debug").strip()


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
