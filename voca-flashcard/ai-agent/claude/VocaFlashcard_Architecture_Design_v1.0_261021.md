# 스마트 보카 아키텍처 설계서

**파일 위치**: `ai-agent/claude/VocaFlashcard_Architecture_Design_v1.0_261021.md` (초안, 승인 후 `docs/`로 이동)
**작성일**: 2026-10-21
**버전**: v1.0 (초안)
**설명**: 프로그램의 계층, 모듈 구성, 기능 분해(Function Map), 모듈 간 인터페이스를 정의한다.
**기준 문서**: `VocaFlashcard_Requirement_Spec_v1.1_261021.md` (이하 명세서), `VocaFlashcard_Decision_Records_v1.1_261021.md` (이하 ADR)

> **테일러링 메모**: 1인 학습용 단일 프로세스 데스크톱 프로그램이므로 방법론의 `Function Map`과 `Integration Spec`은 이 문서에 합쳤다. 파일 형식(CSV, JSON)의 전문 규격은 `Data Design`에 둔다.

---

## 1. 설계 원칙

1. **계층 분리**: 화면(UI)은 계산을 하지 않고, 계산(서비스)은 화면을 import 하지 않는다. 이렇게 해야 화면 없이 로직을 테스트할 수 있다.
2. **파일이 곧 저장소**: DB 없이 CSV와 JSON 파일만 사용한다 (ADR-002, ADR-003).
3. **단방향 의존**: `UI → 서비스 → 저장소/모델`. 역방향 참조는 금지한다.
4. **규칙은 한 곳에**: 일차 계산, 복습 구성, 가중치, 채점 규칙은 각각 하나의 모듈에만 있다.
5. **파일 크기**: 한 파일이 500줄을 넘으면 분리를 검토한다 (smartvoca CLAUDE.md 규칙).

---

## 2. 기술 스택

| 항목 | 선택 | 근거 |
|------|------|------|
| 언어 | Python 3.10 이상 | 명세서 NFR-006 |
| GUI | PyQt6 | ADR-001, 명세서 D3 |
| 데이터 | CSV (`csv` 표준 모듈), JSON (`json` 표준 모듈) | ADR-002, ADR-003 |
| 무작위 추출 | `random` 표준 모듈 (`random.choices`로 가중치 추첨) | 추가 설치 없음 |
| 날짜·시각 | `datetime` 표준 모듈 | 추가 설치 없음 |
| 테스트 | `unittest` 표준 모듈 | 추가 설치 없음. `pytest` 도입은 사용자 승인 후 검토 |

> **승인 필요 항목**: PyQt6 설치(`pip install PyQt6`)는 환경 변경이므로 구현 단계 시작 시 사용자 승인을 받는다.

---

## 3. 계층 구조

```
┌──────────────────────────────────────────────┐
│ UI 계층 (ui/)                                 │  PyQt6 화면, 입력 수집, 결과 표시
├──────────────────────────────────────────────┤
│ 서비스 계층 (services/)                       │  일차 계산, 복습 구성, 출제, 채점, 보고서
├──────────────────────────────────────────────┤
│ 모델 계층 (models/)                           │  Word, Settings, Progress, HistoryRecord 등
├──────────────────────────────────────────────┤
│ 저장소 계층 (storage/)                        │  CSV/JSON 읽기·쓰기, 임시 파일 교체
└──────────────────────────────────────────────┘
        │
        ▼
  data/ 폴더 (voca_2000.csv, settings.json, progress.json, study_history.csv, reports/)
```

---

## 4. 프로젝트 폴더 구조

명세서 기준 프로젝트 경로: `C:\Users\USER\Documents\dev\smartvoca\voca-flashcard`

