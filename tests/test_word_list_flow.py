#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - 단어장 화면 테스트: 표시, 검색, 불러오기·저장, 메인 창 반영 (REQ-001, REQ-002)
# 파일 위치: tests/test_word_list_flow.py

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
from src.storage.word_csv import load_words  # noqa: E402
from src.ui.main_window import MainWindow  # noqa: E402
from src.ui.word_list_view import WordListView  # noqa: E402

HEADER = "번호,영단어,품사,뜻\n"


def make_words(count: int) -> list[Word]:
    return [
        Word(key=f"w{i}", english=f"w{i}", pos="명사", meanings=[f"뜻{i}"], index=i)
        for i in range(count)
    ]


class WordListViewTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.dir = self._temp_dir.name

    def write_csv(self, name: str, body: str) -> str:
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8", newline="") as csv_file:
            csv_file.write(HEADER + body)
        return path

    def test_REQ001_table_shows_every_word_and_empty_message_when_none(self):
        view = WordListView(make_words(3), [], "")
        self.addCleanup(view.deleteLater)
        self.assertEqual(view._table.rowCount(), 3)
        self.assertTrue(view._table.isVisibleTo(view))
        self.assertFalse(view._empty_label.isVisibleTo(view))

        empty_view = WordListView([], [], "")
        self.addCleanup(empty_view.deleteLater)
        self.assertFalse(empty_view._table.isVisibleTo(empty_view))
        self.assertTrue(empty_view._empty_label.isVisibleTo(empty_view))

    def test_REQ001_search_hides_rows_that_do_not_match_english_or_meaning(self):
        view = WordListView(make_words(12), [], "")
        self.addCleanup(view.deleteLater)
        view._search.setText("뜻1")  # 뜻1, 뜻10, 뜻11
        visible = [row for row in range(view._table.rowCount()) if not view._table.isRowHidden(row)]
        self.assertEqual(visible, [1, 10, 11])

    def test_REQ001_load_emits_words_and_shows_skipped_link(self):
        path = self.write_csv("words.csv", "1,apple,명사,사과\n2,,명사,빈칸\n3,book,명사,책\n")
        view = WordListView([], [], "")
        self.addCleanup(view.deleteLater)
        received = []
        view.words_loaded.connect(lambda words, skipped, p: received.append((words, skipped, p)))

        with mock.patch.object(QtWidgets.QFileDialog, "getOpenFileName", return_value=(path, "")):
            view._on_load_clicked()

        words, skipped, loaded_path = received[0]
        self.assertEqual([word.english for word in words], ["apple", "book"])
        self.assertEqual(len(skipped), 1)
        self.assertEqual(loaded_path, path)
        self.assertTrue(view._skip_label.isVisibleTo(view))

    def test_REQ001_bad_header_shows_warning_and_keeps_current_list(self):
        path = os.path.join(self.dir, "bad.csv")
        with open(path, "w", encoding="utf-8") as csv_file:
            csv_file.write("a,b,c\n1,x,y,z\n")
        view = WordListView(make_words(2), [], "")
        self.addCleanup(view.deleteLater)

        with mock.patch.object(QtWidgets.QFileDialog, "getOpenFileName", return_value=(path, "")), \
                mock.patch.object(QtWidgets.QMessageBox, "warning") as warning:
            view._on_load_clicked()

        warning.assert_called_once()
        self.assertEqual(len(view.words), 2)

    def test_REQ002_saved_file_loads_back_to_same_words(self):
        original = make_words(3)
        view = WordListView(original, [], "")
        self.addCleanup(view.deleteLater)
        path = os.path.join(self.dir, "saved.csv")

        with mock.patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=(path, "")), \
                mock.patch.object(QtWidgets.QMessageBox, "information"):
            view._on_save_as_clicked()

        reloaded = load_words(path).words
        self.assertEqual([(w.english, w.pos, w.meanings) for w in reloaded],
                         [(w.english, w.pos, w.meanings) for w in original])

    def test_REQ002_save_failure_warns_and_keeps_existing_file(self):
        view = WordListView(make_words(2), [], "")
        self.addCleanup(view.deleteLater)
        path = self.write_csv("keep.csv", "1,keep,명사,유지\n")

        with mock.patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=(path, "")), \
                mock.patch("src.ui.word_list_view.save_words_with_backup", side_effect=OSError("disk full")), \
                mock.patch.object(QtWidgets.QMessageBox, "warning") as warning:
            view._on_save_as_clicked()

        warning.assert_called_once()
        self.assertEqual(load_words(path).words[0].english, "keep")


class MainWindowWordListTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.dir = self._temp_dir.name

    def test_REQ001_loading_words_updates_home_and_quiz_setup(self):
        path = os.path.join(self.dir, "new.csv")
        with open(path, "w", encoding="utf-8", newline="") as csv_file:
            csv_file.write(HEADER + "".join(f"{i},word{i},명사,뜻{i}\n" for i in range(1, 6)))

        window = MainWindow(make_words(2), Settings(), Progress(),
                            os.path.join(self.dir, "p.json"), os.path.join(self.dir, "h.csv"),
                            os.path.join(self.dir, "reports"))
        self.addCleanup(window.deleteLater)

        with mock.patch.object(QtWidgets.QFileDialog, "getOpenFileName", return_value=(path, "")):
            window._word_list_view._on_load_clicked()

        self.assertEqual(len(window._words), 5)
        self.assertEqual(window._setup_view._count.maximum(), 5)
        self.assertIn("5개", window._status_label.text())


if __name__ == "__main__":
    unittest.main()
