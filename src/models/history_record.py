#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 학습 이력 한 행 데이터 클래스 (HistoryRecord)
# 파일 위치: src/models/history_record.py

from dataclasses import dataclass
from datetime import datetime

ACTIVITY_MEMORIZE = "암기"
ACTIVITY_QUIZ = "시험"
CORRECT_MARK = "O"
WRONG_MARK = "X"


@dataclass
class HistoryRecord:
    """학습 이력 한 행. 데이터 설계서 5.1절 기준이다. 영단어 비교는 소문자 키로 한다."""

    timestamp: datetime
    activity: str
    english: str
    session_id: str = ""
    direction: str = ""
    question_type: str = ""
    correct: str = ""
