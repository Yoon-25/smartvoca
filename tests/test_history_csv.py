#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 학습 이력 CSV 테스트 (REQ-010)
# 파일 위치: tests/test_history_csv.py

import os
import tempfile
import unittest
from datetime import datetime

from src.models.history_record import ACTIVITY_MEMORIZE, ACTIVITY_QUIZ, HistoryRecord
from src.storage.history_csv import HEADER, append_records, read_records

NOW = datetime(2026, 10, 21, 14, 20, 0)


class HistoryCsvTest(unittest.TestCase):

    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.path = os.path.join(self._temp_dir.name, "data", "study_history.csv")

    def read_lines(self) -> list[str]:
        with open(self.path, encoding="utf-8", newline="") as history_file:
            return history_file.read().splitlines()

    def test_REQ010_first_append_creates_file_with_header_once(self):
        append_records(self.path, [HistoryRecord(NOW, ACTIVITY_MEMORIZE, "apple", direction="암기", question_type="암기")])
        append_records(self.path, [HistoryRecord(NOW, ACTIVITY_MEMORIZE, "book", direction="암기", question_type="암기")])

        lines = self.read_lines()

        self.assertEqual(lines[0], ",".join(HEADER))
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines.count(",".join(HEADER)), 1)

    def test_REQ010_append_and_read_round_trip(self):
        original = [
            HistoryRecord(NOW, ACTIVITY_MEMORIZE, "apple", direction="암기", question_type="암기"),
            HistoryRecord(NOW, ACTIVITY_QUIZ, "book", "S20261021142000", "영→한", "단답형", "X"),
        ]

        append_records(self.path, original)

        self.assertEqual(read_records(self.path), original)

    def test_REQ010_missing_file_reads_as_empty(self):
        self.assertEqual(read_records(self.path), [])

    def test_REQ010_malformed_rows_are_ignored(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w", encoding="utf-8", newline="") as history_file:
            history_file.write(",".join(HEADER) + "\n")
            history_file.write("2026-10-21 14:20:00,암기,,apple,암기,암기,\n")  # 정상
            history_file.write("2026-10-21 14:20:00,암기,,apple\n")  # 열 개수 오류
            history_file.write("2026/10/21 14:20:00,암기,,apple,암기,암기,\n")  # 일시 형식 오류
            history_file.write("2026-10-21 14:20:00,복습,,apple,암기,암기,\n")  # 활동 값 오류
            history_file.write("2026-10-21 14:20:00,시험,,apple,한→영,4지선다,O\n")  # 세션ID 없음

        records = read_records(self.path)

        self.assertEqual([record.activity for record in records], [ACTIVITY_MEMORIZE])


if __name__ == "__main__":
    unittest.main()
