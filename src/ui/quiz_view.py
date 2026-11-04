#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 시험 화면: 문제 표시, 답 제출, 정답 표시, 결과 (REQ-004, REQ-009, REQ-010)
# 파일 위치: src/ui/quiz_view.py

from datetime import datetime

from PyQt6 import QtCore, QtWidgets

from src.services.quiz_builder import TYPE_CHOICE, TYPE_OX, TYPE_SHORT
from src.services.quiz_session import QuizSession
from src.storage.history_csv import append_records


class QuizView(QtWidgets.QWidget):
    """시험 한 세션을 진행한다. 화면은 채점 결과를 표시만 하고, 채점은 QuizSession이 한다."""

    go_home = QtCore.pyqtSignal()
    retry = QtCore.pyqtSignal()

    def __init__(self, session: QuizSession, history_path: str, parent=None):
        super().__init__(parent)
        self._session = session
        self._history_path = history_path
        self._choice_group = QtWidgets.QButtonGroup(self)
        self._choice_buttons: list[QtWidgets.QRadioButton] = []
        self._build_ui()
        self._show_question()

    @property
    def session(self) -> QuizSession:
        return self._session

    # ---------- 화면 구성 ----------

    def _build_ui(self):
        self._progress_label = QtWidgets.QLabel()
        self._direction_label = QtWidgets.QLabel()
        self._prompt = QtWidgets.QLabel()
        self._prompt.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._prompt.setStyleSheet("font-size: 28px; font-weight: bold;")
        self._prompt.setWordWrap(True)

        self._answer_edit = QtWidgets.QLineEdit()
        self._answer_edit.setPlaceholderText("영단어 또는 뜻을 입력하세요")
        self._answer_edit.returnPressed.connect(self._on_primary)

        self._choice_layout = QtWidgets.QVBoxLayout()
        self._ox_true = QtWidgets.QPushButton("O")
        self._ox_false = QtWidgets.QPushButton("X")
        self._ox_true.clicked.connect(lambda: self._submit("O"))
        self._ox_false.clicked.connect(lambda: self._submit("X"))
        ox_layout = QtWidgets.QHBoxLayout()
        ox_layout.addWidget(self._ox_true)
        ox_layout.addWidget(self._ox_false)

        self._feedback = QtWidgets.QLabel()
        self._feedback.setWordWrap(True)
        self._primary_button = QtWidgets.QPushButton()
        self._primary_button.clicked.connect(self._on_primary)

        self._question_panel = QtWidgets.QWidget()
        question_layout = QtWidgets.QVBoxLayout(self._question_panel)
        top = QtWidgets.QHBoxLayout()
        top.addWidget(self._progress_label)
        top.addStretch()
        top.addWidget(self._direction_label)
        question_layout.addLayout(top)
        question_layout.addWidget(self._prompt, stretch=1)
        question_layout.addWidget(self._answer_edit)
        question_layout.addLayout(self._choice_layout)
        question_layout.addLayout(ox_layout)
        question_layout.addWidget(self._feedback)
        question_layout.addWidget(self._primary_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        self._result_panel = QtWidgets.QWidget()
        self._result_score = QtWidgets.QLabel()
        self._result_score.setStyleSheet("font-size: 24px; font-weight: bold;")
        self._result_wrong = QtWidgets.QLabel()
        self._result_wrong.setWordWrap(True)
        home_button = QtWidgets.QPushButton("홈으로")
        home_button.clicked.connect(self.go_home.emit)
        retry_button = QtWidgets.QPushButton("다시 시험")
        retry_button.clicked.connect(self.retry.emit)
        result_buttons = QtWidgets.QHBoxLayout()
        result_buttons.addWidget(home_button)
        result_buttons.addStretch()
        result_buttons.addWidget(retry_button)
        result_layout = QtWidgets.QVBoxLayout(self._result_panel)
        result_layout.addWidget(QtWidgets.QLabel("시험 결과"))
        result_layout.addWidget(self._result_score)
        result_layout.addWidget(self._result_wrong)
        result_layout.addStretch()
        result_layout.addLayout(result_buttons)
        self._result_panel.hide()

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._question_panel)
        layout.addWidget(self._result_panel)

    # ---------- 문제 표시 ----------

    def _show_question(self):
        question = self._session.current
        total = len(self._session.questions)
        self._progress_label.setText(f"문제 {self._session.position + 1} / {total}")
        self._direction_label.setText(f"[{question.direction}]")
        self._prompt.setText(question.prompt)
        self._feedback.clear()

        self._clear_choices()
        self._answer_edit.hide()
        self._ox_true.hide()
        self._ox_false.hide()

        if question.qtype == TYPE_SHORT:
            self._answer_edit.show()
            self._answer_edit.clear()
            self._answer_edit.setFocus()
        elif question.qtype == TYPE_CHOICE:
            self._build_choices(question.choices)
        elif question.qtype == TYPE_OX:
            self._ox_true.show()
            self._ox_false.show()

        self._set_input_enabled(True)
        self._primary_button.setText("제출")

    def _build_choices(self, choices: list[str]):
        for index, text in enumerate(choices):
            button = QtWidgets.QRadioButton(text)
            self._choice_group.addButton(button, index)
            self._choice_layout.addWidget(button)
            self._choice_buttons.append(button)

    def _clear_choices(self):
        for button in self._choice_buttons:
            self._choice_group.removeButton(button)
            button.deleteLater()
        self._choice_buttons = []

    def _set_input_enabled(self, enabled: bool):
        self._answer_edit.setEnabled(enabled)
        self._ox_true.setEnabled(enabled)
        self._ox_false.setEnabled(enabled)
        for button in self._choice_buttons:
            button.setEnabled(enabled)

    # ---------- 답 제출과 이동 ----------

    def _on_primary(self):
        if self._session.is_finished:
            return
        if not self._session.is_submitted:
            self._submit_current_input()
        else:
            self._session.next()
            if self._session.is_finished:
                self._show_result()
            else:
                self._show_question()

    def _submit_current_input(self):
        question = self._session.current
        if question.qtype == TYPE_SHORT:
            answer = self._answer_edit.text()
        elif question.qtype == TYPE_CHOICE:
            checked = self._choice_group.checkedId()
            if checked < 0:
                self._feedback.setText("보기를 하나 고르세요.")
                return
            answer = checked
        else:
            return  # OX는 O·X 버튼으로 바로 제출한다
        self._submit(answer)

    def _submit(self, answer):
        if self._session.is_submitted or self._session.is_finished:
            return
        result, record = self._session.submit(answer, datetime.now())
        try:
            append_records(self._history_path, [record])
        except OSError as error:
            QtWidgets.QMessageBox.warning(self, "저장 실패", f"시험 이력을 저장하지 못했습니다.\n{error}")

        color = "#1b7f3b" if result.is_correct else "#b00020"
        self._feedback.setStyleSheet(f"color: {color}; font-size: 16px;")
        self._feedback.setText(result.message)
        self._set_input_enabled(False)
        self._primary_button.setText("결과 보기" if self._session.is_last else "다음 문제")

    def _show_result(self):
        self._question_panel.hide()
        self._result_score.setText(self._session.score_text)
        wrong = ", ".join(self._session.wrong_words) if self._session.wrong_words else "없음"
        self._result_wrong.setText(f"틀린 단어: {wrong}")
        self._result_panel.show()
