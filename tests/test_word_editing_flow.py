#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - smartvoca - 데스크톱 단어장 편집 흐름 테스트: 초안 편집, 진행 중 차단, 저장 확인, 백업, 취소 (REQ-001, REQ-002, ADR-013)
# 파일 위치: tests/test_word_editing_flow.py

import os
import tempfile
import unittest
from unittest import mock

# 화면을 띄우지 않고 실행한다
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import QtWidgets  # noqa: E402

from src.models.word import Word  # noqa: E402
from src.services.word_editor import WordInput  # noqa: E402
from src.storage.word_csv import BACKUP_SUFFIX, load_words, save_words  # noqa: E402
from src.ui.word_list_view import WordListView  # noqa: E402


def make_words(count: int) -> list[Word]:
    words = []
    for index in range(count):
        english = f"word{index}"
        words.append(Word(key=english, english=english, pos="명사", meanings=["뜻"], index=index))
    return words


class WordEditingFlowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.dir = temp_dir.name
        self.path = os.path.join(self.dir, "voca.csv")
        save_words(self.path, make_words(3))

    def _view(self, busy=False) -> WordListView:
        words = load_words(self.path).words
        view = WordListView(words, [], self.path, busy_check=lambda: busy)
        self.addCleanup(view.deleteLater)
        return view

    def test_REQ001_add_edit_delete_change_draft_but_not_file(self):
        view = self._view()
        view.add_entry(WordInput("cat", "명사", "고양이"))
        view.update_entry("word0", WordInput("word0", "동사", "새 뜻/다른 뜻"))
        view.delete_entry("word1")

        self.assertTrue(view.has_unsaved_changes())
        self.assertEqual([w.english for w in view.words], ["word0", "word2", "cat"])
        self.assertEqual(view.words[0].meanings, ["새 뜻", "다른 뜻"])
        self.assertEqual(len(load_words(self.path).words), 3)

    def test_REQ001_invalid_input_is_rejected_and_draft_unchanged(self):
        view = self._view()
        with self.assertRaises(ValueError):
            view.add_entry(WordInput("word0", "명사", "중복"))
        with self.assertRaises(ValueError):
            view.add_entry(WordInput("new", "없음", "뜻"))
        self.assertEqual(len(view.words), 3)
        self.assertFalse(view.has_unsaved_changes())

    def test_ADR013_editing_is_blocked_while_learning(self):
        view = self._view(busy=True)
        with self.assertRaises(RuntimeError):
            view.add_entry(WordInput("cat", "명사", "고양이"))
        with self.assertRaises(RuntimeError):
            view.delete_entry("word0")
        self.assertEqual(len(view.words), 3)

    def test_ADR013_save_writes_file_and_keeps_backup(self):
        view = self._view()
        view.delete_entry("word0")
        with mock.patch.object(QtWidgets.QMessageBox, "question", return_value=QtWidgets.QMessageBox.StandardButton.Yes), \
                mock.patch.object(QtWidgets.QMessageBox, "information"):
            saved = view._save_to(self.path)

        self.assertTrue(saved)
        self.assertFalse(view.has_unsaved_changes())
        self.assertEqual(len(load_words(self.path).words), 2)
        self.assertEqual(len(load_words(self.path + BACKUP_SUFFIX).words), 3)

    def test_ADR013_save_is_cancelled_when_user_declines_warning(self):
        view = self._view()
        view.delete_entry("word0")
        with mock.patch.object(QtWidgets.QMessageBox, "question", return_value=QtWidgets.QMessageBox.StandardButton.No):
            saved = view._save_to(self.path)

        self.assertFalse(saved)
        self.assertTrue(view.has_unsaved_changes())
        self.assertEqual(len(load_words(self.path).words), 3)

    def test_ADR013_meaning_only_edit_saves_without_warning(self):
        view = self._view()
        view.update_entry("word0", WordInput("word0", "명사", "다른 뜻"))
        with mock.patch.object(QtWidgets.QMessageBox, "question") as question, \
                mock.patch.object(QtWidgets.QMessageBox, "information"):
            self.assertEqual(view.save_warnings(), [])
            view._save_to(self.path)
        question.assert_not_called()
        self.assertEqual(load_words(self.path).words[0].meanings, ["다른 뜻"])

    def test_ADR013_discard_restores_file_contents(self):
        view = self._view()
        view.delete_entry("word0")
        view._reload(self.path)
        self.assertFalse(view.has_unsaved_changes())
        self.assertEqual(len(view.words), 3)


if __name__ == "__main__":
    unittest.main()
