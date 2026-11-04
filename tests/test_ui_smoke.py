#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 암기 화면 흐름 스모크 테스트 (REQ-003, REQ-010, REQ-005) - 화면 없이 실행
# 파일 위치: tests/test_ui_smoke.py

import os
import tempfile
import unittest
from unittest import mock

# 화면을 띄우지 않고 실행한다 (CI나 원격 환경에서도 동작)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import QtWidgets  # noqa: E402

from src.models.progress import Progress  # noqa: E402
from src.models.settings import Settings  # noqa: E402
from src.models.word import Word  # noqa: E402
from src.storage.history_csv import read_records  # noqa: E402
from src.storage.json_store import load_progress  # noqa: E402
from src.ui.main_window import PAGE_HOME, MainWindow  # noqa: E402


def make_words(count: int) -> list[Word]:
    return [
        Word(key=f"w{i}", english=f"w{i}", pos="명사", meanings=[f"뜻{i}"], index=i)
        for i in range(count)
    ]


class MemorizeFlowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.progress_path = os.path.join(self._temp_dir.name, "progress.json")
        self.history_path = os.path.join(self._temp_dir.name, "study_history.csv")

    def build_window(self, words: list[Word]) -> MainWindow:
        window = MainWindow(words, Settings(words_per_day=10), Progress(), self.progress_path, self.history_path)
        self.addCleanup(window.deleteLater)
        return window

    def test_REQ003_finishing_day_writes_history_and_moves_to_next_day(self):
        window = self.build_window(make_words(3))
        with mock.patch.object(QtWidgets.QMessageBox, "information") as info:
            window._start_memorize()
            view = window._memorize_view
            for _ in range(3):
                view._on_reveal()
                view._on_next()

        self.assertEqual(window._stack.currentIndex(), PAGE_HOME)
        self.assertIsNone(window._memorize_view)
        info.assert_called_once()
        self.assertEqual(len(read_records(self.history_path)), 3)
        self.assertEqual(load_progress(self.progress_path).current_day, 2)

    def test_REQ003_opening_memorize_shows_memorize_page(self):
        window = self.build_window(make_words(3))

        window._start_memorize()

        self.assertIs(window._stack.currentWidget(), window._memorize_view)
        self.assertEqual(window._memorize_view.session.day, 1)

    def test_REQ003_leaving_in_progress_session_asks_first(self):
        window = self.build_window(make_words(3))
        window._start_memorize()
        window._memorize_view._on_reveal()

        with mock.patch.object(QtWidgets.QMessageBox, "question",
                               return_value=QtWidgets.QMessageBox.StandardButton.No) as question:
            moved = window._go_home()

        self.assertFalse(moved)
        question.assert_called_once()
        self.assertIs(window._stack.currentWidget(), window._memorize_view)

    def test_REQ005_empty_word_list_disables_start(self):
        window = self.build_window([])

        self.assertFalse(window._start_button.isEnabled())


class QuizFlowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.history_path = os.path.join(self._temp_dir.name, "study_history.csv")
        self.progress_path = os.path.join(self._temp_dir.name, "progress.json")

    def build_window(self) -> MainWindow:
        words = make_words(5)
        window = MainWindow(words, Settings(words_per_day=10), Progress(), self.progress_path, self.history_path)
        self.addCleanup(window.deleteLater)
        return window

    def test_REQ004_quiz_runs_to_result_and_writes_quiz_history(self):
        window = self.build_window()

        window._on_quiz_start_requested(2, "한→영", ["단답형"])
        view = window._quiz_view
        self.assertEqual(len(view.session.questions), 2)
        for _ in range(2):
            view._submit(view.session.current.accepted[0])
            view._on_primary()

        self.assertTrue(view.session.is_finished)
        self.assertFalse(view._result_panel.isHidden())
        records = read_records(self.history_path)
        self.assertEqual(len(records), 2)
        self.assertEqual({record.correct for record in records}, {"O"})
        self.assertEqual(len({record.session_id for record in records}), 1)

    def test_REQ004_leaving_unfinished_quiz_asks_first(self):
        window = self.build_window()
        window._on_quiz_start_requested(2, "한→영", ["단답형"])
        window._quiz_view._submit("틀린답")

        with mock.patch.object(QtWidgets.QMessageBox, "question",
                               return_value=QtWidgets.QMessageBox.StandardButton.No) as question:
            moved = window._go_home()

        self.assertFalse(moved)
        question.assert_called_once()


if __name__ == "__main__":
    unittest.main()
