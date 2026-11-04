#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 암기 화면: 카드 앞·뒷면, 이전·다음, 뜻 보기 (REQ-003)
# 파일 위치: src/ui/memorize_view.py

from datetime import datetime

from PyQt6 import QtCore, QtWidgets

from src.services.memorize_session import KIND_NEW, MemorizeSession
from src.storage.history_csv import append_records


class MemorizeView(QtWidgets.QWidget):
    """카드를 한 장씩 보여준다. 완료 처리는 MainWindow가 맡는다 (화면은 계산하지 않음)."""

    # 마지막 카드에서 "완료"를 누르면 발생한다
    completed = QtCore.pyqtSignal()

    def __init__(self, session: MemorizeSession, history_path: str, parent=None):
        super().__init__(parent)
        self._session = session
        self._history_path = history_path
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        self._title = QtWidgets.QLabel()
        self._title.setStyleSheet("font-size: 16px; font-weight: bold;")
        self._counter = QtWidgets.QLabel()
        self._counter.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)

        header = QtWidgets.QHBoxLayout()
        header.addWidget(self._title)
        header.addStretch()
        header.addWidget(self._counter)

        self._english = QtWidgets.QLabel()
        self._english.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._english.setStyleSheet("font-size: 40px; font-weight: bold;")
        self._meaning = QtWidgets.QLabel()
        self._meaning.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._meaning.setStyleSheet("font-size: 22px;")
        self._badge = QtWidgets.QLabel()
        self._badge.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        card = QtWidgets.QFrame()
        card.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.addStretch()
        card_layout.addWidget(self._english)
        card_layout.addWidget(self._meaning)
        card_layout.addStretch()

        self._reveal_button = QtWidgets.QPushButton("뜻 보기")
        self._reveal_button.clicked.connect(self._on_reveal)
        self._previous_button = QtWidgets.QPushButton("← 이전")
        self._previous_button.clicked.connect(self._on_previous)
        self._next_button = QtWidgets.QPushButton("다음 →")
        self._next_button.clicked.connect(self._on_next)

        navigation = QtWidgets.QHBoxLayout()
        navigation.addWidget(self._previous_button)
        navigation.addStretch()
        navigation.addWidget(self._reveal_button)
        navigation.addStretch()
        navigation.addWidget(self._next_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(card, stretch=1)
        layout.addWidget(self._badge)
        layout.addLayout(navigation)

    @property
    def session(self) -> MemorizeSession:
        return self._session

    def _refresh(self):
        total = len(self._session.cards)
        self._title.setText(f"{self._session.day}일차 암기")
        self._counter.setText(f"카드 {self._session.position + 1} / {total}" if total else "카드 없음")

        card = self._session.current
        if card is None:
            self._english.setText("이 일차에 암기할 단어가 없습니다.")
            self._meaning.clear()
            self._badge.clear()
            self._reveal_button.setEnabled(False)
            self._previous_button.setEnabled(False)
            self._next_button.setEnabled(False)
            return

        self._english.setText(card.word.english)
        revealed = self._session.is_revealed()
        self._meaning.setText("  ·  ".join(card.word.meanings) if revealed else "")
        self._badge.setText("" if card.kind == KIND_NEW else f"[{card.kind}]")
        self._reveal_button.setEnabled(not revealed)
        self._previous_button.setEnabled(not self._session.is_first)
        self._next_button.setText("완료" if self._session.is_last else "다음 →")

    def _on_reveal(self):
        # 뜻을 처음 열 때만 암기 이력을 남긴다 (프로세스 설계 4장)
        record = self._session.reveal(datetime.now())
        if record is not None:
            try:
                append_records(self._history_path, [record])
            except OSError as error:
                QtWidgets.QMessageBox.warning(self, "저장 실패", f"암기 이력을 저장하지 못했습니다.\n{error}")
        self._refresh()

    def _on_previous(self):
        self._session.previous()
        self._refresh()

    def _on_next(self):
        if self._session.current is None:
            return
        self._session.next()
        if self._session.finished:
            self.completed.emit()
            return
        self._refresh()
