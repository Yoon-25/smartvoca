#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - 보고서 화면: 기간 선택, 보고서 만들기, 미리보기, 저장 경로 표시 (REQ-011)
# 파일 위치: src/ui/report_view.py

from PyQt6 import QtCore, QtWidgets

from src.services.report_builder import PERIOD_7_DAYS, PERIOD_30_DAYS, PERIOD_ALL

NO_HISTORY_MESSAGE = "이력이 없습니다. 암기나 시험을 한 뒤 다시 시도하세요."


class ReportView(QtWidgets.QWidget):
    """기간을 고르고 보고서를 만든다. 실제 집계와 저장은 메인 창이 맡는다 (아키텍처 설계서 6.3절)."""

    # 기간 값 (7, 30, None=전체)
    generate_requested = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        self._period_buttons = [
            (PERIOD_7_DAYS, QtWidgets.QRadioButton("최근 7일")),
            (PERIOD_30_DAYS, QtWidgets.QRadioButton("최근 30일")),
            (PERIOD_ALL, QtWidgets.QRadioButton("전체")),
        ]
        period_layout = QtWidgets.QHBoxLayout()
        group = QtWidgets.QButtonGroup(self)
        for index, (_days, button) in enumerate(self._period_buttons):
            group.addButton(button)
            period_layout.addWidget(button)
            if index == 0:
                button.setChecked(True)  # 기본값: 최근 7일 (D5)
        period_layout.addStretch()

        generate_button = QtWidgets.QPushButton("보고서 만들기")
        generate_button.clicked.connect(self._on_generate_clicked)

        self._preview = QtWidgets.QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setPlaceholderText("기간을 고르고 '보고서 만들기'를 누르세요.")

        self._saved_label = QtWidgets.QLabel()
        self._saved_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("보고서"))
        layout.addLayout(period_layout)
        layout.addWidget(generate_button)
        layout.addWidget(self._preview)
        layout.addWidget(self._saved_label)

    def selected_period(self) -> int | None:
        for days, button in self._period_buttons:
            if button.isChecked():
                return days
        return PERIOD_7_DAYS

    def _on_generate_clicked(self):
        self.generate_requested.emit(self.selected_period())

    def show_report(self, text: str, saved_path: str):
        self._preview.setPlainText(text)
        self._saved_label.setText(f"저장 위치: {saved_path}")

    def show_message(self, message: str):
        """이력이 없을 때처럼 파일을 만들지 않는 경우 미리보기 자리에 안내한다."""
        self._preview.setPlainText(message)
        self._saved_label.clear()

    def show_preview_only(self, text: str, error: str):
        """파일 저장에 실패해도 보고서 내용은 보여준다."""
        self._preview.setPlainText(text)
        self._saved_label.setText(f"파일을 저장하지 못했습니다. ({error})")
