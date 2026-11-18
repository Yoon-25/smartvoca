#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - 보고서 화면 흐름 테스트: 이력 없음, 파일 생성, 무시한 행 집계 (REQ-011)
# 파일 위치: tests/test_report_flow.py

import os
import tempfile
import unittest

# 화면을 띄우지 않고 실행한다
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import QtWidgets  # noqa: E402

from src.models.progress import Progress  # noqa: E402
from src.models.settings import Settings  # noqa: E402
from src.models.word import Word  # noqa: E402
from src.services.report_builder import PERIOD_7_DAYS, PERIOD_ALL  # noqa: E402
from src.storage.history_csv import read_history  # noqa: E402
from src.ui.main_window import MainWindow  # noqa: E402
from src.ui.report_view import NO_HISTORY_MESSAGE  # noqa: E402


class ReadHistorySkippedTest(unittest.TestCase):

    def test_REQ011_read_history_counts_skipped_rows_but_not_blank_lines(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = os.path.join(temp_dir.name, "study_history.csv")
        with open(path, "w", encoding="utf-8", newline="") as history_file:
            history_file.write("일시,활동,세션ID,영단어,출제방향,유형,정답여부\n")
            history_file.write("2026-11-18 09:00:00,암기,,apple,암기,암기,\n")
            history_file.write("잘못된 일시,암기,,book,암기,암기,\n")
            history_file.write("\n")
            history_file.write("2026-11-18 10:00:00,시험,S1,cat,한→영,단답형,\n")  # 시험인데 정답여부 빈칸

        loaded = read_history(path)
        self.assertEqual([record.english for record in loaded.records], ["apple"])
        self.assertEqual(loaded.skipped, 2)


class ReportFlowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.history_path = os.path.join(self._temp_dir.name, "study_history.csv")
        self.reports_dir = os.path.join(self._temp_dir.name, "reports")
        words = [Word(key="apple", english="apple", pos="명사", meanings=["사과"], index=0)]
        self.window = MainWindow(
            words, Settings(), Progress(),
            os.path.join(self._temp_dir.name, "progress.json"), self.history_path, self.reports_dir,
        )
        self.addCleanup(self.window.deleteLater)
        self.view = self.window._report_view

    def test_REQ011_no_history_shows_message_and_creates_no_file(self):
        self.window._on_report_requested(PERIOD_7_DAYS)
        self.assertEqual(self.view._preview.toPlainText(), NO_HISTORY_MESSAGE)
        self.assertFalse(os.path.exists(self.reports_dir))

    def test_REQ011_history_creates_report_file_and_shows_preview(self):
        with open(self.history_path, "w", encoding="utf-8", newline="") as history_file:
            history_file.write("일시,활동,세션ID,영단어,출제방향,유형,정답여부\n")
            history_file.write("2026-11-17 09:00:00,암기,,apple,암기,암기,\n")
            history_file.write("깨진 행\n")

        self.window._on_report_requested(PERIOD_ALL)

        preview = self.view._preview.toPlainText()
        self.assertIn("암기 단어 수: 1개", preview)
        self.assertIn("무시한 이력 행: 1개", preview)
        saved = os.listdir(self.reports_dir)
        self.assertEqual(len(saved), 1)
        self.assertIn(saved[0], self.view._saved_label.text())


if __name__ == "__main__":
    unittest.main()
