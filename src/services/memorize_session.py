#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 암기 진행 상태와 암기 완료 처리 (REQ-003, REQ-010)
# 파일 위치: src/services/memorize_session.py

from dataclasses import dataclass, field
from datetime import date, datetime

from src.models.history_record import ACTIVITY_MEMORIZE, HistoryRecord
from src.models.progress import Progress
from src.models.word import Word
from src.services.day_planner import StudySet

# 카드 구분 표시 (UI 설계서 4장)
KIND_NEW = "신규"
KIND_PREV_REVIEW = "전날 복습"
KIND_WRONG_REVIEW = "오답 복습"


@dataclass
class Card:
    word: Word
    kind: str


@dataclass
class MemorizeSession:
    """암기 화면의 카드 순서와 진행 상태. 화면을 모르므로 테스트하기 쉽다 (아키텍처 1장)."""

    day: int
    cards: list[Card]
    position: int = 0
    revealed: set[str] = field(default_factory=set)
    finished: bool = False

    @classmethod
    def from_study_set(cls, day: int, study: StudySet) -> "MemorizeSession":
        # 카드 순서는 신규 → 전날 복습 → 오답 복습 (프로세스 설계 3.5절)
        cards = (
            [Card(word, KIND_NEW) for word in study.new_words]
            + [Card(word, KIND_PREV_REVIEW) for word in study.prev_review_words]
            + [Card(word, KIND_WRONG_REVIEW) for word in study.wrong_review_words]
        )
        return cls(day=day, cards=cards)

    @property
    def current(self) -> Card | None:
        if not self.cards:
            return None
        return self.cards[self.position]

    @property
    def is_first(self) -> bool:
        return self.position == 0

    @property
    def is_last(self) -> bool:
        return self.position >= len(self.cards) - 1

    def previous(self) -> None:
        if not self.is_first:
            self.position -= 1

    def next(self) -> None:
        """다음 카드로 간다. 마지막 카드에서 호출하면 암기 완료 상태가 된다."""
        if self.is_last:
            self.finished = True
        else:
            self.position += 1

    def reveal(self, now: datetime) -> HistoryRecord | None:
        """현재 카드의 뜻을 연다. 카드당 세션 내 1회만 암기 이력을 만든다.

        이미 열었던 카드이거나 카드가 없으면 None을 돌려준다.
        """
        card = self.current
        if card is None or card.word.key in self.revealed:
            return None

        self.revealed.add(card.word.key)
        return HistoryRecord(
            timestamp=now,
            activity=ACTIVITY_MEMORIZE,
            english=card.word.english,
            direction="암기",
            question_type="암기",
            correct="",
        )

    def is_in_progress(self) -> bool:
        """카드를 넘기거나 뜻을 한 번이라도 연 상태이고, 아직 완료하지 않았다."""
        return not self.finished and (self.position > 0 or bool(self.revealed))

    def is_revealed(self) -> bool:
        card = self.current
        return card is not None and card.word.key in self.revealed


def complete_day(progress: Progress, day: int, today: date) -> Progress:
    """암기 완료 처리 (프로세스 설계 4장). 현재 일차는 뒤로 가지 않는다 (max 규칙)."""
    return Progress(
        current_day=max(progress.current_day, day + 1),
        last_study_date=today,
    )
