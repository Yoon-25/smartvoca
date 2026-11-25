#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - smartvoca - 단어장 편집 규칙 테스트: 입력 검사, 추가·수정·삭제, 일차 구성 변경 판정, 백업 저장 (REQ-001, REQ-002, ADR-013)
# 파일 위치: tests/test_word_editor.py

import csv
import os
import tempfile
import unittest

from src.models.word import Word
from src.services.word_editor import (
    WordInput,
    add_word,
    day_layout_changed,
    delete_word,
    parse_meanings,
    update_word,
    validate_word_input,
)
from src.storage.word_csv import BACKUP_SUFFIX, load_words, save_words_with_backup


def _words(*english_words: str) -> list[Word]:
    return [Word(key=w.lower(), english=w, pos="명사", meanings=["뜻"], index=i)
            for i, w in enumerate(english_words)]


class ValidationTest(unittest.TestCase):

    def test_REQ001_empty_english_pos_and_meaning_are_reported(self):
        errors = validate_word_input(WordInput("  ", "없음", " / "), [])
        self.assertEqual(len(errors), 3)

    def test_REQ001_duplicate_english_is_rejected_ignoring_case(self):
        errors = validate_word_input(WordInput("Apple", "명사", "사과"), _words("apple"))
        self.assertTrue(any("이미 있는 단어" in error for error in errors))

    def test_REQ001_editing_same_word_is_not_a_duplicate(self):
        errors = validate_word_input(WordInput("apple", "명사", "사과"), _words("apple"), editing_key="apple")
        self.assertEqual(errors, [])

    def test_REQ001_parse_meanings_splits_on_slash_and_drops_blanks(self):
        self.assertEqual(parse_meanings(" 해 / 연도 // "), ["해", "연도"])


class OperationsTest(unittest.TestCase):

    def test_REQ001_add_appends_and_renumbers(self):
        result = add_word(_words("a1", "b2"), WordInput("cat", "명사", "고양이"))
        self.assertEqual([w.english for w in result], ["a1", "b2", "cat"])
        self.assertEqual([w.index for w in result], [0, 1, 2])
        self.assertEqual(result[2].key, "cat")

    def test_REQ001_update_changes_key_when_english_changes(self):
        result = update_word(_words("a1", "b2"), "a1", WordInput("ant", "명사", "개미/곤충"))
        self.assertEqual(result[0].key, "ant")
        self.assertEqual(result[0].meanings, ["개미", "곤충"])

    def test_REQ001_delete_removes_and_renumbers(self):
        result = delete_word(_words("a1", "b2", "c3"), "b2")
        self.assertEqual([w.english for w in result], ["a1", "c3"])
        self.assertEqual([w.index for w in result], [0, 1])

    def test_ADR013_meaning_only_edit_keeps_day_layout(self):
        before = _words("a1", "b2")
        after = update_word(before, "a1", WordInput("a1", "동사", "새 뜻"))
        self.assertFalse(day_layout_changed([w.key for w in before], after))

    def test_ADR013_add_or_delete_or_rename_changes_day_layout(self):
        saved = [w.key for w in _words("a1", "b2")]
        self.assertTrue(day_layout_changed(saved, add_word(_words("a1", "b2"), WordInput("c3", "명사", "뜻"))))
        self.assertTrue(day_layout_changed(saved, delete_word(_words("a1", "b2"), "a1")))
        self.assertTrue(day_layout_changed(saved, update_word(_words("a1", "b2"), "a1", WordInput("z9", "명사", "뜻"))))


class BackupSaveTest(unittest.TestCase):

    def test_ADR013_save_keeps_previous_file_as_backup(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = os.path.join(temp_dir.name, "voca.csv")
        save_words_with_backup(path, _words("a1"))
        backup = save_words_with_backup(path, _words("a1", "b2"))

        self.assertEqual(backup, path + BACKUP_SUFFIX)
        self.assertEqual(len(load_words(backup).words), 1)
        self.assertEqual(len(load_words(path).words), 2)

    def test_ADR013_first_save_creates_no_backup(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = os.path.join(temp_dir.name, "voca.csv")
        self.assertIsNone(save_words_with_backup(path, _words("a1")))
        self.assertFalse(os.path.exists(path + BACKUP_SUFFIX))


if __name__ == "__main__":
    unittest.main()