```
voca-flashcard/
├── ai-agent/                      # Claude 작업 공간 (기존)
├── docs/                          # 확정 산출물 (기존)
├── data/                          # 단어장·이력·설정 (실행 시 사용)
│   ├── voca_2000.csv
│   ├── settings.json              # 첫 설정 저장 시 생성
│   ├── progress.json              # 첫 암기 시작 시 생성
│   ├── study_history.csv          # 첫 활동 기록 시 생성
│   └── reports/                   # 보고서 저장
├── src/                           # 소스 코드
│   ├── main.py                    # 프로그램 시작점
│   ├── models/
│   │   ├── __init__.py
│   │   ├── word.py                # Word 데이터 클래스
│   │   ├── settings.py            # Settings 데이터 클래스
│   │   ├── progress.py            # Progress 데이터 클래스
│   │   └── history_record.py      # HistoryRecord 데이터 클래스
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── word_csv.py            # 단어장 CSV 읽기·쓰기
│   │   ├── history_csv.py         # 이력 CSV 추가·읽기
│   │   ├── json_store.py          # settings.json, progress.json 읽기·쓰기
│   │   └── atomic_write.py        # 임시 파일 후 교체 공통 함수
│   ├── services/
│   │   ├── __init__.py
│   │   ├── meaning_match.py       # 뜻 겹침 판정 (ADR-005)
│   │   ├── day_planner.py         # 일차 계산, 학습 세트 구성 (REQ-005, REQ-006)
│   │   ├── weight_calculator.py   # 단어별 가중치 계산 (REQ-007)
│   │   ├── quiz_builder.py        # 시험 문제 생성 (REQ-004, REQ-007~009)
│   │   ├── grader.py              # 답안 채점 (REQ-009)
│   │   ├── stats.py               # 단어별 누적 통계 집계 (이력 → 오답률, 마지막 출제일)
│   │   └── report_builder.py      # 보고서 생성 (REQ-011)
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py         # 메인 화면, 화면 전환
│       ├── word_list_view.py      # 단어장 화면 (REQ-001, REQ-002)
│       ├── memorize_view.py       # 암기 화면 (REQ-003)
│       ├── quiz_setup_view.py     # 시험 설정 화면 (REQ-004, REQ-008, REQ-009)
│       ├── quiz_view.py           # 시험 진행 화면
│       ├── settings_dialog.py     # 설정 화면 (명세서 5절)
│       └── report_view.py         # 보고서 화면 (REQ-011)
└── tests/                         # unittest 테스트
    ├── test_meaning_match.py
    ├── test_day_planner.py
    ├── test_weight_calculator.py
    ├── test_quiz_builder.py
    ├── test_grader.py
    ├── test_storage.py
    └── test_report_builder.py
```

**테스트 폴더 위치**: `tests/`는 `src/`와 같은 레벨에 둔다. 테스트 실행 시 `src`를 경로에 추가하는 방식을 사용한다 (구현 단계에서 확정).

---

## 5. 기능 분해도 (Function Map)

| 기능 ID | 기능 | 하위 기능 | 담당 모듈 | 관련 REQ |
|--------|------|----------|----------|---------|
| F-01 | 단어 데이터 관리 | F-01-1 CSV 로드 및 검사 | `storage/word_csv.py` | REQ-001 |
| | | F-01-2 중복·빈칸 행 건너뛰기 | `storage/word_csv.py` | REQ-001 |
| | | F-01-3 단어장 저장 (임시 파일 교체) | `storage/word_csv.py`, `storage/atomic_write.py` | REQ-002 |
| F-02 | 암기 | F-02-1 오늘 학습 세트 조회 | `services/day_planner.py` | REQ-003, REQ-005 |
| | | F-02-2 카드 이동 및 완료 판정 | `ui/memorize_view.py` | REQ-003 |
| | | F-02-3 암기 이력 기록 | `storage/history_csv.py` | REQ-003, REQ-010 |
| F-03 | 진도 관리 | F-03-1 일차 수 계산 | `services/day_planner.py` | REQ-005 |
| | | F-03-2 진도 저장·갱신 | `storage/json_store.py` | REQ-005 |
| | | F-03-3 복습 단어 구성 | `services/day_planner.py` | REQ-006 |
| F-04 | 통계 집계 | F-04-1 단어별 오답률·마지막 출제일 계산 | `services/stats.py` | REQ-006, REQ-007, REQ-011 |
| F-05 | 시험 | F-05-1 출제 가중치 계산 | `services/weight_calculator.py` | REQ-007 |
| | | F-05-2 무작위 추첨 (중복 없이) | `services/quiz_builder.py` | REQ-004, REQ-007 |
| | | F-05-3 출제 방향 결정 | `services/quiz_builder.py` | REQ-008 |
| | | F-05-4 문제 유형별 문항 생성 | `services/quiz_builder.py`, `services/meaning_match.py` | REQ-009 |
| | | F-05-5 답안 채점 | `services/grader.py` | REQ-004, REQ-009 |
| | | F-05-6 시험 이력 기록 | `storage/history_csv.py` | REQ-004, REQ-010 |
| F-06 | 설정 | F-06-1 설정 값 검사 및 기본값 복원 | `models/settings.py`, `storage/json_store.py` | 명세서 5절 |
| F-07 | 이력 | F-07-1 이력 CSV 추가 및 읽기 | `storage/history_csv.py` | REQ-010 |
| F-08 | 보고서 | F-08-1 기간별 집계 | `services/report_builder.py` | REQ-011 |
| | | F-08-2 텍스트 파일 저장 | `services/report_builder.py` | REQ-011 |

