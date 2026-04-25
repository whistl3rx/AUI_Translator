from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox
from typing import Callable

import requests
from PIL import ImageGrab
from PyQt5.QtCore import QEventLoop, QPoint, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from app_settings import AppSettings, load_app_settings, save_app_settings, settings_file_exists
from config import LIBRETRANSLATE_TIMEOUT_SECONDS, LIBRETRANSLATE_URL


BBox = tuple[int, int, int, int]
LanguageOption = tuple[str, str]


class ZoomableTextEdit(QTextEdit):
    def __init__(self, window_zoom_handler: Callable[[int], None], text_zoom_handler: Callable[[int], None]) -> None:
        super().__init__()
        self._window_zoom_handler = window_zoom_handler
        self._text_zoom_handler = text_zoom_handler

    def wheelEvent(self, event) -> None:  # type: ignore[override]
        delta = _extract_wheel_delta(event)
        if _has_ctrl_modifier(event):
            self._window_zoom_handler(delta)
            event.accept()
            return
        if _has_alt_modifier(event):
            self._text_zoom_handler(delta)
            event.accept()
            return
        super().wheelEvent(event)


class RegionSelector:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        self._bbox: BBox | None = None

    def select_region(self) -> BBox | None:
        overlay = tk.Toplevel(self.root)
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-alpha", 0.25)
        overlay.attributes("-topmost", True)
        overlay.configure(bg="black")
        overlay.title("Jelöld ki a fordítandó területet")

        canvas = tk.Canvas(overlay, cursor="cross", highlightthickness=0, bg="black")
        canvas.pack(fill=tk.BOTH, expand=True)
        overlay.update_idletasks()

        # Tk koordinatak (logikai px) es a screenshot (fizikai px) kozti skala.
        capture_scale_x, capture_scale_y = self._get_capture_scale(overlay)

        start_x = 0
        start_y = 0
        rect = None

        def on_press(event: tk.Event) -> None:
            nonlocal start_x, start_y, rect
            start_x, start_y = event.x, event.y
            rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline="red", width=2)

        def on_drag(event: tk.Event) -> None:
            nonlocal rect
            if rect is not None:
                canvas.coords(rect, start_x, start_y, event.x, event.y)

        def on_release(event: tk.Event) -> None:
            x1, y1 = start_x, start_y
            x2, y2 = event.x, event.y
            left, right = sorted((x1, x2))
            top, bottom = sorted((y1, y2))
            if right - left > 5 and bottom - top > 5:
                scaled_left = int(round(left * capture_scale_x))
                scaled_top = int(round(top * capture_scale_y))
                scaled_right = int(round(right * capture_scale_x))
                scaled_bottom = int(round(bottom * capture_scale_y))
                self._bbox = (scaled_left, scaled_top, scaled_right, scaled_bottom)
            overlay.destroy()

        def cancel(_: tk.Event) -> None:
            self._bbox = None
            overlay.destroy()

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        overlay.bind("<Escape>", cancel)

        overlay.focus_force()
        overlay.grab_set()
        self.root.wait_window(overlay)
        return self._bbox

    @staticmethod
    def _get_capture_scale(overlay: tk.Toplevel) -> tuple[float, float]:
        logical_w = max(overlay.winfo_screenwidth(), 1)
        logical_h = max(overlay.winfo_screenheight(), 1)
        physical_w, physical_h = ImageGrab.grab().size

        scale_x = physical_w / logical_w
        scale_y = physical_h / logical_h
        return scale_x, scale_y

    @staticmethod
    def capture_region(bbox: BBox):
        return ImageGrab.grab(bbox=bbox)


