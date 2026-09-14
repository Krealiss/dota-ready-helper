# -*- coding: utf-8 -*-
"""Майстер калібрування: зняти мірки кнопок з клієнта користувача."""
from pathlib import Path
from typing import List, Optional

import numpy as np
from PIL import Image, ImageDraw
from PyQt6.QtCore import QPoint, QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QVBoxLayout, QWidget
)

import dota_window
from calibration import Calibration
from config import ASSETS_DIR, CONFIDENCE
from dota_window import WindowInfo
from image_recognition import Box, find_green_button, find_template
from logger import logger

# Діапазон масштабів автопошуку зі специфікації
SCALES = [round(0.5 + 0.1 * i, 1) for i in range(16)]

# Кадр темніший за це значення вважається порожнім
BLANK_THRESHOLD = 8

# Кандидати, що перетинаються більше ніж наполовину, вважаються одним елементом
OVERLAP_LIMIT = 0.5

SHIPPED = {
    "search_btn": ["search_game.png"],
    "searching": ["is_searching_game.png"],
    "stop": ["stop.png"],
    "accept": ["prinyat.png"],
}

def shipped_templates(name: str) -> List[Path]:
    """Наші готові шаблони для елемента — лише як підказка в майстрі."""
    return [ASSETS_DIR / file for file in SHIPPED.get(name, [])
            if (ASSETS_DIR / file).exists()]

def is_blank(frame: Image.Image) -> bool:
    """Чи знімок майже повністю чорний (ексклюзивний повноекранний режим)."""
    return float(np.array(frame.convert("L")).mean()) < BLANK_THRESHOLD

def _overlaps(first: Box, second: Box) -> bool:
    """Чи два прямокутники описують той самий елемент."""
    dx = min(first.left + first.width, second.left + second.width) - max(first.left, second.left)
    dy = min(first.top + first.height, second.top + second.height) - max(first.top, second.top)
    if dx <= 0 or dy <= 0:
        return False

    smaller = min(first.width * first.height, second.width * second.height)
    return (dx * dy) / smaller > OVERLAP_LIMIT

def _match_score(needle, haystack):
    """Кореляція шаблону з кадром: (оцінка, (x, y) лівого верхнього кута)."""
    import cv2

    needle_gray = cv2.cvtColor(np.array(needle.convert("RGB")), cv2.COLOR_RGB2GRAY)
    haystack_gray = cv2.cvtColor(np.array(haystack.convert("RGB")), cv2.COLOR_RGB2GRAY)
    result = cv2.matchTemplate(haystack_gray, needle_gray, cv2.TM_CCOEFF_NORMED)
    _, score, _, location = cv2.minMaxLoc(result)
    return float(score), location

def detect_candidates(frame: Image.Image, templates: List[Path],
                      confidence: Optional[float] = None) -> List[Box]:
    """
    Знайти на кадрі місця, схожі на кнопку.

    Шаблони перебираються в діапазоні масштабів, бо розмір інтерфейсу
    користувача заздалегідь невідомий. Кандидати ранжуються за кореляцією
    та дедублюються по перекриттю.
    """
    conf = confidence if confidence is not None else 0.7
    candidates: List[tuple[float, Box]] = []

    for template in templates:
        try:
            with Image.open(template) as original:
                needle = original.convert("RGB")
        except Exception as e:
            logger.debug(f"Не вдалося прочитати шаблон {template}: {e}")
            continue

        for scale in SCALES:
            size = (max(1, round(needle.width * scale)),
                    max(1, round(needle.height * scale)))
            if size[0] > frame.width or size[1] > frame.height:
                continue

            resized = needle.resize(size, Image.LANCZOS)
            try:
                score, (x, y) = _match_score(resized, frame)
            except Exception as e:
                logger.debug(f"Помилка обчислення кореляції для шаблону {template} на масштабі {scale}: {e}")
                continue

            if score >= conf:
                candidates.append((score, Box(x, y, size[0], size[1])))

    # Сортувати за оцінкою у спаданні та дедублювати перекриваючі кандидати
    candidates.sort(key=lambda x: x[0], reverse=True)
    found: List[Box] = []
    for score, box in candidates:
        if not any(_overlaps(box, existing) for existing in found):
            found.append(box)

    return found

