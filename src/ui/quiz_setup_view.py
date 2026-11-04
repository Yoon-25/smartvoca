#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 시험 설정 화면: 문제 수, 출제 방향, 문제 유형 (REQ-004, REQ-008, REQ-009)
# 파일 위치: src/ui/quiz_setup_view.py

from PyQt6 import QtCore, QtWidgets

from src.services.quiz_builder import (
    DIRECTION_EN_KO,
    DIRECTION_KO_EN,
    DIRECTION_MIXED,
    TYPE_CHOICE,
    TYPE_OX,
    TYPE_SHORT,
)


class QuizSetupView(QtWidgets.QWidget):
    """시험 조건을 고른다. 검사를 통과하면 start_requested로 값을 넘긴다 (UI 설계서 5장)."""

    # (문제 수, 출제 방향, 문제 유형 목록)
    start_requested = QtCore.pyqtSignal(int, str, list)
    cancelled = QtCore.pyqtSignal()

    def __init__(self, word_count: int, default_count: int, parent=None):
        super().__init__(parent)
        self._word_count = word_count
        self._build_ui(default_count)

    def _build_ui(self, default_count: int):
        self._count = QtWidgets.QSpinBox()
        self._count.setRange(1, max(1, self._word_count))
        self._count.setValue(min(max(1, default_count), max(1, self._word_count)))

        self._direction_buttons = {
            DIRECTION_KO_EN: QtWidgets.QRadioButton("한 → 영"),
            DIRECTION_EN_KO: QtWidgets.QRadioButton("영 → 한"),
            DIRECTION_MIXED: QtWidgets.QRadioButton("혼합"),
        }
        self._direction_buttons[DIRECTION_KO_EN].setChecked(True)
        direction_box = QtWidgets.QVBoxLayout()
        for button in self._direction_buttons.values():
            direction_box.addWidget(button)

        self._type_boxes = {
            TYPE_SHORT: QtWidgets.QCheckBox(TYPE_SHORT),
            TYPE_CHOICE: QtWidgets.QCheckBox(TYPE_CHOICE),
            TYPE_OX: QtWidgets.QCheckBox(TYPE_OX),
        }
        self._type_boxes[TYPE_SHORT].setChecked(True)
        type_box = QtWidgets.QVBoxLayout()
        for box in self._type_boxes.values():
            box.toggled.connect(self._refresh_start_enabled)
            type_box.addWidget(box)

        self._warning = QtWidgets.QLabel()
        self._warning.setStyleSheet("color: #b00020;")

        self._cancel_button = QtWidgets.QPushButton("취소")
        self._cancel_button.clicked.connect(self.cancelled.emit)
        self._start_button = QtWidgets.QPushButton("시험 시작")
        self._start_button.clicked.connect(self._on_start)

        form = QtWidgets.QFormLayout()
        form.addRow("문제 수", self._count)
        form.addRow("출제 방향", direction_box)
        form.addRow("문제 유형", type_box)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self._cancel_button)
        buttons.addStretch()
        buttons.addWidget(self._start_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("시험 설정"))
        layout.addLayout(form)
        layout.addWidget(self._warning)
        layout.addStretch()
        layout.addLayout(buttons)
        self._refresh_start_enabled()

    def _selected_types(self) -> list[str]:
        return [name for name, box in self._type_boxes.items() if box.isChecked()]

    def _refresh_start_enabled(self):
        has_type = bool(self._selected_types())
        self._start_button.setEnabled(has_type)
        self._warning.setText("" if has_type else "문제 유형을 하나 이상 선택하세요.")

    def _on_start(self):
        direction = next(name for name, button in self._direction_buttons.items() if button.isChecked())
        self.start_requested.emit(self._count.value(), direction, self._selected_types())