---

## 6. 모듈 간 인터페이스 (Integration Spec)

이 프로그램은 하나의 프로세스 안에서 동작하므로 모듈 간 호출은 Python 함수 호출이다. 아래는 공개 함수 시그니처와 계약이다. 구현은 이 시그니처를 따른다.

### 6.1 저장소 계층

| 모듈 | 함수 | 입력 | 출력 | 실패 시 |
|------|------|------|------|---------|
| `storage/word_csv.py` | `load_words(path: str) -> LoadResult` | CSV 경로 | `LoadResult(words: list[Word], skipped: list[SkipInfo])` | 헤더 불일치 → `WordFileError` 발생 |
| `storage/word_csv.py` | `save_words(path: str, words: list[Word]) -> None` | 경로, 단어 목록 | 없음 | 쓰기 실패 → 원본 보존, `OSError` 전파 |
| `storage/history_csv.py` | `append_records(path: str, records: list[HistoryRecord]) -> None` | 경로, 기록 목록 | 없음 | 파일 없으면 헤더와 함께 생성 |
| `storage/history_csv.py` | `read_records(path: str) -> list[HistoryRecord]` | 경로 | 기록 목록 | 파일 없으면 빈 목록 |
| `storage/json_store.py` | `load_settings(path: str) -> Settings` | 경로 | `Settings` | 파일 없거나 값 오류 → 기본값 + 경고 목록 |
| `storage/json_store.py` | `save_settings(path: str, settings: Settings) -> None` | 경로, 설정 | 없음 | 임시 파일 교체 |
| `storage/json_store.py` | `load_progress(path: str) -> Progress` | 경로 | `Progress` | 파일 없으면 `current_day=1` |
| `storage/json_store.py` | `save_progress(path: str, progress: Progress) -> None` | 경로, 진도 | 없음 | 임시 파일 교체 |

### 6.2 서비스 계층

| 모듈 | 함수 | 입력 | 출력 | 관련 규칙 |
|------|------|------|------|----------|
| `services/meaning_match.py` | `meaning_tokens(meaning: str) -> set[str]` | 뜻 문자열 | "/"로 나눈 뜻 토큰 집합 (앞뒤 공백 제거) | ADR-005 |
| `services/meaning_match.py` | `overlaps(a: Word, b: Word) -> bool` | 단어 2개 | 뜻 토큰이 하나라도 같으면 True | ADR-005 |
| `services/day_planner.py` | `day_count(total_words: int, per_day: int) -> int` | 단어 수, N | 일차 수 | REQ-005 |
| `services/day_planner.py` | `new_words_for_day(words, day, per_day) -> list[Word]` | 단어장, 일차, N | 신규 단어 목록 | REQ-005 |
| `services/day_planner.py` | `build_study_set(words, day, per_day, history, ratios, prev_day_words) -> StudySet` | 단어장, 일차, 설정, 이력 | 신규·전날 복습·오답 복습 목록 | REQ-006 |
| `services/stats.py` | `aggregate(records) -> dict[str, WordStat]` | 이력 기록 | 단어별 시험 횟수, 오답 수, 마지막 출제일, 마지막 결과 | REQ-007, REQ-011 |
| `services/weight_calculator.py` | `weight_of(stat: WordStat | None, today: date) -> float` | 단어 통계, 기준일 | REQ-007 표 |
| `services/quiz_builder.py` | `build_quiz(words, stats, options, rng) -> list[Question]` | 단어장, 통계, 시험 옵션, 난수 생성기 | 문제 목록 | REQ-004, 007~009 |
| `services/grader.py` | `grade(question: Question, answer: str \| int) -> GradeResult` | 문제, 답안 | 정답 여부, 정답 표시 문자열 | REQ-009 |
| `services/report_builder.py` | `build_report(records, period_days, today) -> str` | 이력, 기간, 기준일 | 보고서 텍스트 | REQ-011 |