class TranslationOverlayDialog(QDialog):
    def __init__(self, translated_text: str, selected_bbox: BBox | None = None) -> None:
        super().__init__()
        self._settings: AppSettings = load_app_settings()
        self._selected_bbox = selected_bbox
        self._drag_pos: QPoint | None = None
        self._base_width, self._base_height = self._compute_base_size(selected_bbox)
        self._base_text_font_size = self._settings.base_text_font_size
        self._window_zoom_scale = self._settings.window_zoom_scale
        self._min_window_zoom_scale = self._settings.min_window_zoom_scale
        self._max_window_zoom_scale = self._settings.max_window_zoom_scale
        self._text_zoom_scale = self._settings.text_zoom_scale
        self._min_text_zoom_scale = self._settings.min_text_zoom_scale
        self._max_text_zoom_scale = self._settings.max_text_zoom_scale

        self.setWindowTitle("AUI Forditas")
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(self._base_width, self._base_height)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("AUI Translator")
        title.setObjectName("title")
        subtitle = QLabel("Magyar forditas")
        subtitle.setObjectName("subtitle")
        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        close_button = QPushButton("×")
        close_button.setObjectName("closeBtn")
        close_button.setFixedSize(30, 30)
        close_button.clicked.connect(self.close)
        header.addWidget(close_button)
        card_layout.addLayout(header)

        card_layout.addWidget(self._build_section("Magyar forditas:", translated_text or "[Nincs forditas]"))

        root.addWidget(card)

        self.setStyleSheet(
            """
            QDialog { background: transparent; }
            #card {
                background-color: rgba(11, 18, 30, 232);
                border: 1px solid rgba(80, 130, 200, 130);
                border-radius: 14px;
            }
            QLabel#title {
                color: #e8f3ff;
                font-size: 16px;
                font-weight: 700;
            }
            QLabel#subtitle {
                color: #97b5d5;
                font-size: 11px;
            }
            QLabel.sectionTitle {
                color: #d2e6ff;
                font-size: 12px;
                font-weight: 600;
                margin-top: 4px;
            }
            QTextEdit {
                background-color: rgba(8, 14, 22, 215);
                border: 1px solid rgba(85, 130, 195, 85);
                border-radius: 8px;
                color: #f4f8ff;
                font-family: "Segoe UI";
                padding: 8px;
            }
            QScrollBar:vertical {
                background: rgba(10, 18, 30, 200);
                width: 12px;
                margin: 2px 2px 2px 0px;
                border-radius: 6px;
                border: 1px solid rgba(70, 110, 170, 90);
            }
            QScrollBar::handle:vertical {
                background: rgba(90, 145, 220, 185);
                min-height: 28px;
                border-radius: 6px;
                border: 1px solid rgba(155, 200, 255, 120);
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(120, 175, 245, 220);
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                background: transparent;
                border: none;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QScrollBar:horizontal {
                background: rgba(10, 18, 30, 200);
                height: 12px;
                margin: 0px 2px 2px 2px;
                border-radius: 6px;
                border: 1px solid rgba(70, 110, 170, 90);
            }
            QScrollBar::handle:horizontal {
                background: rgba(90, 145, 220, 185);
                min-width: 28px;
                border-radius: 6px;
                border: 1px solid rgba(155, 200, 255, 120);
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(120, 175, 245, 220);
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0px;
                background: transparent;
                border: none;
            }
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: transparent;
            }
            QPushButton#closeBtn {
                border: 1px solid rgba(120, 160, 220, 120);
                border-radius: 15px;
                background-color: rgba(30, 50, 85, 180);
                color: #e8f3ff;
                font-size: 18px;
                font-weight: 600;
            }
            QPushButton#closeBtn:hover {
                background-color: rgba(55, 85, 135, 200);
            }
            """
        )
        self._apply_window_zoom_scale()
        self._apply_text_zoom_scale()
        self._position_near_selected_region()

    def _build_section(self, title_text: str, content: str) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title = QLabel(title_text)
        title.setProperty("class", "sectionTitle")
        editor = ZoomableTextEdit(self._on_ctrl_wheel_zoom, self._on_alt_wheel_zoom)
        editor.setReadOnly(True)
        editor.setPlainText(content)
        editor.setMinimumHeight(max(240, int(self._base_height * 0.58)))
        self._translation_editor = editor

        layout.addWidget(title)
        layout.addWidget(editor)
        return container

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._drag_pos = None
        event.accept()

    def wheelEvent(self, event) -> None:  # type: ignore[override]
        delta = _extract_wheel_delta(event)
        if _has_ctrl_modifier(event):
            self._on_ctrl_wheel_zoom(delta)
            event.accept()
            return
        if _has_alt_modifier(event):
            self._on_alt_wheel_zoom(delta)
            event.accept()
            return
        super().wheelEvent(event)

    def _on_ctrl_wheel_zoom(self, delta_y: int) -> None:
        if delta_y == 0:
            return
        step = 0.1 if delta_y > 0 else -0.1
        next_scale = max(
            self._min_window_zoom_scale,
            min(self._max_window_zoom_scale, self._window_zoom_scale + step),
        )
        if next_scale == self._window_zoom_scale:
            return
        self._window_zoom_scale = next_scale
        self._apply_window_zoom_scale()
        self._persist_settings()

    def _on_alt_wheel_zoom(self, delta_y: int) -> None:
        if delta_y == 0:
            return
        step = 0.1 if delta_y > 0 else -0.1
        next_scale = max(
            self._min_text_zoom_scale,
            min(self._max_text_zoom_scale, self._text_zoom_scale + step),
        )
        if next_scale == self._text_zoom_scale:
            return
        self._text_zoom_scale = next_scale
        self._apply_text_zoom_scale()
        self._persist_settings()

    def _apply_window_zoom_scale(self) -> None:
        new_width = int(self._base_width * self._window_zoom_scale)
        new_height = int(self._base_height * self._window_zoom_scale)
        self.resize(new_width, new_height)

    def _apply_text_zoom_scale(self) -> None:
        if hasattr(self, "_translation_editor"):
            font = QFont("Segoe UI")
            font.setPointSizeF(self._base_text_font_size * self._text_zoom_scale)
            self._translation_editor.setFont(font)

    def _position_near_selected_region(self) -> None:
        if self._selected_bbox is None:
            return

        left, top, right, bottom = self._selected_bbox
        _ = right, bottom  # intentionally unused currently

        # A kijelolt regio fole/korul pozicionaljuk, hogy hasonlo helyen jelenjen meg.
        target_x = left - 14
        target_y = top - 46

        app = QApplication.instance()
        if app is None:
            self.move(max(0, target_x), max(0, target_y))
            return

        desktop = app.desktop()
        screen_index = desktop.screenNumber(QPoint(left, top))
        if screen_index < 0:
            screen_index = desktop.primaryScreen()
        available = desktop.availableGeometry(screen_index)

        clamped_x = max(available.left(), min(target_x, available.right() - self.width()))
        clamped_y = max(available.top(), min(target_y, available.bottom() - self.height()))
        self.move(clamped_x, clamped_y)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._persist_settings()
        super().closeEvent(event)

    def _persist_settings(self) -> None:
        self._settings.window_zoom_scale = self._window_zoom_scale
        self._settings.text_zoom_scale = self._text_zoom_scale
        self._settings.min_window_zoom_scale = self._min_window_zoom_scale
        self._settings.max_window_zoom_scale = self._max_window_zoom_scale
        self._settings.min_text_zoom_scale = self._min_text_zoom_scale
        self._settings.max_text_zoom_scale = self._max_text_zoom_scale
        self._settings.base_text_font_size = self._base_text_font_size
        save_app_settings(self._settings)

    @staticmethod
    def _compute_base_size(selected_bbox: BBox | None) -> tuple[int, int]:
        if selected_bbox is None:
            return 980, 520

        left, top, right, bottom = selected_bbox
        selected_width = max(1, right - left)
        selected_height = max(1, bottom - top)

        # Kicsi rahagyas keretre, fejlec reszre es kenyelmes margora.
        width = int(selected_width * 1.10) + 44
        height = int(selected_height * 1.15) + 120

        width = max(820, min(width, 1900))
        height = max(420, min(height, 1300))
        return width, height


