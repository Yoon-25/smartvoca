#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 단어장 CSV 로드·저장 테스트 (REQ-001, REQ-002)
# 파일 위치: tests/test_storage.py

import os
import tempfile
import unittest
from unittest import mock

from src.models.word import Word
from src.storage.word_csv import WordFileError, load_words, save_words

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORD_FILE = os.path.join(PROJECT_ROOT, "data", "voca_2000.csv")
HEADER_LINE = "번호,영단어,품사,뜻\n"


class WordFileTestCase(unittest.TestCase):
    """임시 폴더에 단어 파일을 만들어 테스트하는 기반 클래스."""

    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)

    def write_file(self, body: str, name: str = "words.csv", encoding: str = "utf-8") -> str:
        path = os.path.join(self._temp_dir.name, name)
        with open(path, "w", encoding=encoding, newline="") as csv_file:
            csv_file.write(body)
        return path


class LoadWordsTest(WordFileTestCase):

    def test_REQ001_real_word_file_loads_2000_words_without_skips(self):
        result = load_words(WORD_FILE)

        self.assertEqual(len(result.words), 2000)
        self.assertEqual(result.skipped, [])
        self.assertEqual(len({word.key for word in result.words}), 2000)

    def test_REQ001_header_mismatch_raises_word_file_error(self):
        path = self.write_file("number,english,pos,meaning\n1,apple,명사,사과\n")

        with self.assertRaises(WordFileError):
            load_words(path)

    def test_REQ001_header_with_bom_is_accepted(self):
        path = self.write_file(HEADER_LINE + "1,apple,명사,사과\n", encoding="utf-8-sig")

        result = load_words(path)

        self.assertEqual([word.english for word in result.words], ["apple"])

    def test_REQ001_row_with_wrong_column_count_is_skipped_with_line_number(self):
        path = self.write_file(HEADER_LINE + "1,apple,명사,사과\n2,book,명사\n3,water,명사,물\n")

        result = load_words(path)

        self.assertEqual([word.english for word in result.words], ["apple", "water"])
        self.assertEqual(len(result.skipped), 1)
        self.assertEqual(result.skipped[0].line_no, 3)

    def test_REQ001_row_with_empty_english_or_meaning_is_skipped(self):
        path = self.write_file(HEADER_LINE + "1,,명사,사과\n2,book,명사,\n3,water,명사,물\n")

        result = load_words(path)

        self.assertEqual([word.english for word in result.words], ["water"])
        self.assertEqual([skip.line_no for skip in result.skipped], [2, 3])

    def test_REQ001_duplicate_english_keeps_first_only(self):
        path = self.write_file(HEADER_LINE + "1,Apple,명사,사과\n2,apple,명사,사과2\n")

        result = load_words(path)

        self.assertEqual(len(result.words), 1)
        self.assertEqual(result.words[0].english, "Apple")
        self.assertEqual(result.words[0].key, "apple")
        self.assertIn("중복", result.skipped[0].reason)

    def test_REQ001_pos_outside_allowed_list_is_skipped(self):
        path = self.write_file(HEADER_LINE + "1,apple,대명사,사과\n2,book,명사,책\n")

        result = load_words(path)

        self.assertEqual([word.english for word in result.words], ["book"])
        self.assertIn("품사", result.skipped[0].reason)

    def test_REQ001_meanings_are_split_by_slash(self):
        path = self.write_file(HEADER_LINE + "1,year,명사,해/연도\n")

        result = load_words(path)

        self.assertEqual(result.words[0].meanings, ["해", "연도"])

    def test_REQ001_blank_lines_are_ignored_and_index_follows_kept_order(self):
        path = self.write_file(HEADER_LINE + "1,apple,명사,사과\n\n2,,명사,빈칸\n3,book,명사,책\n")

        result = load_words(path)

        self.assertEqual([word.index for word in result.words], [0, 1])
        self.assertEqual([skip.line_no for skip in result.skipped], [4])


class SaveWordsTest(WordFileTestCase):

    def test_REQ002_saved_file_loads_back_with_same_words(self):
        original = load_words(WORD_FILE).words
        path = os.path.join(self._temp_dir.name, "copy.csv")

        save_words(path, original)
        reloaded = load_words(path)

        self.assertEqual(reloaded.skipped, [])
        self.assertEqual(
            [(w.key, w.english, w.pos, w.meanings) for w in reloaded.words],
            [(w.key, w.english, w.pos, w.meanings) for w in original],
        )

    def test_REQ002_save_renumbers_from_one(self):
        words = [
            Word(key="apple", english="apple", pos="명사", meanings=["사과"], index=5),
            Word(key="book", english="book", pos="명사", meanings=["책"], index=9),
        ]
        path = os.path.join(self._temp_dir.name, "numbered.csv")

        save_words(path, words)

        with open(path, encoding="utf-8", newline="") as csv_file:
            lines = csv_file.read().splitlines()
        self.assertEqual(lines, ["번호,영단어,품사,뜻", "1,apple,명사,사과", "2,book,명사,책"])

    def test_REQ002_failed_save_keeps_original_file_and_removes_temp(self):
        path = self.write_file(HEADER_LINE + "1,apple,명사,사과\n", name="original.csv")
        words = [Word(key="book", english="book", pos="명사", meanings=["책"])]

        with mock.patch("src.storage.atomic_write.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                save_words(path, words)

        with open(path, encoding="utf-8") as csv_file:
            self.assertEqual(csv_file.read(), HEADER_LINE + "1,apple,명사,사과\n")
        leftover = [name for name in os.listdir(self._temp_dir.name) if name.endswith(".tmp")]
        self.assertEqual(leftover, [])


if __name__ == "__main__":
    unittest.main()
