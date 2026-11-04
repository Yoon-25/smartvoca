#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 단어 데이터 클래스 (Word)
# 파일 위치: src/models/word.py

from dataclasses import dataclass, field


@dataclass
class Word:
    """단어장의 단어 한 개.

    key: 영단어를 소문자로 바꾼 식별 키 (데이터 설계서 2.4). 이력·통계는 번호가 아니라 이 키를 쓴다.
    index: 단어장 안에서의 0부터의 순서. 저장 시 번호는 index + 1 로 다시 매긴다.
    meanings: 뜻을 '/'로 나눈 토큰 목록 (예: "해/연도" -> ["해", "연도"]).
    """

    key: str
    english: str
    pos: str
    meanings: list[str] = field(default_factory=list)
    index: int = 0
