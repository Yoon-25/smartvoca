#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 설정·진도 JSON 저장소 테스트 (REQ-005, REQ-006)
# 파일 위치: tests/test_json_store.py

import json
import os
import tempfile
import unittest
from datetime import date

from src.models.progress import Progress
from src.models.settings import Settings
from src.storage.json_store import load_progress, load_settings, save_progress, save_settings


class JsonStoreTestCase(unittest.TestCase):

    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)

    def path(self, name: str) -> str:
        return os.path.join(self._temp_dir.name, name)

    def write(self, name: str, text: str) -> str:
        path = self.path(name)
        with open(path, "w", encoding="utf-8") as json_file:
            json_file.write(text)
        return path


class SettingsTest(JsonStoreTestCase):

    def test_REQ006_missing_file_gives_defaults_without_warnings(self):
        result = load_settings(self.path("none.json"))

        self.assertEqual(result.settings, Settings())
        self.assertEqual(result.warnings, [])

    def test_REQ005_words_per_day_out_of_range_falls_back_to_default(self):
        path = self.write("settings.json", json.dumps({"words_per_day": 500, "prev_review_ratio": 0.3}))

        result = load_settings(path)

        self.assertEqual(result.settings.words_per_day, 20)
        self.assertEqual(result.settings.prev_review_ratio, 0.3)
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("words_per_day", result.warnings[0])

    def test_REQ006_ratio_with_wrong_type_falls_back_to_default(self):
        path = self.write("settings.json", json.dumps({"wrong_review_ratio": "0.1"}))

        result = load_settings(path)

        self.assertEqual(result.settings.wrong_review_ratio, 0.1)
        self.assertIn("wrong_review_ratio", result.warnings[0])

    def test_REQ005_bool_is_not_accepted_as_integer(self):
        path = self.write("settings.json", json.dumps({"words_per_day": True}))

        result = load_settings(path)

        self.assertEqual(result.settings.words_per_day, 20)

    def test_REQ006_broken_json_is_moved_to_bak_and_defaults_used(self):
        path = self.write("settings.json", "{not json")

        result = load_settings(path)

        self.assertEqual(result.settings, Settings())
        self.assertFalse(os.path.exists(path))
        self.assertTrue(os.path.exists(path + ".bak"))

    def test_REQ006_save_then_load_round_trip(self):
        path = self.path("settings.json")
        original = Settings(words_per_day=30, prev_review_ratio=0.25, wrong_review_ratio=0.0, default_question_count=15)

        save_settings(path, original)

        self.assertEqual(load_settings(path).settings, original)


class ProgressTest(JsonStoreTestCase):

    def test_REQ005_missing_file_starts_at_day_1(self):
        self.assertEqual(load_progress(self.path("none.json")), Progress())

    def test_REQ005_broken_progress_is_moved_to_bak(self):
        path = self.write("progress.json", "[]x")

        self.assertEqual(load_progress(path), Progress())
        self.assertTrue(os.path.exists(path + ".bak"))

    def test_REQ005_day_below_1_or_bad_date_is_corrected(self):
        path = self.write("progress.json", json.dumps({"current_day": 0, "last_study_date": "2026-13-40"}))

        progress = load_progress(path)

        self.assertEqual(progress.current_day, 1)
        self.assertIsNone(progress.last_study_date)

    def test_REQ005_save_then_load_round_trip(self):
        path = self.path("progress.json")

        save_progress(path, Progress(current_day=7, last_study_date=date(2026, 10, 28)))

        self.assertEqual(load_progress(path), Progress(7, date(2026, 10, 28)))


if __name__ == "__main__":
    unittest.main()
