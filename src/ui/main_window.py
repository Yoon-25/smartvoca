#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - 메인 창: 메뉴, 홈, 단어장·암기·시험·보고서 흐름, 진행 중 이동 확인 (REQ-001~011)
# 파일 위치: src/ui/main_window.py

import os
import random
from datetime import date, datetime

from PyQt6 import QtCore, QtWidgets

from src.models.progress import Progress
from src.models.settings import Settings
from src.models.word import Word
from src.services.day_planner import build_study_set, day_count, new_words_for_day
from src.services.memorize_session import MemorizeSession, complete_day
from src.services.quiz_builder import QuizOptions, build_quiz
from src.services.quiz_session import QuizSession, new_session_id
from src.services.stats import aggregate
from src.services.report_builder import build_report, filter_period, save_report
from src.storage.history_csv import read_history, read_records
from src.storage.json_store import save_progress
from src.ui.memorize_view import MemorizeView
from src.ui.quiz_setup_view import QuizSetupView
from src.ui.quiz_view import QuizView
from src.ui.report_view import NO_HISTORY_MESSAGE, ReportView
from src.ui.word_list_view import WordListView

PAGE_HOME = 0
PAGE_QUIZ_SETUP = 1  # 암기·시험 진행 화면은 생성할 때마다 뒤에 추가된다

LEAVE_CONFIRM_MESSAGE = "진행 중인 학습이 있습니다. 나가면 진행 상황이 사라집니다. 나가시겠습니까?"


