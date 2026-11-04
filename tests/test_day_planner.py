#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 일차 계산·학습 세트 구성 테스트 (REQ-005, REQ-006)
# 파일 위치: tests/test_day_planner.py

import random
import unittest
from datetime import datetime

from src.models.history_record import ACTIVITY_MEMORIZE, ACTIVITY_QUIZ, HistoryRecord
from src.models.word import Word
from src.services.day_planner import build_study_set, day_count, new_words_for_day, round_half_up
from src.services.stats import aggregate, memorized_keys


def make_words(count: int) -> list[Word]:
    return [
        Word(key=f"w{i:04d}", english=f"w{i:04d}", pos="명사", meanings=[f"뜻{i}"], index=i)
        for i in range(count)
    ]


def memorize(word: Word) -> HistoryRecord:
    return HistoryRecord(datetime(2026, 10, 1, 9, 0), ACTIVITY_MEMORIZE, word.english)


def quiz(word: Word, correct: str, when: datetime = datetime(2026, 10, 2, 9, 0)) -> HistoryRecord:
    return HistoryRecord(when, ACTIVITY_QUIZ, word.english, "S1", "한→영", "단답형", correct)


class RoundHalfUpTest(unittest.TestCase):

    def test_REQ006_half_rounds_up_not_to_even(self):
        self.assertEqual(round_half_up(2.5), 3)
        self.assertEqual(round_half_up(1.5), 2)

    def test_REQ006_float_noise_does_not_break_half(self):
        # 20 × 0.1 = 2.0000000000000004, 15 × 0.1 = 1.5 (프로세스 설계 3.6절 예시)
        self.assertEqual(round_half_up(20 * 0.1), 2)
        self.assertEqual(round_half_up(15 * 0.1), 2)


class DayCountTest(unittest.TestCase):

    def test_REQ005_2000_words_by_20_gives_100_days(self):
        self.assertEqual(day_count(2000, 20), 100)

    def test_REQ005_partial_last_day_is_counted(self):
        self.assertEqual(day_count(2001, 20), 101)


class NewWordsForDayTest(unittest.TestCase):

    def test_REQ005_word_2000_is_in_day_100(self):
        words = make_words(2000)

        day_100 = new_words_for_day(words, 100, 20)

        self.assertIn(words[1999], day_100)
        self.assertEqual(day_100[0].index, 1980)

    def test_REQ005_last_day_contains_only_remaining_words(self):
        words = make_words(2000)

        # 2000 ÷ 30 → 67일차는 20개
        self.assertEqual(len(new_words_for_day(words, 67, 30)), 20)

    def test_REQ005_day_1_is_first_n_words(self):
        words = make_words(50)

        self.assertEqual([w.index for w in new_words_for_day(words, 1, 20)], list(range(20)))


class PrevReviewTest(unittest.TestCase):

    def test_REQ006_day_1_has_no_previous_review(self):
        words = make_words(100)

        study = build_study_set(words, 1, 20, [], 0.2, 0.1, random.Random(1))

        self.assertEqual(study.prev_review_words, [])

    def test_REQ006_previous_day_review_uses_only_memorized_words(self):
        words = make_words(100)
        # 1일차(0~19) 중 짝수 번호만 암기함
        history = [memorize(w) for w in words[:20] if w.index % 2 == 0]

        study = build_study_set(words, 2, 20, history, 0.2, 0.0, random.Random(1))

        self.assertEqual(len(study.prev_review_words), 4)  # round_half_up(20 × 0.2)
        self.assertTrue(all(w.index % 2 == 0 and w.index < 20 for w in study.prev_review_words))

    def test_REQ006_no_memorization_on_previous_day_gives_empty_review(self):
        words = make_words(100)

        study = build_study_set(words, 2, 20, [], 0.2, 0.0, random.Random(1))

        self.assertEqual(study.prev_review_words, [])


class WrongReviewTest(unittest.TestCase):

    def test_REQ006_wrong_review_picks_from_top_candidates_only(self):
        words = make_words(100)
        # w0000~w0009: 모두 틀림(오답률 1.0), w0010~w0029: 절반 틀림(오답률 0.5)
        history = []
        for word in words[:10]:
            history.append(quiz(word, "X"))
        for word in words[10:30]:
            history.append(quiz(word, "O"))
            history.append(quiz(word, "X"))

        study = build_study_set(words, 5, 20, history, 0.0, 0.1, random.Random(3))

        # 오답 복습 개수 = round_half_up(20 × 0.1) = 2, 후보 상위 3배수 = 6개
        self.assertEqual(len(study.wrong_review_words), 2)
        self.assertTrue(all(w.index < 6 for w in study.wrong_review_words))

    def test_REQ006_word_without_wrong_answer_is_not_a_wrong_candidate(self):
        words = make_words(30)
        history = [quiz(words[25], "O")]

        study = build_study_set(words, 2, 20, history, 0.0, 0.1, random.Random(1))

        self.assertEqual(study.wrong_review_words, [])


class StudySetTest(unittest.TestCase):

    def test_REQ006_set_has_n_words_without_duplicates(self):
        words = make_words(200)
        history = [memorize(w) for w in words[:20]] + [quiz(words[5], "X"), quiz(words[40], "X")]

        study = build_study_set(words, 2, 20, history, 0.2, 0.1, random.Random(7))
        keys = [w.key for w in study.card_order()]

        self.assertEqual(len(keys), 20)
        self.assertEqual(len(set(keys)), len(keys))

    def test_REQ006_review_word_is_not_repeated_as_new_word(self):
        words = make_words(60)
        history = [memorize(w) for w in words[:20]] + [quiz(words[25], "X")]

        study = build_study_set(words, 2, 20, history, 0.2, 0.1, random.Random(2))
        new_keys = {w.key for w in study.new_words}
        review_keys = {w.key for w in study.prev_review_words + study.wrong_review_words}

        self.assertFalse(new_keys & review_keys)

    def test_REQ006_card_order_is_new_then_prev_then_wrong(self):
        words = make_words(60)
        history = [memorize(w) for w in words[:20]] + [quiz(words[25], "X")]

        study = build_study_set(words, 2, 20, history, 0.2, 0.1, random.Random(2))

        self.assertEqual(study.card_order()[: len(study.new_words)], study.new_words)

    def test_REQ005_last_day_set_can_be_smaller_than_n(self):
        words = make_words(2000)

        study = build_study_set(words, 67, 30, [], 0.0, 0.0, random.Random(1))

        self.assertEqual(len(study.new_words), 20)


class StatsTest(unittest.TestCase):

    def test_REQ011_aggregate_counts_only_quiz_rows(self):
        records = [
            HistoryRecord(datetime(2026, 10, 1, 9), ACTIVITY_MEMORIZE, "apple"),
            quiz(Word("apple", "apple", "명사", ["사과"]), "X", datetime(2026, 10, 1, 10)),
            quiz(Word("apple", "Apple", "명사", ["사과"]), "O", datetime(2026, 10, 3, 10)),
        ]

        stat = aggregate(records)["apple"]

        self.assertEqual((stat.attempts, stat.wrong), (2, 1))
        self.assertEqual(stat.last_correct, True)
        self.assertEqual(stat.last_quiz_date.isoformat(), "2026-10-03")

    def test_REQ006_memorized_keys_are_lowercase(self):
        records = [HistoryRecord(datetime(2026, 10, 1, 9), ACTIVITY_MEMORIZE, "Apple")]

        self.assertEqual(memorized_keys(records), {"apple"})


if __name__ == "__main__":
    unittest.main()