def detect_accept(frame: Image.Image) -> Optional[Box]:
    """Кнопку 'Прийняти' шукаємо за кольором — вона не залежить від мови."""
    return find_green_button(frame)

# --- Вікно майстра ----------------------------------------------------------

CAPTURE_HOTKEY = "F10"

# Найменша рамка, яку вважаємо кнопкою
MIN_SELECTION = 10

# Поріг впевненості для автопідказки в майстрі. Нижчий за звичайний (0.7,
# використовується під час роботи бота): готовий шаблон тут — лише орієнтир
# для рамки, яку користувач підтверджує очима, а не самостійне рішення.
AUTO_DETECT_CONFIDENCE = 0.45

class CropLabel(QLabel):
    """Знімок вікна з можливістю виділити кнопку рамкою."""

    def __init__(self):
        super().__init__()
        self.frame: Optional[Image.Image] = None
        self.ratio = 1.0
        self._start: Optional[QPoint] = None
        self._current: Optional[QPoint] = None
        self.highlight: Optional[tuple] = None

    def set_frame(self, frame: Image.Image, display_width: int = 960):
        """Показати кадр, зменшений до display_width."""
        self.frame = frame
        self.ratio = frame.width / display_width
        height = round(frame.height / self.ratio)

        image = QImage(frame.convert("RGB").tobytes(), frame.width, frame.height,
                       frame.width * 3, QImage.Format.Format_RGB888)
        self.setPixmap(QPixmap.fromImage(image).scaled(display_width, height,
                                                       Qt.AspectRatioMode.KeepAspectRatio))
        self.setFixedSize(display_width, height)

    def begin_selection(self, point: QPoint):
        self._start = point
        self._current = point

    def update_selection(self, point: QPoint):
        self._current = point
        self.update()

    def finish_selection(self, point: QPoint) -> Optional[tuple]:
        """Повернути виділене у координатах справжнього кадру."""
        if self._start is None:
            return None

        left, top = min(self._start.x(), point.x()), min(self._start.y(), point.y())
        width, height = abs(point.x() - self._start.x()), abs(point.y() - self._start.y())
        self._start = self._current = None

        if width < MIN_SELECTION or height < MIN_SELECTION:
            return None

        return (round(left * self.ratio), round(top * self.ratio),
                round(width * self.ratio), round(height * self.ratio))

    def mousePressEvent(self, event):
        self.begin_selection(event.pos())

    def mouseMoveEvent(self, event):
        self.update_selection(event.pos())

    def mouseReleaseEvent(self, event):
        rect = self.finish_selection(event.pos())
        if rect:
            self.highlight = rect
            self.selected(rect)

    def selected(self, rect):
        """Перевизначається діалогом."""

    def paintEvent(self, event):
        super().paintEvent(event)
        if not (self._start and self._current):
            return

        painter = QPainter(self)
        painter.setPen(QPen(Qt.GlobalColor.red, 2))
        painter.drawRect(QRect(self._start, self._current))

