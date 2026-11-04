#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 가중치, 뜻 겹침, 문제 생성, 채점, 시험 세션 테스트 (REQ-004, REQ-007~010)
# 파일 위치: tests/test_quiz.py

import random
import unittest
from datetime import date, datetime

from src.models.history_record import ACTIVITY_QUIZ, HistoryRecord
from src.models.word import Word
from src.services.grader import grade
from src.services.meaning_match import meaning_tokens, overlaps
from src.services.quiz_builder import (
    DIRECTION_EN_KO,
    DIRECTION_KO_EN,
    DIRECTION_MIXED,
    TYPE_CHOICE,
    TYPE_OX,
    TYPE_SHORT,
    QuizOptions,
    build_quiz,
)
from src.services.quiz_session import QuizSession, new_session_id
from src.services.stats import WordStat
from src.services.weight_calculator import weight_of

TODAY = date(2026, 11, 4)
NOW = datetime(2026, 11, 4, 10, 0, 0)


def word(index: int, english: str, meanings: list[str]) -> Word:
    return Word(key=english.lower(), english=english, pos="명사", meanings=meanings, index=index)


def sample_words() -> list[Word]:
    # 0~1번은 뜻이 같다 (shop/store), 나머지는 뜻이 서로 다르다
    words = [
        word(0, "shop", ["가게"]),
        word(1, "store", ["가게", "보관하다"]),
    ]
    meanings = ["책", "물", "시간", "집", "학교", "친구", "자동차", "나무", "바다", "하늘"]
    words += [word(i + 2, f"word{i}", [meaning]) for i, meaning in enumerate(meanings)]
    return words


def options(count: int, direction: str, types: list[str]) -> QuizOptions:
    return QuizOptions(count=count, direction=direction, question_types=types, per_day=5, today=TODAY)


class WeightTest(unittest.TestCase):

    def test_REQ007_unseen_word_has_weight_4(self):
        self.assertEqual(weight_of(None, TODAY), 4.0)

    def test_REQ007_table_examples_from_process_design(self):
        # 오답률 60%, 3일 전, 마지막 오답 → 1 + 3
        high_wrong = WordStat(attempts=5, wrong=3, last_quiz_date=date(2026, 11, 1), last_correct=False)
        # 오답률 0%, 40일 전, 마지막 정답 → 1 + 2 − 0.5
        old_correct = WordStat(attempts=2, wrong=0, last_quiz_date=date(2026, 9, 25), last_correct=True)
        # 오답률 25%, 2일 전, 마지막 정답 → 1 + 1 − 0.5
        some_wrong = WordStat(attempts=4, wrong=1, last_quiz_date=date(2026, 11, 2), last_correct=True)

        self.assertEqual(weight_of(high_wrong, TODAY), 4.0)
        self.assertEqual(weight_of(old_correct, TODAY), 2.5)
        self.assertEqual(weight_of(some_wrong, TODAY), 1.5)

    def test_REQ007_minimum_weight_is_half(self):
        recent_correct_clean = WordStat(attempts=3, wrong=0, last_quiz_date=TODAY, last_correct=True)

        self.assertEqual(weight_of(recent_correct_clean, TODAY), 0.5)


class MeaningMatchTest(unittest.TestCase):

    def test_REQ009_words_sharing_a_meaning_overlap(self):
        words = sample_words()

        self.assertTrue(overlaps(words[0], words[1]))
        self.assertFalse(overlaps(words[0], words[2]))

    def test_REQ009_meaning_tokens_split_on_slash_and_trim(self):
        self.assertEqual(meaning_tokens(" 해 / 연도 "), {"해", "연도"})


