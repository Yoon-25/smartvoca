#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 일차 계산과 학습 세트 구성 (REQ-005, REQ-006)
# 파일 위치: src/services/day_planner.py

import math
import random
from dataclasses import dataclass, field
from collections.abc import Sequence

from src.models.history_record import HistoryRecord
from src.models.word import Word
from src.services.stats import WordStat, aggregate, memorized_keys

# 오답 복습 후보는 상위 3배수에서만 뽑는다 (프로세스 설계 3.3절)
WRONG_CANDIDATE_MULTIPLIER = 3


@dataclass
class StudySet:
    """하루 학습 세트. 저장하지 않고 암기 화면을 열 때마다 계산한다 (ADR-008)."""

    new_words: list[Word] = field(default_factory=list)
    prev_review_words: list[Word] = field(default_factory=list)
    wrong_review_words: list[Word] = field(default_factory=list)

    def card_order(self) -> list[Word]:
        """암기 카드 순서: 신규 → 전날 복습 → 오답 복습 (프로세스 설계 3.5절)."""
        return self.new_words + self.prev_review_words + self.wrong_review_words


def round_half_up(value: float) -> int:
    """0.5를 올림하는 반올림. Python round()는 짝수 쪽으로 반올림하므로 쓰지 않는다 (프로세스 설계 3.6절)."""
    # 부동소수점 오차(예: 2.4999999999)를 먼저 걷어낸다
    return math.floor(round(value, 9) + 0.5)


def day_count(total_words: int, per_day: int) -> int:
    """전체 일차 수 = 올림(단어 수 ÷ N) (REQ-005)."""
    if per_day < 1:
        raise ValueError("하루 단어 수는 1 이상이어야 합니다.")
    return math.ceil(total_words / per_day)


def new_words_for_day(words: Sequence[Word], day: int, per_day: int) -> list[Word]:
    """일차의 신규 단어 범위. 마지막 일차는 남은 단어만 담는다 (프로세스 설계 2장)."""
    start = (day - 1) * per_day
    end = min(day * per_day, len(words))
    return list(words[start:end])


def build_study_set(
    words: Sequence[Word],
    day: int,
    per_day: int,
    history: Sequence[HistoryRecord],
    prev_ratio: float,
    wrong_ratio: float,
    rng: random.Random | None = None,
) -> StudySet:
    """일차 학습 세트를 만든다 (REQ-006, 프로세스 설계 3장).

    순서: 전날 복습 → 오답 복습(전날 복습과 겹치면 제외) → 신규 단어(복습과 겹치지 않는 것, 앞에서부터).
    rng를 넘기지 않으면 무작위 생성기를 새로 만든다. 테스트에서는 고정 시드를 넣는다.
    """
    rng = rng or random.Random()

    prev_review = _prev_review_words(words, day, per_day, prev_ratio, history, rng)
    prev_keys = {word.key for word in prev_review}

    wrong_review = _wrong_review_words(words, per_day, wrong_ratio, history, prev_keys, rng)
    review_keys = prev_keys | {word.key for word in wrong_review}

    pool = [word for word in new_words_for_day(words, day, per_day) if word.key not in review_keys]
    new_count = max(0, per_day - len(prev_review) - len(wrong_review))

    return StudySet(
        new_words=pool[:new_count],
        prev_review_words=prev_review,
        wrong_review_words=wrong_review,
    )


def _prev_review_words(
    words: Sequence[Word],
    day: int,
    per_day: int,
    ratio: float,
    history: Sequence[HistoryRecord],
    rng: random.Random,
) -> list[Word]:
    """직전 일차 범위 중 암기 이력이 있는 단어에서 무작위로 고른다 (프로세스 설계 3.2절)."""
    if day <= 1:
        return []

    memorized = memorized_keys(history)
    candidates = [
        word for word in new_words_for_day(words, day - 1, per_day) if word.key in memorized
    ]
    return _sample(candidates, round_half_up(per_day * ratio), rng)


def _wrong_review_words(
    words: Sequence[Word],
    per_day: int,
    ratio: float,
    history: Sequence[HistoryRecord],
    exclude_keys: set[str],
    rng: random.Random,
) -> list[Word]:
    """오답률 상위 후보에서 무작위로 고른다 (프로세스 설계 3.3절)."""
    count = round_half_up(per_day * ratio)
    stats = aggregate(history)
    words_by_key = {word.key: word for word in words}

    ranked = sorted(
        (
            (key, stat)
            for key, stat in stats.items()
            if stat.wrong >= 1 and key in words_by_key and key not in exclude_keys
        ),
        key=lambda item: _wrong_sort_key(item[0], item[1]),
    )
    top_keys = [key for key, _ in ranked[: WRONG_CANDIDATE_MULTIPLIER * count]]
    return _sample([words_by_key[key] for key in top_keys], count, rng)


def _wrong_sort_key(key: str, stat: WordStat) -> tuple:
    # 오답률 내림차순 → 오답 수 내림차순 → 영단어 오름차순
    return (-stat.wrong_rate, -stat.wrong, key)


def _sample(candidates: list[Word], count: int, rng: random.Random) -> list[Word]:
    """후보가 부족하면 있는 만큼만 뽑는다."""
    if count <= 0 or not candidates:
        return []
    return rng.sample(candidates, min(count, len(candidates)))
