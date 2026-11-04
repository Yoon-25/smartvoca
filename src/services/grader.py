#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 답안 채점과 결과 문구 (REQ-004, REQ-009)
# 파일 위치: src/services/grader.py

from dataclasses import dataclass

from src.services.quiz_builder import TYPE_CHOICE, TYPE_OX, TYPE_SHORT, Question

CORRECT_MESSAGE = "정답입니다."


@dataclass
class GradeResult:
    is_correct: bool
    message: str


def grade(question: Question, answer: str | int) -> GradeResult:
    """답안을 채점한다 (프로세스 설계 8장).

    단답형: 앞뒤 공백을 빼고 소문자로 맞춘 뒤 정답 목록과 비교한다.
    4지선다: 보기 번호(int) 또는 보기 문자열(str)을 받는다.
    OX: "O" 또는 "X" (대소문자 무시).
    """
    if question.qtype == TYPE_CHOICE:
        selected = _choice_text(question, answer)
        is_correct = selected == question.correct
    elif question.qtype == TYPE_OX:
        is_correct = str(answer).strip().upper() == question.correct
    elif question.qtype == TYPE_SHORT:
        typed = str(answer).strip().lower()
        is_correct = typed in {accepted.strip().lower() for accepted in question.accepted}
    else:
        raise ValueError(f"알 수 없는 문제 유형: {question.qtype}")

    message = CORRECT_MESSAGE if is_correct else f"오답입니다. 정답: {question.answer_text}"
    return GradeResult(is_correct=is_correct, message=message)


def _choice_text(question: Question, answer: str | int) -> str:
    if isinstance(answer, int):
        if 0 <= answer < len(question.choices):
            return question.choices[answer]
        return ""
    return answer