class _WizardDialog(QDialog):
    """
    Майстер калібрування кнопок.

    Крок 0: очікування вікна Dota 2 (перевірка кожні 2 секунди).
    Крок 1: знімок головного меню за F10 → автопідказка або ручна рамка
            для search_btn.
    Крок 4: другий знімок — searching і stop знімаються з ОДНОГО кадру
            (обидва видно на екрані активного пошуку одночасно).
    Крок 5: зведення, «Перевірити зараз» на живому екрані, «Пропустити».
    """

    # Порядок елементів, що знімаються. "stop" навмисно йде відразу за
    # "searching" без нового знімка — обидва видно на тому самому кадрі.
    STEPS = ["search_btn", "searching", "stop"]

    CAPTURE_PROMPTS = {
        "search_btn": "Перемкнись у Dota, відкрий головне меню і натисни {key}.",
        "searching": "Перемкнись у Dota, запусти пошук гри і натисни {key} ще раз.",
    }

    ELEMENT_QUESTIONS = {
        "search_btn": "Це кнопка пошуку гри?",
        "searching": "Це індикатор активного пошуку матчу?",
        "stop": "Це кнопка відміни (скасування) пошуку?",
    }

    # Сигнал потрібен, бо F10 ловиться у чужому потоці бібліотеки keyboard —
    # напряму чіпати віджети звідти не можна, а emit() з іншого потоку
    # Qt сам поставить у чергу подій головного потоку.
    _capture_signal = pyqtSignal()

    def __init__(self, store: Calibration):
        super().__init__()
        self.store = store
        self.saved = False

        self.window: Optional[WindowInfo] = None
        self.frame: Optional[Image.Image] = None
        self._current_name: Optional[str] = None
        self._step_index = 0
        self._pending_box: Optional[Box] = None
        self._pending_source = "auto"
        self._candidates: List[Box] = []
        self._awaiting_action: Optional[str] = None
        self._hotkey_handle = None

        self._wait_timer = QTimer(self)
        self._wait_timer.timeout.connect(self._check_window)

        self._build_ui()
        self._capture_signal.connect(self._on_hotkey)
        self.finished.connect(lambda _result: self._release_hotkey())

        self._register_hotkey()
        self._check_window()

    # --- Побудова інтерфейсу --------------------------------------------

    def _build_ui(self):
        self.setWindowTitle("Dota Ready Helper — калібрування")
        self.setMinimumWidth(760)

        layout = QVBoxLayout(self)

        self.status = QLabel("Шукаю вікно Dota 2...")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.crop_label = CropLabel()
        self.crop_label.selected = self._on_manual_rect
        layout.addWidget(self.crop_label)

        self.preview_label = QLabel()
        self.preview_label.setFixedHeight(90)
        layout.addWidget(self.preview_label)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.hide()
        layout.addWidget(self.summary_label)

        self._candidates_row = QHBoxLayout()
        self.candidates_box = QWidget()
        self.candidates_box.setLayout(self._candidates_row)
        self.candidates_box.hide()
        layout.addWidget(self.candidates_box)

        buttons = QHBoxLayout()

        self.confirm_btn = QPushButton("Так")
        self.confirm_btn.clicked.connect(self.confirm_candidate)
        self.confirm_btn.setVisible(False)

        self.manual_btn = QPushButton("Виділю сам")
        self.manual_btn.clicked.connect(self._start_manual_selection)
        self.manual_btn.setVisible(False)

        self.check_btn = QPushButton("Перевірити зараз")
        self.check_btn.clicked.connect(self._request_check)
        self.check_btn.setVisible(False)

        self.save_btn = QPushButton("Зберегти")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self.save_and_close)
        self.save_btn.setVisible(False)

        self.skip_btn = QPushButton("Пропустити")
        self.skip_btn.clicked.connect(self._skip)

        buttons.addWidget(self.confirm_btn)
        buttons.addWidget(self.manual_btn)
        buttons.addWidget(self.check_btn)
        buttons.addStretch()
        buttons.addWidget(self.skip_btn)
        buttons.addWidget(self.save_btn)
        layout.addLayout(buttons)

    def _set_status(self, text: str):
        self.status.setText(text)

    # --- Гаряча клавіша ---------------------------------------------------

    def _register_hotkey(self):
        """Зареєструвати глобальний F10. Невдача не має валити майстер."""
        try:
            import keyboard
            self._hotkey_handle = keyboard.add_hotkey(
                CAPTURE_HOTKEY, self._capture_signal.emit
            )
        except Exception as e:
            self._hotkey_handle = None
            logger.warning(
                f"Глобальна клавіша {CAPTURE_HOTKEY} недоступна ({e}) — "
                "користуйся кнопками в майстрі."
            )

    def _release_hotkey(self):
        """Зняти гарячу клавішу — інакше F10 лишиться зайнятим після закриття."""
        if self._hotkey_handle is None:
            return
        try:
            import keyboard
            keyboard.remove_hotkey(self._hotkey_handle)
        except Exception as e:
            logger.debug(f"Не вдалося зняти гарячу клавішу {CAPTURE_HOTKEY}: {e}")
        finally:
            self._hotkey_handle = None

    def _on_hotkey(self):
        """F10: або зняти кадр для поточного кроку, або виконати перевірку."""
        if not self._awaiting_action:
            return

        action, _, name = self._awaiting_action.partition(":")
        if action == "check":
            self._run_check()
        elif action == "capture" and name:
            self.capture_step(name)

    # --- Крок 0: очікування вікна ------------------------------------------

    def _check_window(self):
        window = dota_window.find_window()
        if dota_window.is_usable(window):
            self.window = window
            if self._wait_timer.isActive():
                self._wait_timer.stop()
            if self._step_index < len(self.STEPS):
                self._prompt_capture(self.STEPS[self._step_index])
            return

        self._set_status("Запусти Dota 2 — перевіряю появу вікна кожні 2 секунди...")
        if not self._wait_timer.isActive():
            self._wait_timer.start(2000)

    def _prompt_capture(self, name: str):
        """Показати підказку «натисни F10» для наступного елемента."""
        self._current_name = name
        self._awaiting_action = f"capture:{name}"

        template = self.CAPTURE_PROMPTS.get(
            name, "Натисни {key} у грі, коли будеш готовий."
        )
        self._set_status(template.format(key=CAPTURE_HOTKEY))

        self.crop_label.clear()
        self.preview_label.clear()
        self.confirm_btn.setVisible(False)
        self.manual_btn.setVisible(False)
        self.candidates_box.hide()

    # --- Крок 1/4: знімок і автопідказка ------------------------------------

    def capture_step(self, name: str):
        """
        Зняти вікно Dota і запустити автопідказку для елемента name.

        Викликається обробником F10, а також напряму — саме ця точка входу
        описана в контракті тестів потоку майстра.
        """
        self._awaiting_action = None
        self.window = dota_window.find_window()
        if not dota_window.is_usable(self.window):
            self._set_status("Вікно Dota не знайдено або згорнуте — перемкнись у гру.")
            return

        frame = dota_window.capture(self.window)
        if is_blank(frame):
            self._set_status(
                "Знімок вийшов чорним — Dota, схоже, в ексклюзивному "
                "повноекранному режимі. Перемкни гру у віконний режим без "
                f"рамки і натисни {CAPTURE_HOTKEY} ще раз."
            )
            return

        self.frame = frame
        self._current_name = name
        self._show_frame()
        self._auto_detect(name)
        self._bring_to_front()

    def _bring_to_front(self):
        self.raise_()
        self.activateWindow()

    def _show_frame(self, box: Optional[Box] = None):
        """
        Показати поточний кадр у CropLabel.

        CropLabel сам не малює self.highlight (лише рамку активного
        перетягування), тому підсвітка кандидата вижигається на копії
        зображення заздалегідь — self.frame лишається чистим для вирізання.
        """
        display = self.frame.copy()
        if box is not None:
            draw = ImageDraw.Draw(display)
            width = max(2, box.height // 30)
            draw.rectangle(
                [box.left, box.top, box.left + box.width, box.top + box.height],
                outline=(255, 0, 0), width=width
            )
        self.crop_label.set_frame(display)

    def _auto_detect(self, name: str):
        templates = shipped_templates(name)
        self._candidates = (
            detect_candidates(self.frame, templates, confidence=AUTO_DETECT_CONFIDENCE)
            if templates else []
        )

        if len(self._candidates) == 1:
            self._offer_candidate(self._candidates[0])
        elif len(self._candidates) > 1:
            self._offer_candidates_list(self._candidates)
        else:
            self._start_manual_selection()

    def _offer_candidate(self, box: Box):
        self._pending_box = box
        self._pending_source = "auto"
        self._show_frame(box)
        self.candidates_box.hide()
        self.preview_label.clear()

        question = self.ELEMENT_QUESTIONS.get(self._current_name, "Це потрібний елемент?")
        self._set_status(f"{question} [Так] / [Виділю сам]")
        self.confirm_btn.setVisible(True)
        self.manual_btn.setVisible(True)

    def _offer_candidates_list(self, candidates: List[Box]):
        self._pending_box = None

        display = self.frame.copy()
        draw = ImageDraw.Draw(display)
        for i, box in enumerate(candidates, start=1):
            draw.rectangle(
                [box.left, box.top, box.left + box.width, box.top + box.height],
                outline=(255, 0, 0), width=3
            )
            draw.text((box.left, max(0, box.top - 18)), str(i), fill=(255, 255, 0))
        self.crop_label.set_frame(display)

        while self._candidates_row.count():
            item = self._candidates_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i in range(len(candidates)):
            button = QPushButton(f"Кандидат {i + 1}")
            button.clicked.connect(lambda _checked=False, idx=i: self._select_candidate(idx))
            self._candidates_row.addWidget(button)

        self.candidates_box.show()
        self.confirm_btn.setVisible(False)
        self.manual_btn.setVisible(True)

        question = self.ELEMENT_QUESTIONS.get(self._current_name, "потрібний елемент")
        self._set_status(
            f"Знайдено кілька варіантів. Обери, де {question.lower()}, "
            "або виділи сам."
        )

    def _select_candidate(self, index: int):
        self.candidates_box.hide()
        self._pending_box = self._candidates[index]
        self._pending_source = "auto"
        self.confirm_candidate()

    def _start_manual_selection(self):
        self._pending_box = None
        self._pending_source = "manual"
        self.candidates_box.hide()
        self._show_frame()
        self.preview_label.clear()
        self.confirm_btn.setVisible(False)
        self.manual_btn.setVisible(False)

        question = self.ELEMENT_QUESTIONS.get(self._current_name, "потрібний елемент")
        self._set_status(f"Автопошук не впорався. Виділи мишею: {question.lower()}")

    def _on_manual_rect(self, rect: tuple):
        """Перевизначення CropLabel.selected — викликається після ручного виділення."""
        left, top, width, height = rect
        self._pending_box = Box(left, top, width, height)
        self._pending_source = "manual"

        crop = self.frame.crop((left, top, left + width, top + height)).convert("RGB")
        image = QImage(crop.tobytes(), crop.width, crop.height, crop.width * 3,
                       QImage.Format.Format_RGB888)
        zoom = max(1, 220 // max(1, crop.width))
        pixmap = QPixmap.fromImage(image).scaled(
            crop.width * zoom, crop.height * zoom, Qt.AspectRatioMode.KeepAspectRatio
        )
        self.preview_label.setPixmap(pixmap)

        self.confirm_btn.setVisible(True)
        self._set_status("Підтвердь виділену область [Так] або виділи ще раз.")

    # --- Підтвердження та перехід між кроками -------------------------------

    def confirm_candidate(self):
        """Зберегти підтвердженого (авто чи ручного) кандидата в калібрування."""
        if self._pending_box is None or self.frame is None or self.window is None:
            return

        box = self._pending_box
        crop = self.frame.crop((box.left, box.top, box.left + box.width, box.top + box.height))
        rel = dota_window.to_relative(self.window, (box.left, box.top, box.width, box.height))
        self.store.add(self._current_name, crop, rel, source=self._pending_source)

        self._pending_box = None
        self.preview_label.clear()
        self._advance_step()

    def _advance_step(self):
        self._step_index += 1
        if self._step_index >= len(self.STEPS):
            self._show_summary()
            return

        next_name = self.STEPS[self._step_index]
        if next_name == "stop":
            # Той самий кадр, що й для "searching" — обидва видно одночасно,
            # новий знімок не потрібен.
            self._current_name = next_name
            self._auto_detect(next_name)
        else:
            self._prompt_capture(next_name)

    # --- Крок 5: зведення і самоперевірка -----------------------------------

    def _show_summary(self):
        self._awaiting_action = None
        self.crop_label.hide()
        self.preview_label.hide()
        self.confirm_btn.setVisible(False)
        self.manual_btn.setVisible(False)
        self.candidates_box.hide()

        lines = ["Калібрування завершено. Зведення:"]
        for name in self.STEPS:
            element = self.store.element(name)
            state = f"збережено ({element.source})" if element else "пропущено"
            lines.append(f"  • {name}: {state}")
        lines.append(
            "«Прийняти» саме визначиться автоматично при першому знайденому "
            "матчі — цей елемент не знімається заздалегідь."
        )
        self.summary_label.setText("\n".join(lines))
        self.summary_label.show()

        self._set_status("Готово. Можна перевірити калібрування на живому екрані.")
        self.check_btn.setVisible(True)
        self.save_btn.setVisible(True)

    def _request_check(self):
        self._awaiting_action = "check"
        self._set_status(f"Перемкнись у Dota і натисни {CAPTURE_HOTKEY} для перевірки.")

    def _run_check(self):
        """
        Свіжий знімок і перевірка кожного елемента так само, як робитиме бот.

        Майстер не заявляє про успіх, доки не переконається на живому екрані —
        інакше про невдале калібрування дізнаються лише тоді, коли бот
        мовчки не прийме матч.
        """
        window = dota_window.find_window()
        if not dota_window.is_usable(window):
            self._set_status("Вікно Dota не знайдено — перемкнись у гру і спробуй ще раз.")
            return

        frame = dota_window.capture(window)
        if is_blank(frame):
            self._set_status(
                "Знімок чорний — перемкни Dota у віконний режим без рамки "
                "і спробуй ще раз."
            )
            return

        lines = ["Перевірка на свіжому знімку:"]
        for name in self.STEPS:
            if not self.store.has(name):
                lines.append(f"  • {name}: не відкалібровано")
                continue

            left, top, width, height = self.store.search_region(name, window)
            crop = frame.crop((
                left - window.left, top - window.top,
                left - window.left + width, top - window.top + height,
            ))
            found = find_template(
                self.store.template_path(name), crop,
                confidence=CONFIDENCE.get(name), offset=(left, top)
            )
            lines.append(f"  • {name}: {'знайдено' if found else 'НЕ знайдено'}")

        self._set_status("\n".join(lines))

    # --- Завершення майстра --------------------------------------------------

    def _skip(self):
        """
        Пропустити калібрування навмисно.

        Приймання матчів шукає кнопку за кольором і калібрування не
        потребує — пропуск вимикає лише дистанційний запуск/зупинку пошуку
        через Telegram, про що сказано прямо, а не замовчується.
        """
        answer = QMessageBox.question(
            self, "Пропустити калібрування?",
            "Приймання матчів працюватиме і без калібрування — кнопка "
            "«Прийняти» визначається автоматично за кольором. Пропуск лише "
            "вимикає дистанційний запуск і зупинку пошуку гри через "
            "Telegram.\n\nПропустити калібрування?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        if not self.store.is_empty():
            self.store.save()
            self.saved = True
        self.reject()

    def save_and_close(self):
        """Зберегти калібрування на диск і закрити майстер."""
        if self.window is not None:
            self.store.window_size = (self.window.width, self.window.height)
        self.store.save()
        self.saved = True
        self.accept()

def run_wizard(calibration_dir=None) -> bool:
    """
    Показати майстер калібрування.

    Returns:
        True якщо калібрування збережено (навіть частково)
    """
    from config import CALIBRATION_DIR

    store = Calibration.load(calibration_dir or CALIBRATION_DIR)
    app = QApplication.instance() or QApplication([])
    dialog = _WizardDialog(store)
    dialog.exec()
    return dialog.saved
