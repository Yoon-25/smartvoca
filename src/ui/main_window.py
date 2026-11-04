#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 메인 창: 상단 메뉴, 홈 화면, 화면 전환, 암기 완료 처리 (REQ-003, REQ-005, REQ-006)
# 파일 위치: src/ui/main_window.py

from datetime import date

from PyQt6 import QtCore, QtWidgets

from src.models.progress import Progress
from src.models.settings import Settings
from src.models.word import Word
from src.services.day_planner import build_study_set, day_count, new_words_for_day
from src.services.memorize_session import MemorizeSession, complete_day
from src.storage.history_csv import read_records
from src.storage.json_store import save_progress
from src.ui.memorize_view import MemorizeView

PAGE_HOME = 0
PAGE_MEMORIZE = 1


class MainWindow(QtWidgets.QMainWindow):
    """메인 창. 가운데 영역은 QStackedWidget으로 화면을 바꾼다 (UI 설계서 1장)."""

    def __init__(self, words: list[Word], settings: Settings, progress: Progress,
                 progress_path: str, history_path: str, parent=None):
        super().__init__(parent)
        self._words = words
        self._settings = settings
        self._progress = progress
        self._progress_path = progress_path
        self._history_path = history_path
        self._memorize_view: MemorizeView | None = None

        self.setWindowTitle("스마트 보카")
        self.resize(800, 560)
        self._build_ui()
        self._refresh_home()

    # ---------- 화면 구성 ----------

    def _build_ui(self):
        self._stack = QtWidgets.QStackedWidget()
        self._stack.addWidget(self._build_home())
        self.setCentralWidget(self._stack)

        self._menu_buttons = {}
        toolbar = self.addToolBar("메뉴")
        toolbar.setMovable(False)
        for name, enabled in [("홈", True), ("단어장", False), ("암기", True), ("시험", False), ("보고서", False)]:
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

        layout = QtWidgets.QVBoxLayout(page)
        layout.addWidget(QtWidgets.QLabel("오늘의 학습"))
        layout.addWidget(self._today_label)
        layout.addWidget(self._set_label)
        layout.addWidget(self._start_button)
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

        self._status_label.setText(
            f"단어 {len(self._words):,}개 · 오늘 {day}일차 · 하루 {per_day}개"
        )

    # ---------- 화면 전환 ----------

    def _on_menu(self, name: str):
        if name == "홈":
            self._go_home()
        elif name == "암기":
            self._start_memorize()

    def _go_home(self) -> bool:
        if not self._confirm_leave_memorize():
            return False
        self._remove_memorize_view()
        self._refresh_home()
        self._stack.setCurrentIndex(PAGE_HOME)
        return True

    def _confirm_leave_memorize(self) -> bool:
        """암기 진행 중이면 나가기 전에 확인한다 (UI 설계서 9장 메시지)."""
        if self._memorize_view is None or not self._memorize_view.session.is_in_progress():
            return True
        answer = QtWidgets.QMessageBox.question(
            self,
            "확인",
            "진행 중인 학습이 있습니다. 나가면 진행 상황이 사라집니다. 나가시겠습니까?",
        )
        return answer == QtWidgets.QMessageBox.StandardButton.Yes

    # ---------- 암기 ----------

    def _start_memorize(self):
        if self._memorize_view is not None and not self._confirm_leave_memorize():
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

    def closeEvent(self, event):
        # 진행 중인 암기가 있으면 창 닫기도 확인한다
        if self._confirm_leave_memorize():
            event.accept()
        else:
            event.ignore()
