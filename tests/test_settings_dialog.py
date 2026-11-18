#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - 설정 대화상자와 설정 저장 흐름 테스트 (REQ-004, REQ-005, REQ-006)
# 파일 위치: tests/test_settings_dialog.py

import os
import tempfile
import unittest
from unittest import mock

# 화면을 띄우지 않고 실행한다
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import QtWidgets  # noqa: E402

from src.models.progress import Progress  # noqa: E402
from src.models.settings import Settings  # noqa: E402
from src.models.word import Word  # noqa: E402
from src.storage.json_store import load_settings  # noqa: E402
from src.ui.main_window import MainWindow  # noqa: E402
from src.ui.settings_dialog import DAY_CHANGE_QUESTION, SettingsDialog  # noqa: E402


def make_words(count: int) -> list[Word]:
    return [Word(key=f"w{i}", english=f"w{i}", pos="명사", meanings=[f"뜻{i}"], index=i) for i in range(count)]


class SettingsDialogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.dir = self._temp_dir.name

    def test_REQ005_fields_show_current_values_and_percent_for_ratios(self):
        dialog = SettingsDialog(Settings(words_per_day=30, prev_review_ratio=0.25, wrong_review_ratio=0.1,
                                         default_question_count=7), 2000)
        self.addCleanup(dialog.deleteLater)
        self.assertEqual(dialog._words_per_day.value(), 30)
        self.assertEqual(dialog._prev_ratio.value(), 25)
        self.assertEqual(dialog._wrong_ratio.value(), 10)
        self.assertEqual(dialog._question_count.value(), 7)

    def test_REQ005_result_converts_percent_back_to_decimal(self):
        dialog = SettingsDialog(Settings(), 2000)
        self.addCleanup(dialog.deleteLater)
        dialog._prev_ratio.setValue(35)
        self.assertEqual(dialog.result_settings().prev_review_ratio, 0.35)

    def test_REQ005_restore_defaults_fills_fields_without_saving(self):
        dialog = SettingsDialog(Settings(words_per_day=60), 2000)
        self.addCleanup(dialog.deleteLater)
        dialog._restore_defaults()
        self.assertEqual(dialog.result_settings(), Settings())

    def test_REQ005_changing_words_per_day_asks_before_accepting(self):
        dialog = SettingsDialog(Settings(words_per_day=20), 2000)
        self.addCleanup(dialog.deleteLater)
        dialog._words_per_day.setValue(30)

        with mock.patch.object(QtWidgets.QMessageBox, "question",
                               return_value=QtWidgets.QMessageBox.StandardButton.No) as question, \
                mock.patch.object(dialog, "accept") as accept:
            dialog._on_save_clicked()

        question.assert_called_once()
        self.assertEqual(question.call_args.args[2], DAY_CHANGE_QUESTION)
        accept.assert_not_called()

    def test_REQ005_other_changes_accept_without_asking(self):
        dialog = SettingsDialog(Settings(), 2000)
        self.addCleanup(dialog.deleteLater)
        dialog._question_count.setValue(15)

        with mock.patch.object(QtWidgets.QMessageBox, "question") as question, \
                mock.patch.object(dialog, "accept") as accept:
            dialog._on_save_clicked()

        question.assert_not_called()
        accept.assert_called_once()


class MainWindowSettingsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.dir = self._temp_dir.name
        self.settings_path = os.path.join(self.dir, "settings.json")
        self.window = MainWindow(make_words(50), Settings(), Progress(),
                                 os.path.join(self.dir, "p.json"), os.path.join(self.dir, "h.csv"),
                                 os.path.join(self.dir, "reports"), settings_path=self.settings_path)
        self.addCleanup(self.window.deleteLater)

    def test_REQ005_saved_settings_persist_and_update_quiz_setup(self):
        new_settings = Settings(words_per_day=40, prev_review_ratio=0.3, wrong_review_ratio=0.0,
                                default_question_count=12)

        class FakeDialog:
            def __init__(self, *args, **kwargs):
                pass

            def exec(self):
                return QtWidgets.QDialog.DialogCode.Accepted

            def result_settings(self):
                return new_settings

        with mock.patch("src.ui.main_window.SettingsDialog", FakeDialog):
            self.window._open_settings()

        self.assertEqual(self.window._settings, new_settings)
        self.assertEqual(load_settings(self.settings_path).settings, new_settings)
        self.assertEqual(self.window._setup_view._count.value(), 12)

    def test_REQ005_cancelled_dialog_saves_nothing(self):
        class CancelDialog:
            def __init__(self, *args, **kwargs):
                pass

            def exec(self):
                return QtWidgets.QDialog.DialogCode.Rejected

        with mock.patch("src.ui.main_window.SettingsDialog", CancelDialog):
            self.window._open_settings()

        self.assertFalse(os.path.exists(self.settings_path))


if __name__ == "__main__":
    unittest.main()