`rng`는 `random.Random` 객체다. 테스트에서 고정 시드를 넣어 결과를 재현한다.

### 6.3 UI 계층 호출 규칙

- UI는 `storage`와 `services`를 직접 호출한다. UI끼리는 직접 호출하지 않고 `main_window.py`를 거쳐 화면을 전환한다.
- UI는 파일 경로를 `settings`에서 읽은 기본 경로로 전달한다. 경로 상수는 `src/main.py`에 한 번만 정의한다.
- 오류는 서비스/저장소에서 예외로 올리고, UI에서 메시지 상자로 표시한다.

---

## 7. 데이터 흐름 요약

| 흐름 | 시작 | 경로 | 결과 |
|------|------|------|------|
| 앱 시작 | `main.py` | `load_words` → `load_settings` → `load_progress` | 메인 화면 표시 |
| 암기 시작 | 메인 화면 | `day_planner.build_study_set` → 암기 화면 | 카드 목록 |
| 암기 기록 | 카드 "뜻 보기" | `history_csv.append_records` | 이력 1행 추가 |
| 암기 완료 | 마지막 카드 | `save_progress` (current_day 갱신) | 다음 일차 준비 |
| 시험 출제 | 시험 시작 | `stats.aggregate` → `quiz_builder.build_quiz` | 문제 목록 |
| 답변 채점 | 답 제출 | `grader.grade` → `history_csv.append_records` | 정답 표시, 이력 행 추가 |
| 보고서 | 보고서 버튼 | `history_csv.read_records` → `report_builder.build_report` → 텍스트 파일 저장 | 파일 경로 표시 |

---

## 8. 오류 처리 원칙

| 구분 | 처리 |
|------|------|
| 단어 파일 헤더 오류 | 로드 중단, 기존 단어장 유지, 메시지 표시 |
| 단어 파일 빈칸·중복 | 건너뛰고 건너뛴 행 목록 표시 |
| 설정 값 범위 오류 | 해당 키만 기본값으로 복원, 경고 표시 |
| 설정·진도 파일 손상 (JSON 파싱 실패) | 기본값으로 시작, 손상 파일은 `*.bak`으로 이름 변경 후 보존 |
| 이력 파일 행 손상 | 해당 행 무시, 무시한 행 수 표시 |
| 쓰기 실패 | 임시 파일 삭제, 원본 유지, 메시지 표시 |
| 단어 풀 부족 (문제 수 > 단어 수) | 문제 수를 단어 수로 제한하고 안내 |

---

## 9. 비기능 설계

| 항목 | 설계 |
|------|------|
| 성능 (NFR-004) | 이력은 시작 시 한 번 읽어 메모리에 집계한다. 2,000단어 기준 채점·카드 이동은 메모리 작업이므로 0.3초 내 충분하다. |
| 데이터 안전 (NFR-002) | 모든 파일 쓰기는 `atomic_write.py`를 거친다 (임시 파일 → 교체). |
| 인코딩 (NFR-003) | 모든 `open`에 `encoding="utf-8"`을 명시한다. CSV는 `newline=""`을 사용한다. |
| 개인정보 (NFR-005) | 네트워크 호출 없음. |

---

## 10. 설계 결정 (추가 ADR 후보)

| 번호 | 결정 | 상태 |
|------|------|------|
| ADR-007 (예정) | 테스트 프레임워크: `unittest` 사용, `pytest`는 보류 | 사용자 승인 필요 |
| ADR-008 (예정) | 전날 복습 단어는 저장하지 않고 단어장 순서와 설정으로 계산 | 설계서 `Process Logic` 3.2절 참조 |

ADR-007·008은 사용자 승인 후 `Decision Records`에 추가한다.
