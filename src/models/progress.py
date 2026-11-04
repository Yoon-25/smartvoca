#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 진도 데이터 클래스 (Progress)
# 파일 위치: src/models/progress.py

from dataclasses import dataclass
from datetime import date


@dataclass
class Progress:
    """진도 값. 데이터 설계서 4.1절 기준이다."""

    current_day: int = 1
    last_study_date: date | None = None