def show_result_window(translated_text: str, selected_bbox: BBox | None = None) -> None:
    app = QApplication.instance()
    created_app = app is None
    if created_app:
        app = QApplication([])

    dialog = TranslationOverlayDialog(translated_text, selected_bbox=selected_bbox)
    dialog.show()

    if created_app:
        app.exec_()
    else:
        loop = QEventLoop()
        dialog.destroyed.connect(loop.quit)
        loop.exec_()


class LanguageSelectionDialog(QDialog):
    def __init__(self, options: list[LanguageOption], current_source: str, current_target: str) -> None:
        super().__init__()
        self.setWindowTitle("Forditasi nyelvek beallitasa")
        self.resize(760, 430)
        self._selected_source = current_source
        self._selected_target = current_target

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        info = QLabel("Valaszd ki a forras- es celnyelvet (elso inditas / config hiany).")
        root.addWidget(info)

        lists_row = QHBoxLayout()
        self._source_list = QListWidget()
        self._target_list = QListWidget()
        self._source_list.setSelectionMode(QListWidget.SingleSelection)
        self._target_list.setSelectionMode(QListWidget.SingleSelection)

        source_box = QVBoxLayout()
        source_box.addWidget(QLabel("Forras nyelv"))
        source_box.addWidget(self._source_list)

        target_box = QVBoxLayout()
        target_box.addWidget(QLabel("Cel nyelv"))
        target_box.addWidget(self._target_list)

        lists_row.addLayout(source_box)
        lists_row.addLayout(target_box)
        root.addLayout(lists_row)

        for code, name in options:
            source_item = QListWidgetItem(f"{name} ({code})")
            source_item.setData(Qt.UserRole, code)
            self._source_list.addItem(source_item)

            target_item = QListWidgetItem(f"{name} ({code})")
            target_item.setData(Qt.UserRole, code)
            self._target_list.addItem(target_item)

        self._select_by_code(self._source_list, current_source or "auto")
        self._select_by_code(self._target_list, current_target or "hu")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept_selection)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @property
    def selected_source(self) -> str:
        return self._selected_source

    @property
    def selected_target(self) -> str:
        return self._selected_target

    def _accept_selection(self) -> None:
        source_item = self._source_list.currentItem()
        target_item = self._target_list.currentItem()
        if source_item is None or target_item is None:
            return

        self._selected_source = str(source_item.data(Qt.UserRole))
        self._selected_target = str(target_item.data(Qt.UserRole))
        self.accept()

    @staticmethod
    def _select_by_code(widget: QListWidget, code: str) -> None:
        for i in range(widget.count()):
            item = widget.item(i)
            if str(item.data(Qt.UserRole)) == code:
                widget.setCurrentRow(i)
                return
        if widget.count() > 0:
            widget.setCurrentRow(0)


