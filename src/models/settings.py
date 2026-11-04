#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 설정 데이터 클래스 (Settings)
# 파일 위치: src/models/settings.py

from dataclasses import dataclass


@dataclass
class Settings:
    """설정 값. 기본값과 허용 범위는 데이터 설계서 6.1절 기준이다."""

    words_per_day: int = 20
    prev_review_ratio: float = 0.2
    wrong_review_ratio: float = 0.1
    default_question_count: int = 10
