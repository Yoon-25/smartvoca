#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 학습 이력 CSV 추가·읽기, 무시한 행 수 집계 (REQ-010, REQ-011)
# 파일 위치: src/storage/history_csv.py

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from src.models.history_record import ACTIVITY_MEMORIZE, ACTIVITY_QUIZ, HistoryRecord

# 데이터 설계서 5.1절: 열 순서 고정
HEADER = ["일시", "활동", "세션ID", "영단어", "출제방향", "유형", "정답여부"]
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
ALLOWED_ACTIVITIES = (ACTIVITY_MEMORIZE, ACTIVITY_QUIZ)


def append_records(path: str, records: list[HistoryRecord]) -> None:
    """이력을 끝에 덧붙인다. 파일이 없거나 비어 있으면 헤더를 먼저 쓴다.

    덧붙이기만 하므로 기존 행은 건드리지 않는다.
    """
    if not records:
        return

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    needs_header = not os.path.exists(path) or os.path.getsize(path) == 0

    with open(path, "a", encoding="utf-8", newline="") as history_file:
        writer = csv.writer(history_file)
        if needs_header:
            writer.writerow(HEADER)
        for record in records:
            writer.writerow([
                record.timestamp.strftime(TIME_FORMAT),
                record.activity,
                record.session_id,
                record.english,
                record.direction,
                record.question_type,
                record.correct,
            ])


@dataclass
class HistoryLoad:
    """이력 읽기 결과. skipped는 형식이 맞지 않아 무시한 행 수 (보고서 하단에 표시한다)."""

    records: list[HistoryRecord]
    skipped: int


def read_history(path: str) -> HistoryLoad:
    """이력을 읽고 무시한 행 수를 함께 돌려준다. 파일이 없으면 빈 결과."""
    if not os.path.exists(path):
        return HistoryLoad(records=[], skipped=0)

    records: list[HistoryRecord] = []
    skipped = 0
    with open(path, encoding="utf-8-sig", newline="") as history_file:
        reader = csv.reader(history_file)
        next(reader, None)  # 헤더 행 건너뜀
        for row in reader:
            if not row:
                continue  # 빈 줄은 무시 개수에 넣지 않는다
            record = _parse_row(row)
            if record is None:
                skipped += 1
            else:
                records.append(record)
    return HistoryLoad(records=records, skipped=skipped)


def read_records(path: str) -> list[HistoryRecord]:
    """이력을 읽는다. 파일이 없으면 빈 목록. 형식이 맞지 않는 행은 무시한다 (데이터 설계서 5.3절)."""
    return read_history(path).records


def _parse_row(row: list[str]) -> HistoryRecord | None:
    if len(row) != len(HEADER):
        return None

    timestamp_text, activity, session_id, english, direction, question_type, correct = row
    try:
        timestamp = datetime.strptime(timestamp_text, TIME_FORMAT)
    except ValueError:
        return None

    if activity not in ALLOWED_ACTIVITIES:
        return None
    # 시험 행은 세션ID와 정답여부가 반드시 있어야 한다
    if activity == ACTIVITY_QUIZ and (not session_id or not correct):
        return None

    return HistoryRecord(
        timestamp=timestamp,
        activity=activity,
        english=english,
        session_id=session_id,
        direction=direction,
        question_type=question_type,
        correct=correct,
    )
