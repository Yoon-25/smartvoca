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
from src.ui.main_window import PAGE_MEMORIZE, MainWindow  # noqa: E402


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

        self.assertEqual(window._stack.currentIndex(), 0)
        self.assertIsNone(window._memorize_view)
        info.assert_called_once()
        self.assertEqual(len(read_records(self.history_path)), 3)
        self.assertEqual(load_progress(self.progress_path).current_day, 2)

    def test_REQ003_opening_memorize_shows_memorize_page(self):
        window = self.build_window(make_words(3))

        window._start_memorize()

        self.assertEqual(window._stack.currentIndex(), PAGE_MEMORIZE)
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
        self.assertEqual(window._stack.currentIndex(), PAGE_MEMORIZE)

    def test_REQ005_empty_word_list_disables_start(self):
        window = self.build_window([])

        self.assertFalse(window._start_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
