#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 암기 진행 상태와 완료 처리 테스트 (REQ-003)
# 파일 위치: tests/test_memorize_session.py

import unittest
from datetime import date, datetime

from src.models.history_record import ACTIVITY_MEMORIZE
from src.models.progress import Progress
from src.models.word import Word
from src.services.day_planner import StudySet
from src.services.memorize_session import (
    KIND_NEW,
    KIND_PREV_REVIEW,
    KIND_WRONG_REVIEW,
    MemorizeSession,
    complete_day,
)

NOW = datetime(2026, 11, 4, 10, 0, 0)


def word(english: str) -> Word:
    return Word(key=english.lower(), english=english, pos="명사", meanings=["뜻"])


def sample_session() -> MemorizeSession:
    study = StudySet(
        new_words=[word("apple"), word("book")],
        prev_review_words=[word("cat")],
        wrong_review_words=[word("dog")],
    )
    return MemorizeSession.from_study_set(3, study)


class CardOrderTest(unittest.TestCase):

    def test_REQ003_cards_follow_new_prev_wrong_order_with_kind_labels(self):
        session = sample_session()

        self.assertEqual(
            [(card.word.english, card.kind) for card in session.cards],
            [
                ("apple", KIND_NEW),
                ("book", KIND_NEW),
                ("cat", KIND_PREV_REVIEW),
                ("dog", KIND_WRONG_REVIEW),
            ],
        )

    def test_REQ003_previous_does_nothing_on_first_card(self):
        session = sample_session()

        session.previous()

        self.assertEqual(session.position, 0)
        self.assertTrue(session.is_first)

    def test_REQ003_next_on_last_card_finishes_session(self):
        session = sample_session()
        for _ in range(3):
            session.next()
        self.assertTrue(session.is_last)
        self.assertFalse(session.finished)

        session.next()

        self.assertTrue(session.finished)
        self.assertEqual(session.position, 3)


class RevealTest(unittest.TestCase):

    def test_REQ003_reveal_creates_one_memorize_record_per_card(self):
        session = sample_session()

        first = session.reveal(NOW)
        second = session.reveal(NOW)

        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(first.activity, ACTIVITY_MEMORIZE)
        self.assertEqual(first.english, "apple")
        self.assertEqual((first.direction, first.question_type, first.correct), ("암기", "암기", ""))
        self.assertEqual(first.session_id, "")

    def test_REQ003_moving_to_another_card_allows_reveal_again_for_new_card(self):
        session = sample_session()
        session.reveal(NOW)
        session.next()

        record = session.reveal(NOW)

        self.assertEqual(record.english, "book")

    def test_REQ003_going_back_does_not_repeat_record_for_seen_card(self):
        session = sample_session()
        session.reveal(NOW)
        session.next()
        session.previous()

        self.assertIsNone(session.reveal(NOW))
        self.assertTrue(session.is_revealed())


class InProgressTest(unittest.TestCase):

    def test_REQ003_fresh_session_is_not_in_progress(self):
        self.assertFalse(sample_session().is_in_progress())

    def test_REQ003_revealing_a_card_makes_session_in_progress(self):
        session = sample_session()
        session.reveal(NOW)

        self.assertTrue(session.is_in_progress())

    def test_REQ003_finished_session_is_not_in_progress(self):
        session = sample_session()
        for _ in range(4):
            session.next()

        self.assertFalse(session.is_in_progress())


class CompleteDayTest(unittest.TestCase):

    def test_REQ005_completing_day_moves_to_next_day_and_sets_date(self):
        progress = complete_day(Progress(current_day=3), 3, date(2026, 11, 4))

        self.assertEqual(progress, Progress(current_day=4, last_study_date=date(2026, 11, 4)))

    def test_REQ005_relearning_an_old_day_does_not_move_back(self):
        progress = complete_day(Progress(current_day=10), 3, date(2026, 11, 4))

        self.assertEqual(progress.current_day, 10)


if __name__ == "__main__":
    unittest.main()
