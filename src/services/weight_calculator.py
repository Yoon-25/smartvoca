#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 시험 출제 가중치 계산 (REQ-007)
# 파일 위치: src/services/weight_calculator.py

from datetime import date

from src.services.stats import WordStat

BASE_WEIGHT = 1.0
MIN_WEIGHT = 0.5


def weight_of(stat: WordStat | None, today: date) -> float:
    """단어 하나의 출제 가중치 (프로세스 설계 6.1절). 시험 이력이 없으면 stat은 None이다."""
    weight = BASE_WEIGHT

    if stat is None:
        weight += 3.0  # 시험 이력 없음
    else:
        rate = stat.wrong / stat.attempts
        if rate >= 0.5:
            weight += 3.0  # 오답률 50% 이상
        elif rate >= 0.2:
            weight += 1.0  # 오답률 20% 이상 50% 미만

        days = (today - stat.last_quiz_date).days
        if days >= 30:
            weight += 2.0  # 30일 이상 경과
        elif days >= 7:
            weight += 1.0  # 7일 이상 30일 미만 경과

        if stat.last_correct:
            weight -= 0.5  # 마지막 결과 정답

    return max(weight, MIN_WEIGHT)
