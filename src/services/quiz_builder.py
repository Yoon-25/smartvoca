#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 시험 문제 생성: 대상 추첨, 방향·유형, 보기, OX (REQ-004, REQ-007~009)
# 파일 위치: src/services/quiz_builder.py

import random
from dataclasses import dataclass, field
from datetime import date

from src.models.word import Word
from src.services.meaning_match import overlaps
from src.services.stats import WordStat
from src.services.weight_calculator import weight_of

DIRECTION_KO_EN = "한→영"
DIRECTION_EN_KO = "영→한"
DIRECTION_MIXED = "혼합"

TYPE_SHORT = "단답형"
TYPE_CHOICE = "4지선다"
TYPE_OX = "OX"

CHOICE_DISTRACTOR_COUNT = 3  # 4지선다 오답 보기 수 (보기 전체 4개)
SAME_DAY_DISTRACTOR_MAX = 3  # 같은 일차 후보를 먼저 쓰는 최대 개수 (프로세스 설계 7.4절)
OX_TRUE_PROBABILITY = 0.5


@dataclass
class QuizOptions:
    count: int
    direction: str
    question_types: list[str]
    per_day: int
    today: date


@dataclass
class Question:
    word: Word
    direction: str  # 이 문제의 실제 방향 (혼합 설정이어도 한→영 또는 영→한)
    qtype: str
    prompt: str
    choices: list[str] = field(default_factory=list)  # 4지선다 보기 (섞인 순서)
    correct: str = ""  # 4지선다: 정답 보기 문자열, OX: "O" 또는 "X"
    accepted: list[str] = field(default_factory=list)  # 단답형 정답 목록 (표시 원문)
    answer_text: str = ""  # 오답일 때 보여줄 정답 문자열


def build_quiz(words: list[Word], stats: dict[str, WordStat], options: QuizOptions,
               rng: random.Random) -> list[Question]:
    """문제 목록을 만든다. 같은 단어는 한 시험에 한 번만 나온다 (REQ-004)."""
    count = min(options.count, len(words))
    targets = _draw_targets(words, stats, count, options.today, rng)

    questions = []
    for target in targets:
        direction = _pick_direction(options.direction, rng)
        qtype = rng.choice(options.question_types)
        question = _make_question(words, target, direction, qtype, options.per_day, rng)
        questions.append(question)
    return questions


def _draw_targets(words: list[Word], stats: dict[str, WordStat], count: int, today: date,
                  rng: random.Random) -> list[Word]:
    """가중치 비례 비복원 추첨 (프로세스 설계 7.2절)."""
    pool = list(words)
    weights = [weight_of(stats.get(word.key), today) for word in pool]
    picked = []
    for _ in range(count):
        index = rng.choices(range(len(pool)), weights=weights, k=1)[0]
        picked.append(pool.pop(index))
        weights.pop(index)
    return picked


def _pick_direction(direction: str, rng: random.Random) -> str:
    if direction == DIRECTION_MIXED:
        return rng.choice([DIRECTION_KO_EN, DIRECTION_EN_KO])
    return direction


def _make_question(words, target: Word, direction: str, qtype: str, per_day: int,
                   rng: random.Random) -> Question:
    if qtype == TYPE_CHOICE:
        distractors = _distractors(words, target, CHOICE_DISTRACTOR_COUNT, per_day, rng)
        if len(distractors) == CHOICE_DISTRACTOR_COUNT:
            return _make_choice(target, distractors, direction, rng)
        qtype = TYPE_SHORT  # 후보가 부족하면 단답형으로 바꾼다 (프로세스 설계 7.4절)

    if qtype == TYPE_OX:
        return _make_ox(words, target, direction, per_day, rng)

    return _make_short(words, target, direction)


def _make_short(words, target: Word, direction: str) -> Question:
    if direction == DIRECTION_KO_EN:
        accepted = [word.english for word in words if overlaps(target, word)]
        prompt = "뜻: " + "/".join(target.meanings)
    else:
        accepted = list(target.meanings)
        prompt = target.english
    return Question(
        word=target,
        direction=direction,
        qtype=TYPE_SHORT,
        prompt=prompt,
        accepted=accepted,
        answer_text=", ".join(accepted),
    )


def _make_choice(target: Word, distractors: list[Word], direction: str, rng: random.Random) -> Question:
    if direction == DIRECTION_KO_EN:
        prompt = "뜻: " + "/".join(target.meanings)
        options = [target.english] + [word.english for word in distractors]
        correct = target.english
    else:
        prompt = target.english
        options = ["/".join(target.meanings)] + ["/".join(word.meanings) for word in distractors]
        correct = options[0]

    rng.shuffle(options)
    return Question(
        word=target,
        direction=direction,
        qtype=TYPE_CHOICE,
        prompt=prompt,
        choices=options,
        correct=correct,
        answer_text=correct,
    )


def _make_ox(words, target: Word, direction: str, per_day: int, rng: random.Random) -> Question:
    target_meaning = "/".join(target.meanings)
    is_true = rng.random() < OX_TRUE_PROBABILITY

    other = None
    if not is_true:
        found = _distractors(words, target, 1, per_day, rng)
        other = found[0] if found else None
        is_true = other is None  # 후보가 없으면 O 문제로 바꾼다

    if is_true:
        shown_english, shown_meaning = target.english, target_meaning
    else:
        shown_english, shown_meaning = other.english, "/".join(other.meanings)

    # 한→영은 뜻(T)을 먼저 보여주고, 영→한은 영단어(T)를 먼저 보여준다 (프로세스 설계 7.5절)
    if direction == DIRECTION_KO_EN:
        prompt = f"뜻: {target_meaning}  ↔  영단어: {shown_english}"
    else:
        prompt = f"영단어: {target.english}  ↔  뜻: {shown_meaning}"

    correct = "O" if is_true else "X"
    return Question(
        word=target,
        direction=direction,
        qtype=TYPE_OX,
        prompt=prompt,
        correct=correct,
        answer_text=correct,
    )


def _distractors(words, target: Word, count: int, per_day: int, rng: random.Random) -> list[Word]:
    """뜻이 겹치지 않는 후보에서 고른다. 같은 일차를 먼저 쓴다 (ADR-005, 프로세스 설계 7.4절)."""
    candidates = [word for word in words if word.key != target.key and not overlaps(target, word)]
    target_day = target.index // per_day

    same_day = [word for word in candidates if word.index // per_day == target_day]
    chosen = _sample(same_day, min(SAME_DAY_DISTRACTOR_MAX, count), rng)

    chosen_keys = {word.key for word in chosen}
    rest = [word for word in candidates if word.key not in chosen_keys]
    chosen += _sample(rest, count - len(chosen), rng)
    return chosen


def _sample(candidates: list[Word], count: int, rng: random.Random) -> list[Word]:
    if count <= 0 or not candidates:
        return []
    return rng.sample(candidates, min(count, len(candidates)))