class MainWindow(QtWidgets.QMainWindow):
    """메인 창. 가운데 영역은 QStackedWidget으로 화면을 바꾼다 (UI 설계서 1장)."""

    def __init__(self, words: list[Word], settings: Settings, progress: Progress,
                 progress_path: str, history_path: str, reports_dir: str | None = None,
                 word_file_path: str = "", skipped: list | None = None, parent=None):
        super().__init__(parent)
        self._words = words
        self._settings = settings
        self._progress = progress
        self._progress_path = progress_path
        self._history_path = history_path
        # 보고서 폴더를 생략하면 이력 파일 옆의 reports 폴더를 쓴다 (데이터 설계서 8절)
        self._reports_dir = reports_dir or os.path.join(os.path.dirname(os.path.abspath(history_path)), "reports")
        self._word_file_path = word_file_path
        self._skipped = skipped or []
        self._memorize_view: MemorizeView | None = None
        self._quiz_view: QuizView | None = None
        self._quiz_options: QuizOptions | None = None

        self.setWindowTitle("스마트 보카")
        self.resize(800, 560)
        self._build_ui()
        self._refresh_home()

    # ---------- 화면 구성 ----------

    def _build_ui(self):
        self._stack = QtWidgets.QStackedWidget()
        self._stack.addWidget(self._build_home())
        self._setup_view = self._create_setup_view()
        self._stack.addWidget(self._setup_view)
        self._word_list_view = WordListView(self._words, self._skipped, self._word_file_path)
        self._word_list_view.words_loaded.connect(self._on_words_loaded)
        self._stack.addWidget(self._word_list_view)
        self._report_view = ReportView()
        self._report_view.generate_requested.connect(self._on_report_requested)
        self._stack.addWidget(self._report_view)
        self.setCentralWidget(self._stack)

        self._menu_buttons = {}
        toolbar = self.addToolBar("메뉴")
        toolbar.setMovable(False)
        for name, enabled in [("홈", True), ("단어장", True), ("암기", True), ("시험", True), ("보고서", True)]:
            button = QtWidgets.QToolButton()
            button.setText(name if enabled else f"{name} (준비 중)")
            button.setEnabled(enabled)
            button.clicked.connect(lambda _checked=False, n=name: self._on_menu(n))
            toolbar.addWidget(button)
            self._menu_buttons[name] = button

        self._status_label = QtWidgets.QLabel()
        self.statusBar().addPermanentWidget(self._status_label)

    def _build_home(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()

        self._today_label = QtWidgets.QLabel()
        self._today_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        self._set_label = QtWidgets.QLabel()
        self._last_study_label = QtWidgets.QLabel()

        self._start_button = QtWidgets.QPushButton("암기 시작")
        self._start_button.clicked.connect(self._start_memorize)
        quiz_button = QtWidgets.QPushButton("시험 보기")
        quiz_button.clicked.connect(lambda: self._on_menu("시험"))

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self._start_button)
        buttons.addWidget(quiz_button)

        layout = QtWidgets.QVBoxLayout(page)
        layout.addWidget(QtWidgets.QLabel("오늘의 학습"))
        layout.addWidget(self._today_label)
        layout.addWidget(self._set_label)
        layout.addLayout(buttons)
        layout.addWidget(self._last_study_label)
        layout.addStretch()
        return page

    # ---------- 홈 화면 ----------

    def _today_day(self) -> int:
        """오늘의 일차 = min(현재 일차, 전체 일차 수). 단어가 없으면 0 (프로세스 설계 1장)."""
        total = day_count(len(self._words), self._settings.words_per_day) if self._words else 0
        if total == 0:
            return 0
        return min(self._progress.current_day, total)

    def _refresh_home(self):
        day = self._today_day()
        per_day = self._settings.words_per_day

        if day == 0:
            self._today_label.setText("단어장이 비어 있습니다.")
            self._set_label.clear()
            self._start_button.setEnabled(False)
        else:
            new_words = new_words_for_day(self._words, day, per_day)
            self._today_label.setText(
                f"{day}일차 (단어 {new_words[0].index + 1} ~ {new_words[-1].index + 1})"
            )
            self._set_label.setText(f"신규 {len(new_words)}개 · 복습은 암기 시작 시 계산됩니다.")
            self._start_button.setEnabled(True)

        if self._progress.last_study_date:
            self._last_study_label.setText(f"마지막 학습: {self._progress.last_study_date.isoformat()}")
        else:
            self._last_study_label.setText("아직 학습 기록 없음")

        self._status_label.setText(f"단어 {len(self._words):,}개 · 오늘 {day}일차 · 하루 {per_day}개")

    # ---------- 화면 전환 ----------

    def _on_menu(self, name: str):
        if name == "홈":
            self._go_home()
        elif name == "암기":
            self._start_memorize()
        elif name == "시험":
            self._open_quiz_setup()
        elif name == "보고서":
            self._open_report()
        elif name == "단어장":
            self._open_word_list()

    def _go_home(self) -> bool:
        if not self._confirm_leave():
            return False
        self._remove_memorize_view()
        self._remove_quiz_view()
        self._refresh_home()
        self._stack.setCurrentIndex(PAGE_HOME)
        return True

    def _confirm_leave(self) -> bool:
        """암기나 시험이 진행 중이면 나가기 전에 확인한다 (UI 설계서 1장, 9장)."""
        if not self._is_in_progress():
            return True
        answer = QtWidgets.QMessageBox.question(self, "확인", LEAVE_CONFIRM_MESSAGE)
        return answer == QtWidgets.QMessageBox.StandardButton.Yes

    def _is_in_progress(self) -> bool:
        memorizing = self._memorize_view is not None and self._memorize_view.session.is_in_progress()
        quizzing = self._quiz_view is not None and self._quiz_in_progress(self._quiz_view.session)
        return memorizing or quizzing

    @staticmethod
    def _quiz_in_progress(session: QuizSession) -> bool:
        return not session.is_finished and (session.position > 0 or session.is_submitted)

    # ---------- 암기 ----------

    def _start_memorize(self):
        if not self._confirm_leave():
            return
        day = self._today_day()
        if day == 0:
            return

        history = read_records(self._history_path)
        study = build_study_set(
            self._words,
            day,
            self._settings.words_per_day,
            history,
            self._settings.prev_review_ratio,
            self._settings.wrong_review_ratio,
        )
        session = MemorizeSession.from_study_set(day, study)

        self._remove_memorize_view()
        self._remove_quiz_view()
        self._memorize_view = MemorizeView(session, self._history_path)
        self._memorize_view.completed.connect(self._on_memorize_completed)
        self._stack.addWidget(self._memorize_view)
        self._stack.setCurrentWidget(self._memorize_view)

    def _on_memorize_completed(self):
        view = self._memorize_view
        if view is None:
            return
        day = view.session.day

        self._progress = complete_day(self._progress, day, date.today())
        try:
            save_progress(self._progress_path, self._progress)
        except OSError as error:
            QtWidgets.QMessageBox.warning(self, "저장 실패", f"진도를 저장하지 못했습니다.\n{error}")

        QtWidgets.QMessageBox.information(
            self,
            "암기 완료",
            f"{day}일차 암기를 마쳤습니다. 다음 학습은 {self._today_day()}일차입니다.",
        )
        self._remove_memorize_view()
        self._refresh_home()
        self._stack.setCurrentIndex(PAGE_HOME)

    def _remove_memorize_view(self):
        if self._memorize_view is None:
            return
        self._stack.removeWidget(self._memorize_view)
        self._memorize_view.deleteLater()
        self._memorize_view = None

    # ---------- 시험 ----------

    def _open_quiz_setup(self):
        if not self._confirm_leave():
            return
        if not self._words:
            QtWidgets.QMessageBox.information(self, "시험", "단어장이 비어 있어 시험을 시작할 수 없습니다.")
            return
        self._remove_memorize_view()
        self._remove_quiz_view()
        self._stack.setCurrentIndex(PAGE_QUIZ_SETUP)

    # ---------- 단어장 ----------

    def _open_word_list(self):
        if not self._confirm_leave():
            return
        self._remove_memorize_view()
        self._remove_quiz_view()
        self._stack.setCurrentWidget(self._word_list_view)

    def _on_words_loaded(self, words: list[Word], skipped: list, path: str):
        """단어장을 불러오면 홈 요약과 시험 설정의 단어 수를 새 목록에 맞춘다."""
        self._words = words
        self._skipped = skipped
        self._word_file_path = path
        self._rebuild_setup_view()
        self._refresh_home()

    def _create_setup_view(self) -> QuizSetupView:
        view = QuizSetupView(len(self._words), self._settings.default_question_count)
        view.start_requested.connect(self._on_quiz_start_requested)
        view.cancelled.connect(self._go_home)
        return view

    def _rebuild_setup_view(self):
        index = self._stack.indexOf(self._setup_view)
        self._stack.removeWidget(self._setup_view)
        self._setup_view.deleteLater()
        self._setup_view = self._create_setup_view()
        self._stack.insertWidget(index, self._setup_view)

    # ---------- 보고서 ----------

    def _open_report(self):
        if not self._confirm_leave():
            return
        self._remove_memorize_view()
        self._remove_quiz_view()
        self._stack.setCurrentWidget(self._report_view)

    def _on_report_requested(self, period_days):
        view = self._report_view
        today = date.today()
        now = datetime.now()

        loaded = read_history(self._history_path)
        if not filter_period(loaded.records, period_days, today):
            view.show_message(NO_HISTORY_MESSAGE)  # 이력이 없으면 파일을 만들지 않는다 (REQ-011)
            return

        text = build_report(
            loaded.records,
            period_days,
            today,
            now,
            word_keys={word.key for word in self._words},
            skipped=loaded.skipped,
        )
        try:
            saved_path = save_report(text, self._reports_dir, now)
        except OSError as error:
            view.show_preview_only(text, str(error))
            return
        view.show_report(text, saved_path)

    def _on_quiz_start_requested(self, count: int, direction: str, types: list[str]):
        self._quiz_options = QuizOptions(
            count=count,
            direction=direction,
            question_types=types,
            per_day=self._settings.words_per_day,
            today=date.today(),
        )
        self._start_quiz()

    def _start_quiz(self):
        if self._quiz_options is None:
            return
        stats = aggregate(read_records(self._history_path))
        questions = build_quiz(self._words, stats, self._quiz_options, random.Random())
        session = QuizSession(session_id=new_session_id(datetime.now()), questions=questions)

        self._remove_quiz_view()
        self._quiz_view = QuizView(session, self._history_path)
        self._quiz_view.go_home.connect(self._go_home)
        self._quiz_view.retry.connect(self._start_quiz)
        self._stack.addWidget(self._quiz_view)
        self._stack.setCurrentWidget(self._quiz_view)

    def _remove_quiz_view(self):
        if self._quiz_view is None:
            return
        self._stack.removeWidget(self._quiz_view)
        self._quiz_view.deleteLater()
        self._quiz_view = None

    def closeEvent(self, event):
        # 진행 중인 학습이 있으면 창 닫기도 확인한다
        if self._confirm_leave():
            event.accept()
        else:
            event.ignore()
