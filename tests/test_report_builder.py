#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - 보고서 집계·기간 필터·저장 테스트 (REQ-011)
# 파일 위치: tests/test_report_builder.py

import os
import tempfile
import unittest
from datetime import date, datetime

from src.models.history_record import ACTIVITY_MEMORIZE, ACTIVITY_QUIZ, CORRECT_MARK, WRONG_MARK, HistoryRecord
from src.services.report_builder import build_report, filter_period, save_report

TODAY = date(2026, 11, 18)
NOW = datetime(2026, 11, 18, 13, 30, 0)


def memo(day: int, english: str) -> HistoryRecord:
    return HistoryRecord(datetime(2026, 11, day, 9, 0, 0), ACTIVITY_MEMORIZE, english)


def quiz(day: int, session: str, english: str, correct: str) -> HistoryRecord:
    return HistoryRecord(
        datetime(2026, 11, day, 10, 0, 0), ACTIVITY_QUIZ, english,
        session_id=session, direction="한→영", question_type="단답형", correct=correct,
    )


class PeriodFilterTest(unittest.TestCase):

    def test_REQ011_recent_7_days_includes_today_and_six_days_before(self):
        records = [memo(12, "a"), memo(13, "b"), memo(18, "c")]  # 11/12 = 오늘-6일, 11/11 = 오늘-7일
        self.assertEqual(len(filter_period(records + [memo(11, "old")], 7, TODAY)), 3)

    def test_REQ011_all_period_keeps_every_past_record(self):
        records = [memo(1, "a"), memo(18, "b")]
        self.assertEqual(len(filter_period(records, None, TODAY)), 2)


class BuildReportTest(unittest.TestCase):

    def test_REQ011_counts_study_days_memorized_words_sessions_and_accuracy(self):
        records = [
            memo(17, "apple"), memo(18, "book"), memo(18, "Apple"),
            quiz(18, "S1", "apple", CORRECT_MARK),
            quiz(18, "S1", "book", WRONG_MARK),
            quiz(18, "S2", "cat", CORRECT_MARK),
        ]
        text = build_report(records, 7, TODAY, NOW)
        self.assertIn("학습 일수: 2일", text)
        self.assertIn("암기 단어 수: 2개", text)  # apple, book (대소문자 무시)
        self.assertIn("시험 횟수: 2회", text)
        self.assertIn("평균 정답률: 66.7% (정답 2 / 시험 3)", text)

    def test_REQ011_changing_period_changes_numbers(self):
        records = [memo(1, "old"), memo(18, "new")]
        self.assertIn("암기 단어 수: 1개", build_report(records, 7, TODAY, NOW))
        self.assertIn("암기 단어 수: 2개", build_report(records, None, TODAY, NOW))

    def test_REQ011_no_quiz_rows_shows_not_applicable(self):
        text = build_report([memo(18, "a")], 7, TODAY, NOW)
        self.assertIn("평균 정답률: 해당 없음", text)

    def test_REQ011_top_wrong_requires_three_attempts_and_sorts_by_rate(self):
        records = []
        # apple: 3회 중 2회 오답 (66.7%)
        records += [quiz(18, "S1", "apple", WRONG_MARK), quiz(17, "S2", "apple", WRONG_MARK), quiz(16, "S3", "apple", CORRECT_MARK)]
        # book: 2회만 출제 (오답률 100%지만 제외)
        records += [quiz(18, "S4", "book", WRONG_MARK), quiz(18, "S5", "book", WRONG_MARK)]
        # cat: 4회 중 1회 오답 (25%)
        records += [quiz(18, f"C{i}", "cat", WRONG_MARK if i == 0 else CORRECT_MARK) for i in range(4)]
        text = build_report(records, 7, TODAY, NOW)
        apple_pos = text.index("1. apple")
        cat_pos = text.index("2. cat")
        self.assertLess(apple_pos, cat_pos)
        self.assertNotIn("book -", text)

    def test_REQ011_unknown_words_and_skipped_rows_are_reported(self):
        records = [memo(18, "apple"), memo(18, "zzz")]
        text = build_report(records, 7, TODAY, NOW, word_keys={"apple"}, skipped=4)
        self.assertIn("단어장에 없는 단어: 1개", text)
        self.assertIn("무시한 이력 행: 4개", text)


class SaveReportTest(unittest.TestCase):

    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.reports_dir = os.path.join(self._temp_dir.name, "reports")

    def test_REQ011_saves_utf8_file_with_timestamp_name(self):
        path = save_report("내용\n", self.reports_dir, NOW)
        self.assertEqual(os.path.basename(path), "report_20261118_133000.txt")
        with open(path, encoding="utf-8") as report_file:
            self.assertEqual(report_file.read(), "내용\n")

    def test_REQ011_same_second_adds_suffix_and_never_overwrites(self):
        first = save_report("first\n", self.reports_dir, NOW)
        second = save_report("second\n", self.reports_dir, NOW)
        third = save_report("third\n", self.reports_dir, NOW)
        self.assertEqual(os.path.basename(second), "report_20261118_133000_2.txt")
        self.assertEqual(os.path.basename(third), "report_20261118_133000_3.txt")
        with open(first, encoding="utf-8") as report_file:
            self.assertEqual(report_file.read(), "first\n")


if __name__ == "__main__":
    unittest.main()