class BuildQuizTest(unittest.TestCase):

    def test_REQ004_question_count_is_respected_and_words_are_unique(self):
        questions = build_quiz(sample_words(), {}, options(8, DIRECTION_KO_EN, [TYPE_SHORT]), random.Random(1))

        keys = [question.word.key for question in questions]
        self.assertEqual(len(questions), 8)
        self.assertEqual(len(set(keys)), 8)

    def test_REQ004_count_is_capped_at_word_count(self):
        questions = build_quiz(sample_words(), {}, options(99, DIRECTION_KO_EN, [TYPE_SHORT]), random.Random(1))

        self.assertEqual(len(questions), len(sample_words()))

    def test_REQ007_word_with_high_weight_is_drawn_more_often(self):
        words = sample_words()
        stats = {"word0": WordStat(attempts=2, wrong=2, last_quiz_date=date(2026, 9, 1), last_correct=False)}
        rng = random.Random(0)

        counts = {word.key: 0 for word in words}
        for _ in range(300):
            for question in build_quiz(words, stats, options(1, DIRECTION_KO_EN, [TYPE_SHORT]), rng):
                counts[question.word.key] += 1

        self.assertGreater(counts["word0"], counts["word5"])

    def test_REQ008_mixed_direction_produces_both_directions(self):
        questions = build_quiz(sample_words(), {}, options(10, DIRECTION_MIXED, [TYPE_SHORT]), random.Random(5))

        self.assertEqual({question.direction for question in questions}, {DIRECTION_KO_EN, DIRECTION_EN_KO})

    def test_REQ009_choice_question_has_four_options_including_answer_and_no_overlap(self):
        words = sample_words()
        questions = build_quiz(words, {}, options(5, DIRECTION_KO_EN, [TYPE_CHOICE]), random.Random(2))

        for question in questions:
            if question.qtype != TYPE_CHOICE:
                continue  # 후보 부족으로 단답형이 된 경우
            self.assertEqual(len(question.choices), 4)
            self.assertIn(question.correct, question.choices)
            self.assertEqual(len(set(question.choices)), 4)

    def test_REQ009_ox_question_uses_only_o_or_x_answers(self):
        questions = build_quiz(sample_words(), {}, options(10, DIRECTION_KO_EN, [TYPE_OX]), random.Random(3))

        self.assertTrue(all(question.correct in ("O", "X") for question in questions))

    def test_REQ009_short_answer_accepts_all_words_with_same_meaning(self):
        words = sample_words()
        target = words[0]  # shop
        questions = build_quiz(words, {}, options(len(words), DIRECTION_KO_EN, [TYPE_SHORT]), random.Random(4))
        question = next(q for q in questions if q.word.key == target.key)

        self.assertEqual(set(question.accepted), {"shop", "store"})


class GraderTest(unittest.TestCase):

    def short_question(self) -> object:
        questions = build_quiz(sample_words(), {}, options(len(sample_words()), DIRECTION_EN_KO, [TYPE_SHORT]),
                               random.Random(1))
        return next(q for q in questions if q.word.key == "shop")

    def test_REQ009_short_answer_ignores_case_and_spaces(self):
        question = self.short_question()

        self.assertTrue(grade(question, "  가게 ").is_correct)

    def test_REQ009_wrong_short_answer_shows_correct_answer(self):
        question = self.short_question()

        result = grade(question, "책")

        self.assertFalse(result.is_correct)
        self.assertEqual(result.message, "오답입니다. 정답: 가게")

    def test_REQ009_choice_answer_by_index_and_text(self):
        questions = build_quiz(sample_words(), {}, options(10, DIRECTION_KO_EN, [TYPE_CHOICE]), random.Random(2))
        question = next(q for q in questions if q.qtype == TYPE_CHOICE)
        correct_index = question.choices.index(question.correct)

        self.assertTrue(grade(question, correct_index).is_correct)
        self.assertTrue(grade(question, question.correct).is_correct)

    def test_REQ009_ox_answer_is_case_insensitive(self):
        questions = build_quiz(sample_words(), {}, options(10, DIRECTION_KO_EN, [TYPE_OX]), random.Random(3))
        question = questions[0]

        self.assertTrue(grade(question, question.correct.lower()).is_correct)


class QuizSessionTest(unittest.TestCase):

    def build(self) -> QuizSession:
        questions = build_quiz(sample_words(), {}, options(3, DIRECTION_KO_EN, [TYPE_SHORT]), random.Random(1))
        return QuizSession(session_id=new_session_id(NOW), questions=questions)

    def test_REQ010_session_id_format(self):
        self.assertEqual(new_session_id(NOW), "S20261104100000")

    def test_REQ004_submit_creates_one_quiz_history_row_with_session_id(self):
        session = self.build()
        question = session.current

        result, record = session.submit(question.accepted[0], NOW)

        self.assertTrue(result.is_correct)
        self.assertEqual(record.activity, ACTIVITY_QUIZ)
        self.assertEqual(record.session_id, "S20261104100000")
        self.assertEqual(record.correct, "O")
        self.assertEqual(record.english, question.word.english)

    def test_REQ004_cannot_submit_twice_for_same_question(self):
        session = self.build()
        session.submit("틀린답", NOW)

        with self.assertRaises(RuntimeError):
            session.submit("다시", NOW)

    def test_REQ004_must_submit_before_next(self):
        session = self.build()

        with self.assertRaises(RuntimeError):
            session.next()

    def test_REQ004_score_and_wrong_words_after_all_questions(self):
        session = self.build()
        for _ in range(3):
            session.submit("틀린답", NOW)
            session.next()

        self.assertTrue(session.is_finished)
        self.assertEqual(session.correct_count, 0)
        self.assertEqual(len(session.wrong_words), 3)
        self.assertEqual(session.score_text, "0 / 3 정답 (0%)")


if __name__ == "__main__":
    unittest.main()
