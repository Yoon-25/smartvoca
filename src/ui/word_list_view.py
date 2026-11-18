#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - 단어장 화면: 목록 표, 검색, 불러오기·저장, 건너뛴 행 보기 (REQ-001, REQ-002)
# 파일 위치: src/ui/word_list_view.py

import os

from PyQt6 import QtCore, QtWidgets

from src.models.word import Word
from src.storage.word_csv import LoadResult, SkipInfo, WordFileError, load_words, save_words

EMPTY_MESSAGE = "단어장이 비어 있습니다. 불러오기로 CSV 파일을 선택하세요."
DEFAULT_SAVE_NAME = "voca_2000.csv"
TABLE_HEADERS = ["번호", "영단어", "품사", "뜻"]


class WordListView(QtWidgets.QWidget):
    """단어장을 표로 보여준다. 불러오기가 성공하면 words_loaded로 새 단어장을 알린다 (UI 설계서 3장)."""

    # (단어 목록, 건너뛴 행 목록, 불러온 파일 경로)
    words_loaded = QtCore.pyqtSignal(object, object, str)

    def __init__(self, words: list[Word], skipped: list[SkipInfo], file_path: str, parent=None):
        super().__init__(parent)
        self._words = words
        self._skipped = skipped
        self._file_path = file_path
        self._build_ui()
        self._render()

    # ---------- 화면 구성 ----------

    def _build_ui(self):
        self._title = QtWidgets.QLabel()
        self._title.setStyleSheet("font-size: 16px; font-weight: bold;")

        load_button = QtWidgets.QPushButton("불러오기…")
        load_button.clicked.connect(self._on_load_clicked)
        save_button = QtWidgets.QPushButton("저장…")
        save_button.clicked.connect(self._on_save_clicked)

        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("영단어 또는 뜻 검색")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._apply_filter)

        top = QtWidgets.QHBoxLayout()
        top.addWidget(load_button)
        top.addWidget(save_button)
        top.addStretch()
        top.addWidget(QtWidgets.QLabel("검색:"))
        top.addWidget(self._search)

        self._table = QtWidgets.QTableWidget(0, len(TABLE_HEADERS))
        self._table.setHorizontalHeaderLabels(TABLE_HEADERS)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setColumnWidth(0, 70)
        self._table.setColumnWidth(1, 160)
        self._table.setColumnWidth(2, 80)

        self._empty_label = QtWidgets.QLabel(EMPTY_MESSAGE)
        self._empty_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self._skip_label = QtWidgets.QLabel()
        self._skip_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self._skip_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
        self._skip_label.linkActivated.connect(self._show_skipped_details)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._title)
        layout.addLayout(top)
        layout.addWidget(self._table)
        layout.addWidget(self._empty_label)
        layout.addWidget(self._skip_label)

    # ---------- 표시 ----------

    def _render(self):
        self._title.setText(f"단어장 - {os.path.basename(self._file_path)}" if self._file_path else "단어장")

        self._table.setRowCount(len(self._words))
        for row, word in enumerate(self._words):
            values = [str(word.index + 1), word.english, word.pos, " / ".join(word.meanings)]
            for column, value in enumerate(values):
                self._table.setItem(row, column, QtWidgets.QTableWidgetItem(value))

        is_empty = not self._words
        self._table.setVisible(not is_empty)
        self._search.setEnabled(not is_empty)
        self._empty_label.setVisible(is_empty)

        if self._skipped:
            self._skip_label.setText(f'<a href="skipped">건너뛴 행 {len(self._skipped)}개 (세부 보기)</a>')
        else:
            self._skip_label.clear()
        self._skip_label.setVisible(bool(self._skipped))
        self._apply_filter(self._search.text())

    def _apply_filter(self, text: str):
        """영단어 또는 뜻에 검색어가 들어 있는 행만 보인다. 대소문자는 무시한다."""
        needle = text.strip().lower()
        for row, word in enumerate(self._words):
            haystack = f"{word.english} {' '.join(word.meanings)}".lower()
            self._table.setRowHidden(row, bool(needle) and needle not in haystack)

    # ---------- 동작 ----------

    def _on_load_clicked(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "단어장 불러오기", "", "CSV 파일 (*.csv)")
        if not path:
            return

        try:
            result: LoadResult = load_words(path)
        except FileNotFoundError:
            self._warn("단어장 오류", f"파일을 찾을 수 없습니다.\n{path}")
            return
        except WordFileError as error:
            self._warn("단어장 오류", f"{error}\n현재 단어장은 그대로 유지됩니다.")
            return
        except (OSError, UnicodeDecodeError) as error:
            self._warn("단어장 오류", f"파일을 읽을 수 없습니다. 현재 단어장은 그대로 유지됩니다.\n{error}")
            return

        self._words = result.words
        self._skipped = result.skipped
        self._file_path = path
        self._search.clear()
        self._render()
        self.words_loaded.emit(result.words, result.skipped, path)

    def _on_save_clicked(self):
        if not self._words:
            self._warn("저장", "저장할 단어가 없습니다.")
            return

        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "단어장 저장", DEFAULT_SAVE_NAME, "CSV 파일 (*.csv)")
        if not path:
            return

        try:
            save_words(path, self._words)
        except OSError as error:
            self._warn("저장 실패", f"파일을 저장하지 못했습니다. 기존 파일은 그대로 있습니다. (원인: {error})")
            return
        QtWidgets.QMessageBox.information(self, "저장", f"{len(self._words):,}개 단어를 저장했습니다.\n{path}")

    def _show_skipped_details(self, _link: str):
        lines = [f"{skip.line_no}행: {skip.reason}" for skip in self._skipped]
        box = QtWidgets.QMessageBox(self)
        box.setIcon(QtWidgets.QMessageBox.Icon.Information)
        box.setWindowTitle("건너뛴 행")
        box.setText(f"{len(self._skipped)}개 행을 건너뛰었습니다.")
        box.setDetailedText("\n".join(lines))
        box.exec()

    def _warn(self, title: str, message: str):
        QtWidgets.QMessageBox.warning(self, title, message)

    # ---------- 외부에서 볼 수 있는 상태 ----------

    @property
    def words(self) -> list[Word]:
        return self._words
