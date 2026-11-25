#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - smartvoca - 단어장 화면: 목록, 검색, 추가·수정·삭제(초안), 저장·불러오기 확인, 건너뛴 행 보기 (REQ-001, REQ-002, ADR-013)
# 파일 위치: src/ui/word_list_view.py

import os

from PyQt6 import QtCore, QtWidgets

from src.models.word import Word
from src.services.word_editor import (
    WordInput,
    add_word,
    day_layout_changed,
    delete_word,
    find_word,
    update_word,
    validate_word_input,
)
from src.storage.word_csv import LoadResult, SkipInfo, WordFileError, load_words, save_words_with_backup
from src.ui.word_edit_dialog import WordEditDialog

EMPTY_MESSAGE = "단어장이 비어 있습니다. 추가 버튼으로 단어를 넣거나 불러오기로 CSV 파일을 선택하세요."
DEFAULT_SAVE_NAME = "voca_2000.csv"
TABLE_HEADERS = ["번호", "영단어", "품사", "뜻"]
BUSY_MESSAGE = "진행 중인 암기·시험이 있습니다. 학습을 끝낸 뒤 단어를 바꿔 주세요."


class WordListView(QtWidgets.QWidget):
    """단어장을 표로 보여주고 편집한다. 편집은 메모리 초안에서 하고 '저장'을 눌러야 파일에 쓴다 (ADR-013).

    words_loaded: 초안이 바뀔 때마다 (단어 목록, 건너뛴 행, 파일 경로)를 알린다. 메인 창이 홈·시험 설정을 맞춘다.
    busy_check: 진행 중인 학습이 있으면 True를 돌려주는 함수. 있으면 편집과 저장을 막는다.
    """

    words_loaded = QtCore.pyqtSignal(object, object, str)

    def __init__(self, words: list[Word], skipped: list[SkipInfo], file_path: str, busy_check=None, parent=None):
        super().__init__(parent)
        self._words = list(words)
        self._skipped = list(skipped)
        self._file_path = file_path
        self._busy_check = busy_check
        self._saved_keys = [word.key for word in words]  # 파일에 있는 키 순서 (일차 구성 변경 판정)
        self._dirty = False
        self._build_ui()
        self._render()

    # ---------- 화면 구성 ----------

    def _build_ui(self):
        self._title = QtWidgets.QLabel()
        self._title.setStyleSheet("font-size: 16px; font-weight: bold;")
        self._dirty_label = QtWidgets.QLabel()
        self._dirty_label.setStyleSheet("color: #8a5a00; font-weight: bold;")

        self._add_button = self._button("추가…", self._on_add_clicked)
        self._edit_button = self._button("수정…", self._on_edit_clicked)
        self._delete_button = self._button("삭제", self._on_delete_clicked)
        self._save_button = self._button("저장", self._on_save_clicked)
        self._discard_button = self._button("변경 취소", self._on_discard_clicked)
        load_button = self._button("불러오기…", self._on_load_clicked)
        save_as_button = self._button("다른 이름으로 저장…", self._on_save_as_clicked)

        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("영단어 또는 뜻 검색")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._apply_filter)

        top = QtWidgets.QHBoxLayout()
        for button in (self._add_button, self._edit_button, self._delete_button):
            top.addWidget(button)
        top.addSpacing(16)
        for button in (self._save_button, self._discard_button):
            top.addWidget(button)
        top.addStretch()
        top.addWidget(QtWidgets.QLabel("검색:"))
        top.addWidget(self._search)

        file_row = QtWidgets.QHBoxLayout()
        file_row.addWidget(load_button)
        file_row.addWidget(save_as_button)
        file_row.addStretch()

        self._table = QtWidgets.QTableWidget(0, len(TABLE_HEADERS))
        self._table.setHorizontalHeaderLabels(TABLE_HEADERS)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setColumnWidth(0, 70)
        self._table.setColumnWidth(1, 160)
        self._table.setColumnWidth(2, 80)
        self._table.doubleClicked.connect(lambda _index: self._on_edit_clicked())

        self._empty_label = QtWidgets.QLabel(EMPTY_MESSAGE)
        self._empty_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self._skip_label = QtWidgets.QLabel()
        self._skip_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self._skip_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
        self._skip_label.linkActivated.connect(self._show_skipped_details)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._title)
        layout.addWidget(self._dirty_label)
        layout.addLayout(top)
        layout.addLayout(file_row)
        layout.addWidget(self._table)
        layout.addWidget(self._empty_label)
        layout.addWidget(self._skip_label)

    @staticmethod
    def _button(text: str, handler) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton(text)
        button.clicked.connect(handler)
        return button

    # ---------- 표시 ----------

    def _render(self):
        name = os.path.basename(self._file_path) if self._file_path else "(파일 없음)"
        self._title.setText(f"단어장 - {name}")
        self._dirty_label.setText("저장하지 않은 변경이 있습니다." if self._dirty else "")

        self._table.setRowCount(len(self._words))
        for row, word in enumerate(self._words):
            values = [str(word.index + 1), word.english, word.pos, " / ".join(word.meanings)]
            for column, value in enumerate(values):
                self._table.setItem(row, column, QtWidgets.QTableWidgetItem(value))

        is_empty = not self._words
        self._table.setVisible(not is_empty)
        self._search.setEnabled(not is_empty)
        self._empty_label.setVisible(is_empty)
        self._edit_button.setEnabled(not is_empty)
        self._delete_button.setEnabled(not is_empty)
        self._save_button.setEnabled(self._dirty)
        self._discard_button.setEnabled(self._dirty)

        if self._skipped:
            self._skip_label.setText(f'<a href="skipped">건너뛴 행 {len(self._skipped)}개 (세부 보기)</a>')
        else:
            self._skip_label.clear()
        self._skip_label.setVisible(bool(self._skipped))
        self._apply_filter(self._search.text())
        self.words_loaded.emit(self._words, self._skipped, self._file_path)

    def _apply_filter(self, text: str):
        """영단어 또는 뜻에 검색어가 들어 있는 행만 보인다. 대소문자는 무시한다."""
        needle = text.strip().lower()
        for row, word in enumerate(self._words):
            haystack = f"{word.english} {' '.join(word.meanings)}".lower()
            self._table.setRowHidden(row, bool(needle) and needle not in haystack)

    def _selected_word(self) -> Word | None:
        row = self._table.currentRow()
        if 0 <= row < len(self._words):
            return self._words[row]
        return None

    # ---------- 초안 편집 (대화상자 없이 호출 가능한 부분) ----------

    def _check_not_busy(self):
        if self._busy_check is not None and self._busy_check():
            raise RuntimeError(BUSY_MESSAGE)

    def add_entry(self, data: WordInput) -> None:
        self._check_not_busy()
        errors = validate_word_input(data, self._words)
        if errors:
            raise ValueError("\n".join(errors))
        self._words = add_word(self._words, data)
        self._dirty = True
        self._render()

    def update_entry(self, key: str, data: WordInput) -> None:
        self._check_not_busy()
        if find_word(self._words, key) is None:
            raise ValueError("단어를 찾을 수 없습니다.")
        errors = validate_word_input(data, self._words, editing_key=key)
        if errors:
            raise ValueError("\n".join(errors))
        self._words = update_word(self._words, key, data)
        self._dirty = True
        self._render()

    def delete_entry(self, key: str) -> None:
        self._check_not_busy()
        if find_word(self._words, key) is None:
            raise ValueError("단어를 찾을 수 없습니다.")
        self._words = delete_word(self._words, key)
        self._dirty = True
        self._render()

    def _on_add_clicked(self):
        self._run_with_message(lambda: self._open_dialog_and_apply(None))

    def _on_edit_clicked(self):
        word = self._selected_word()
        if word is None:
            return
        self._run_with_message(lambda: self._open_dialog_and_apply(word))

    def _open_dialog_and_apply(self, word: Word | None):
        self._check_not_busy()
        dialog = WordEditDialog(self._words, word, self)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted or dialog.result_input() is None:
            return
        if word is None:
            self.add_entry(dialog.result_input())
        else:
            self.update_entry(word.key, dialog.result_input())

    def _on_delete_clicked(self):
        word = self._selected_word()
        if word is None:
            return
        answer = QtWidgets.QMessageBox.question(
            self, "삭제", f"'{word.english}' 단어를 삭제할까요?\n저장하기 전까지 파일은 바뀌지 않습니다."
        )
        if answer == QtWidgets.QMessageBox.StandardButton.Yes:
            self._run_with_message(lambda: self.delete_entry(word.key))

    def _run_with_message(self, action):
        try:
            action()
        except (ValueError, RuntimeError) as error:
            self._warn("단어 편집", str(error))

    # ---------- 저장과 불러오기 (파일 쓰기 확인) ----------

    def save_warnings(self) -> list[str]:
        warnings = []
        if day_layout_changed(self._saved_keys, self._words):
            warnings.append("단어 순서나 개수가 바뀌어 일차 구성이 달라집니다. 진도(현재 일차)는 그대로 유지됩니다.")
        if self._skipped:
            warnings.append(f"건너뛴 행 {len(self._skipped)}개는 저장하면 파일에서 사라집니다. 직전 파일은 .bak으로 남습니다.")
        return warnings

    def _on_save_clicked(self):
        self._save_to(self._file_path)

    def _on_save_as_clicked(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "단어장 저장", DEFAULT_SAVE_NAME, "CSV 파일 (*.csv)")
        if path:
            self._save_to(path)

    def _save_to(self, path: str) -> bool:
        if not self._words:
            self._warn("저장", "저장할 단어가 없습니다.")
            return False
        try:
            self._check_not_busy()
        except RuntimeError as error:
            self._warn("저장", str(error))
            return False
        if not path:
            return False

        warnings = self.save_warnings()
        if warnings:
            answer = QtWidgets.QMessageBox.question(self, "저장 확인", "\n".join(warnings) + "\n\n저장할까요?")
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                return False

        try:
            backup = save_words_with_backup(path, self._words)
        except OSError as error:
            self._warn("저장 실패", f"파일을 저장하지 못했습니다. 기존 파일은 그대로 있습니다. (원인: {error})")
            return False

        self._file_path = path
        self._saved_keys = [word.key for word in self._words]
        self._skipped = []
        self._dirty = False
        self._render()
        message = f"{len(self._words):,}개 단어를 저장했습니다.\n{path}"
        if backup:
            message += f"\n직전 파일은 {backup}에 남겼습니다."
        QtWidgets.QMessageBox.information(self, "저장", message)
        return True

    def _on_discard_clicked(self):
        answer = QtWidgets.QMessageBox.question(self, "변경 취소", "저장하지 않은 변경을 버릴까요?")
        if answer == QtWidgets.QMessageBox.StandardButton.Yes and self._file_path:
            self._reload(self._file_path)

    def _on_load_clicked(self):
        if self._dirty:
            answer = QtWidgets.QMessageBox.question(
                self, "단어장 불러오기", "저장하지 않은 변경이 사라집니다. 계속할까요?"
            )
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "단어장 불러오기", "", "CSV 파일 (*.csv)")
        if path:
            self._reload(path)

    def _reload(self, path: str):
        """파일을 읽어 초안을 바꾼다. 실패하면 현재 단어장을 그대로 둔다."""
        try:
            self._check_not_busy()
            result: LoadResult = load_words(path)
        except RuntimeError as error:
            self._warn("단어장 오류", str(error))
            return
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
        self._saved_keys = [word.key for word in result.words]
        self._dirty = False
        self._search.clear()
        self._render()

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

    def has_unsaved_changes(self) -> bool:
        return self._dirty
