#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 시험 세션 진행과 답안 제출 시 이력 생성 (REQ-004, REQ-010)
# 파일 위치: src/services/quiz_session.py

from dataclasses import dataclass, field
from datetime import datetime

from src.models.history_record import ACTIVITY_QUIZ, CORRECT_MARK, WRONG_MARK, HistoryRecord
from src.services.grader import GradeResult, grade
from src.services.quiz_builder import Question


def new_session_id(now: datetime) -> str:
    """세션ID = 'S' + 시각 (데이터 설계서 5.1절)."""
    return "S" + now.strftime("%Y%m%d%H%M%S")


@dataclass
class QuizSession:
    session_id: str
    questions: list[Question]
    position: int = 0
    correct_count: int = 0
    wrong_words: list[str] = field(default_factory=list)
    _submitted: bool = False

    @property
    def current(self) -> Question | None:
        if self.position >= len(self.questions):
            return None
        return self.questions[self.position]

    @property
    def is_submitted(self) -> bool:
        return self._submitted

    @property
    def is_last(self) -> bool:
        return self.position >= len(self.questions) - 1

    @property
    def is_finished(self) -> bool:
        return self.position >= len(self.questions)

    def submit(self, answer: str | int, now: datetime) -> tuple[GradeResult, HistoryRecord]:
        """현재 문제에 답한다. 한 문제당 한 번만 채점하고 이력 1행을 만든다."""
        question = self.current
        if question is None or self._submitted:
            raise RuntimeError("제출할 수 없는 상태입니다.")

        result = grade(question, answer)
        self._submitted = True
        if result.is_correct:
            self.correct_count += 1
        elif question.word.english not in self.wrong_words:
            self.wrong_words.append(question.word.english)

        record = HistoryRecord(
            timestamp=now,
            activity=ACTIVITY_QUIZ,
            english=question.word.english,
            session_id=self.session_id,
            direction=question.direction,
            question_type=question.qtype,
            correct=CORRECT_MARK if result.is_correct else WRONG_MARK,
        )
        return result, record

    def next(self) -> None:
        """제출한 뒤에만 다음 문제로 간다."""
        if not self._submitted:
            raise RuntimeError("답을 제출한 뒤 넘어갈 수 있습니다.")
        self.position += 1
        self._submitted = False

    @property
    def score_text(self) -> str:
        total = len(self.questions)
        percent = round(self.correct_count / total * 100) if total else 0
        return f"{self.correct_count} / {total} 정답 ({percent}%)"
