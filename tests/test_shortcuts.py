#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - 암기·시험 단축 키 테스트 (REQ-003, REQ-009)
# 파일 위치: tests/test_shortcuts.py

import os
import random
import tempfile
import unittest
from datetime import date, datetime

# 화면을 띄우지 않고 실행한다
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import QtCore, QtGui, QtWidgets  # noqa: E402

from src.models.progress import Progress  # noqa: E402
from src.models.settings import Settings  # noqa: E402
from src.models.word import Word  # noqa: E402
from src.services.quiz_builder import QuizOptions, build_quiz  # noqa: E402
from src.services.quiz_session import QuizSession, new_session_id  # noqa: E402
from src.storage.history_csv import read_records  # noqa: E402
from src.ui.main_window import MainWindow  # noqa: E402
from src.ui.quiz_view import QuizView  # noqa: E402


def make_words(count: int) -> list[Word]:
    return [Word(key=f"w{i}", english=f"w{i}", pos="명사", meanings=[f"뜻{i}"], index=i) for i in range(count)]


class MemorizeShortcutTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.history_path = os.path.join(self._temp_dir.name, "h.csv")
        self.window = MainWindow(make_words(3), Settings(words_per_day=10), Progress(),
                                 os.path.join(self._temp_dir.name, "p.json"), self.history_path,
                                 os.path.join(self._temp_dir.name, "reports"))
        self.addCleanup(self.window.deleteLater)
        self.window._start_memorize()
        self.view = self.window._memorize_view

    def test_REQ003_space_reveals_once_and_records_history(self):
        self.view._on_space()
        self.view._on_space()  # 이미 연 뒤에는 아무 일도 없다
        self.assertTrue(self.view.session.is_revealed())
        self.assertEqual(len(read_records(self.history_path)), 1)

    def test_REQ003_right_key_moves_next_but_never_completes_on_last_card(self):
        self.view._on_next_by_key()
        self.view._on_next_by_key()
        self.assertEqual(self.view.session.position, 2)
        self.view._on_next_by_key()  # 마지막 카드에서는 무시한다
        self.assertEqual(self.view.session.position, 2)
        self.assertFalse(self.view.session.finished)

    def test_REQ003_left_key_moves_back_and_stops_at_first_card(self):
        self.view._on_next_by_key()
        self.view._on_previous_by_key()
        self.view._on_previous_by_key()
        self.assertEqual(self.view.session.position, 0)


class QuizShortcutTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.window = MainWindow(make_words(6), Settings(words_per_day=10), Progress(),
                                 os.path.join(self._temp_dir.name, "p.json"),
                                 os.path.join(self._temp_dir.name, "h.csv"),
                                 os.path.join(self._temp_dir.name, "reports"))
        self.addCleanup(self.window.deleteLater)

    def test_REQ009_number_key_selects_matching_choice(self):
        options = QuizOptions(count=1, direction="ko_en", question_types=["4지선다"],
                              per_day=10, today=date(2026, 11, 18))
        questions = build_quiz(make_words(6), {}, options, random.Random(1))
        session = QuizSession(session_id=new_session_id(datetime(2026, 11, 18, 9, 0, 0)), questions=questions)
        view = QuizView(session, os.path.join(self._temp_dir.name, "h.csv"))
        self.addCleanup(view.deleteLater)

        self.assertEqual(len(view._choice_buttons), 4)
        view.keyPressEvent(QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress, QtCore.Qt.Key.Key_3,
                                           QtCore.Qt.KeyboardModifier.NoModifier))
        self.assertTrue(view._choice_buttons[2].isChecked())


if __name__ == "__main__":
    unittest.main()
