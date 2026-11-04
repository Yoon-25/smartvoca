#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 학습 이력에서 단어별 시험 통계와 암기 여부를 계산
# 파일 위치: src/services/stats.py

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from src.models.history_record import ACTIVITY_MEMORIZE, ACTIVITY_QUIZ, WRONG_MARK, HistoryRecord


@dataclass
class WordStat:
    """단어 하나의 시험 통계. 파일에 저장하지 않고 이력에서 매번 계산한다 (데이터 설계서 7절)."""

    attempts: int = 0
    wrong: int = 0
    last_quiz_date: date | None = None
    last_correct: bool | None = None

    @property
    def wrong_rate(self) -> float:
        return self.wrong / self.attempts if self.attempts else 0.0


def aggregate(records: Iterable[HistoryRecord]) -> dict[str, WordStat]:
    """시험 이력만 모아 단어 키별 통계를 만든다. 암기 기록은 무시한다."""
    stats: dict[str, WordStat] = {}
    latest_time = {}

    for record in records:
        if record.activity != ACTIVITY_QUIZ:
            continue

        key = record.english.lower()
        stat = stats.setdefault(key, WordStat())
        stat.attempts += 1
        if record.correct == WRONG_MARK:
            stat.wrong += 1

        # 마지막 결과는 가장 최근 시험 행 기준이다
        if key not in latest_time or record.timestamp >= latest_time[key]:
            latest_time[key] = record.timestamp
            stat.last_quiz_date = record.timestamp.date()
            stat.last_correct = record.correct != WRONG_MARK

    return stats


def memorized_keys(records: Iterable[HistoryRecord]) -> set[str]:
    """암기 이력이 한 번이라도 있는 단어의 소문자 키 집합 (프로세스 설계 3.2절)."""
    return {record.english.lower() for record in records if record.activity == ACTIVITY_MEMORIZE}
