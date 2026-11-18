#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - 설정 대화상자: 하루 단어 수, 복습 비율, 기본 문제 수 (REQ-005, REQ-006, REQ-004)
# 파일 위치: src/ui/settings_dialog.py

from PyQt6 import QtWidgets

from src.models.settings import Settings
from src.storage.json_store import QUESTION_COUNT_MIN, RATIO_RANGE, WORDS_PER_DAY_RANGE

DAY_CHANGE_QUESTION = "일차 구성이 바뀝니다. 계속할까요?"
RATIO_PERCENT_MAX = int(RATIO_RANGE[1] * 100)


class SettingsDialog(QtWidgets.QDialog):
    """설정 값을 바꾼다. 저장 파일 쓰기는 메인 창이 맡는다 (UI 설계서 7장).

    비율은 화면에서 %로 입력받고 result_settings()에서 0.2 같은 소수로 바꾼다.
    """

    def __init__(self, settings: Settings, word_count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self._original = settings
        self._word_count = word_count
        self._build_ui()
        self._fill(settings)

    # ---------- 화면 구성 ----------

    def _build_ui(self):
        self._words_per_day = QtWidgets.QSpinBox()
        self._words_per_day.setRange(*WORDS_PER_DAY_RANGE)
        self._prev_ratio = self._percent_spin(RATIO_PERCENT_MAX)
        self._wrong_ratio = self._percent_spin(RATIO_PERCENT_MAX)
        self._question_count = QtWidgets.QSpinBox()
        self._question_count.setRange(QUESTION_COUNT_MIN, max(QUESTION_COUNT_MIN, self._word_count))

        form = QtWidgets.QFormLayout()
        form.addRow(f"하루 단어 수 ({WORDS_PER_DAY_RANGE[0]} ~ {WORDS_PER_DAY_RANGE[1]})", self._words_per_day)
        form.addRow(f"전날 복습 비율 % (0 ~ {RATIO_PERCENT_MAX})", self._prev_ratio)
        form.addRow(f"오답 복습 비율 % (0 ~ {RATIO_PERCENT_MAX})", self._wrong_ratio)
        form.addRow(f"기본 문제 수 (1 ~ {self._question_count.maximum()})", self._question_count)

        restore_button = QtWidgets.QPushButton("기본값 복원")
        restore_button.clicked.connect(self._restore_defaults)
        cancel_button = QtWidgets.QPushButton("취소")
        cancel_button.clicked.connect(self.reject)
        save_button = QtWidgets.QPushButton("저장")
        save_button.setDefault(True)
        save_button.clicked.connect(self._on_save_clicked)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(restore_button)
        buttons.addStretch()
        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)

    @staticmethod
    def _percent_spin(maximum: int) -> QtWidgets.QSpinBox:
        spin = QtWidgets.QSpinBox()
        spin.setRange(0, maximum)
        spin.setSuffix(" %")
        return spin

    def _fill(self, settings: Settings):
        self._words_per_day.setValue(settings.words_per_day)
        self._prev_ratio.setValue(round(settings.prev_review_ratio * 100))
        self._wrong_ratio.setValue(round(settings.wrong_review_ratio * 100))
        self._question_count.setValue(min(max(QUESTION_COUNT_MIN, settings.default_question_count),
                                          self._question_count.maximum()))

    # ---------- 동작 ----------

    def _restore_defaults(self):
        """기본값으로 채우기만 한다. 저장은 저장 버튼을 눌러야 한다."""
        self._fill(Settings())

    def _on_save_clicked(self):
        if self.result_settings().words_per_day != self._original.words_per_day:
            answer = QtWidgets.QMessageBox.question(self, "설정", DAY_CHANGE_QUESTION)
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                return
        self.accept()

    def result_settings(self) -> Settings:
        return Settings(
            words_per_day=self._words_per_day.value(),
            prev_review_ratio=round(self._prev_ratio.value() / 100, 2),
            wrong_review_ratio=round(self._wrong_ratio.value() / 100, 2),
            default_question_count=self._question_count.value(),
        )
