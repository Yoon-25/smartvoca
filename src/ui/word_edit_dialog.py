#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - smartvoca - 단어 추가·수정 대화상자: 입력 칸, 검사 메시지 표시 (REQ-001, ADR-013)
# 파일 위치: src/ui/word_edit_dialog.py

from PyQt6 import QtWidgets

from src.models.word import Word
from src.services.word_editor import WordInput, validate_word_input
from src.storage.word_csv import ALLOWED_POS


class WordEditDialog(QtWidgets.QDialog):
    """단어 한 개를 입력받는다. 확인을 누르면 검사하고, 통과하면 WordInput을 돌려준다."""

    def __init__(self, words: list[Word], word: Word | None = None, parent=None):
        super().__init__(parent)
        self._words = words
        self._editing_key = word.key if word else None
        self._result: WordInput | None = None
        self.setWindowTitle("단어 수정" if word else "단어 추가")
        self._build_ui(word)

    def _build_ui(self, word: Word | None):
        self._english = QtWidgets.QLineEdit(word.english if word else "")
        self._pos = QtWidgets.QComboBox()
        self._pos.addItems(list(ALLOWED_POS))
        if word and word.pos in ALLOWED_POS:
            self._pos.setCurrentText(word.pos)
        self._meanings = QtWidgets.QLineEdit(" / ".join(word.meanings) if word else "")
        self._meanings.setPlaceholderText("여러 뜻은 '/'로 나눕니다. 예: 해 / 연도")

        form = QtWidgets.QFormLayout()
        form.addRow("영단어", self._english)
        form.addRow("품사", self._pos)
        form.addRow("뜻", self._meanings)

        self._error_label = QtWidgets.QLabel()
        self._error_label.setStyleSheet("color: #b00020;")
        self._error_label.setWordWrap(True)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._error_label)
        layout.addWidget(buttons)
        self._english.setFocus()

    def _on_accept(self):
        data = WordInput(
            english=self._english.text(),
            pos=self._pos.currentText(),
            meaning_text=self._meanings.text(),
        )
        errors = validate_word_input(data, self._words, editing_key=self._editing_key)
        if errors:
            self._error_label.setText("\n".join(errors))
            return
        self._result = data
        self.accept()

    def result_input(self) -> WordInput | None:
        """확인으로 닫혔을 때만 값을 돌려준다."""
        return self._result