def run_in_tk_thread(handler: Callable[[], None]) -> None:
    try:
        handler()
    except Exception as exc:  # pragma: no cover
        # Fallback hibaüzenet GUI környezetben.
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Hiba", str(exc))
        root.destroy()


def start_background_task(handler: Callable[[], None]) -> None:
    thread = threading.Thread(target=lambda: run_in_tk_thread(handler), daemon=True)
    thread.start()


def ensure_language_settings() -> None:
    settings = load_app_settings()
    if settings_file_exists() and settings.source_language and settings.target_language:
        return

    options = _load_language_options()
    app = QApplication.instance()
    created_app = app is None
    if created_app:
        app = QApplication([])

    dialog = LanguageSelectionDialog(options, settings.source_language or "auto", settings.target_language or "hu")
    accepted = dialog.exec_() == QDialog.Accepted

    if not accepted:
        raise RuntimeError("A nyelvbeallitas szukseges a folytatashoz.")

    settings.source_language = dialog.selected_source
    settings.target_language = dialog.selected_target
    save_app_settings(settings)


def _load_language_options() -> list[LanguageOption]:
    endpoint = _languages_endpoint(LIBRETRANSLATE_URL)
    try:
        response = requests.get(endpoint, timeout=LIBRETRANSLATE_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
        options: list[LanguageOption] = []
        for item in data:
            code = str(item.get("code", "")).strip().lower()
            name = str(item.get("name", code)).strip()
            if code:
                options.append((code, name))
        options = sorted(options, key=lambda x: x[1].lower())
        if options:
            if not any(code == "auto" for code, _ in options):
                options.insert(0, ("auto", "Auto-detect"))
            return options
    except Exception:
        pass

    fallback = [
        ("auto", "Auto-detect"),
        ("en", "English"),
        ("hu", "Hungarian"),
        ("de", "German"),
        ("fr", "French"),
        ("es", "Spanish"),
        ("it", "Italian"),
        ("pt", "Portuguese"),
        ("ru", "Russian"),
        ("ja", "Japanese"),
        ("ko", "Korean"),
        ("zh", "Chinese"),
        ("tr", "Turkish"),
        ("pl", "Polish"),
        ("nl", "Dutch"),
    ]
    return fallback


def _languages_endpoint(translate_url: str) -> str:
    url = translate_url.strip()
    if url.endswith("/translate"):
        return url[: -len("/translate")] + "/languages"
    return url.rstrip("/") + "/languages"


def _has_ctrl_modifier(event) -> bool:
    mods = int(event.modifiers())
    app_mods = int(QApplication.keyboardModifiers())
    return bool((mods | app_mods) & int(Qt.ControlModifier))


def _has_alt_modifier(event) -> bool:
    mods = int(event.modifiers())
    app_mods = int(QApplication.keyboardModifiers())
    # AltGr kiosztasoknal a GroupSwitchModifier is erkezhet.
    group_switch = int(getattr(Qt, "GroupSwitchModifier", 0))
    return bool((mods | app_mods) & (int(Qt.AltModifier) | group_switch))


def _extract_wheel_delta(event) -> int:
    delta = event.angleDelta().y()
    if delta == 0:
        delta = event.angleDelta().x()
    if delta == 0:
        delta = event.pixelDelta().y()
    if delta == 0:
        delta = event.pixelDelta().x()
    return delta
