# 스마트 보카 아키텍처 설계서

**파일 위치**: `docs/VocaFlashcard_Architecture_Design_v1.5_261125.md` (승인, 2026-11-25)
**작성일**: 2026-10-21
**버전**: v1.5 (승인, 2026-11-25, 실행 잠금(ADR-012), 초안 보호(ADR-013) 반영: 4·6.2·11.5·11.6절 갱신)
**설명**: 프로그램의 계층, 모듈 구성, 기능 분해(Function Map), 모듈 간 인터페이스를 정의한다.
**기준 문서**: `VocaFlashcard_Requirement_Spec_v1.2_261125.md` (이하 명세서), `VocaFlashcard_Decision_Records_v1.7_261125.md` (이하 ADR)

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
| 웹 (추가) | Flask 3.x, Jinja2 템플릿 (로컬 서버 `127.0.0.1`) | ADR-012. 데스크톱 유지 |
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

웹 버전(ADR-012)은 UI 계층 자리에 `src/web/`(Flask 라우트와 템플릿)을 둔다. 웹도 서비스·저장소 계층만 호출한다. 흐름을 묶는 `src/web/controller.py`가 데스크톱 `main_window.py`와 같은 역할을 한다 (11절).

---

## 4. 프로젝트 폴더 구조

프로젝트 경로: `C:\Users\USER\Documents\dev\smartvoca` (2026-10-28 `voca-flashcard` 내용을 루트로 이동, 구조 정리)

```
smartvoca/
├── CLAUDE.md                      # 프로젝트 지침
├── .gitignore
├── .gitattributes                 # 줄바꿈 정책 (LF 저장)
├── ai-agent/                      # Claude 작업 공간 (기존)
├── docs/                          # 확정 산출물 (기존)
├── data/                          # 단어장·이력·설정 (실행 시 사용)
│   ├── voca_2000.csv
│   ├── settings.json              # 첫 설정 저장 시 생성
│   ├── progress.json              # 첫 암기 시작 시 생성
│   ├── study_history.csv          # 첫 활동 기록 시 생성
│   └── reports/                   # 보고서 저장
├── src/                           # 소스 코드
│   ├── main.py                    # 프로그램 시작점 (데스크톱)
│   ├── paths.py                   # 데스크톱·웹 공용 데이터 경로 상수 (ADR-012)
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
│   │   ├── atomic_write.py        # 임시 파일 후 교체 공통 함수
│   │   └── instance_lock.py       # 데스크톱·웹 동시 실행 방지 잠금 파일 (ADR-012)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── meaning_match.py       # 뜻 겹침 판정 (ADR-005)
│   │   ├── day_planner.py         # 일차 계산, 학습 세트 구성 (REQ-005, REQ-006)
│   │   ├── weight_calculator.py   # 단어별 가중치 계산 (REQ-007)
│   │   ├── quiz_builder.py        # 시험 문제 생성 (REQ-004, REQ-007~009)
│   │   ├── grader.py              # 답안 채점 (REQ-009)
│   │   ├── stats.py               # 단어별 누적 통계 집계 (이력 → 오답률, 마지막 출제일)
│   │   ├── memorize_session.py    # 암기 세션 상태, 완료 처리 (REQ-003)
│   │   ├── quiz_session.py        # 시험 세션 상태, 문제별 1회 채점, 이력 기록 (REQ-010)
│   │   ├── report_builder.py      # 보고서 생성 (REQ-011)
│   │   └── word_editor.py         # 단어장 편집 규칙: 입력 검사, 추가·수정·삭제, 일차 구성 변경 판정 (ADR-013)
│   ├── ui/
│       ├── __init__.py
│       ├── main_window.py         # 메인 화면, 화면 전환
│       ├── word_list_view.py      # 단어장 화면: 목록, 초안 편집, 저장 확인 (REQ-001, REQ-002, ADR-013)
│       ├── word_edit_dialog.py    # 단어 추가·수정 대화상자 (ADR-013)
│       ├── memorize_view.py       # 암기 화면 (REQ-003)
│       ├── quiz_setup_view.py     # 시험 설정 화면 (REQ-004, REQ-008, REQ-009)
│       ├── quiz_view.py           # 시험 진행 화면
│       ├── settings_dialog.py     # 설정 화면 (명세서 5절)
│       └── report_view.py         # 보고서 화면 (REQ-011)
│   └── web/                       # 웹 버전 (ADR-012, Flask, 로컬 실행)
│       ├── __init__.py
│       ├── __main__.py            # 시작점: python -m src.web (127.0.0.1:5000)
│       ├── app.py                 # Flask 라우트, 입력 검사
│       ├── controller.py          # 학습 흐름, 암기·시험 세션 보관 (REQ-001~011)
│       └── templates/             # base, home, memorize, quiz, quiz_setup, quiz_result, words, settings, report
└── tests/                         # unittest 테스트
    ├── test_day_planner.py
    ├── test_history_csv.py
    ├── test_json_store.py
    ├── test_memorize_session.py
    ├── test_quiz.py                # 뜻 판정, 가중치, 출제, 채점, 시험 세션
    ├── test_storage.py
    ├── test_report_builder.py
    ├── test_report_flow.py
    ├── test_word_list_flow.py
    ├── test_settings_dialog.py
    ├── test_shortcuts.py
    ├── test_ui_smoke.py
    ├── test_web_app.py           # 웹 흐름 (Flask test client)
    ├── test_word_editor.py       # 단어장 편집 규칙, 백업 저장 (ADR-013)
    ├── test_instance_lock.py     # 실행 잠금 (ADR-012)
    ├── test_entrypoints.py       # 데스크톱·웹 시작 모듈 점검 (ADR-012)
    └── test_word_editing_flow.py # 데스크톱 단어장 편집 흐름 (ADR-013)
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
| `storage/history_csv.py` | `read_history(path: str) -> HistoryLoad` | 경로 | `HistoryLoad(records: list[HistoryRecord], skipped: int)` | 파일 없으면 빈 결과. 형식 오류 행은 `skipped`로 센다 (REQ-011) |
| `storage/history_csv.py` | `read_records(path: str) -> list[HistoryRecord]` | 경로 | 기록 목록 | `read_history`의 `records`만 돌려주는 래퍼 |
| `storage/json_store.py` | `load_settings(path: str) -> SettingsLoadResult` | 경로 | `SettingsLoadResult(settings: Settings, warnings: list[str])` | 파일 없거나 깨짐 → 기본값, 깨진 파일은 `*.bak` 보존. 범위·타입 오류 키 → 기본값 + `warnings` |
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
| `services/day_planner.py` | `build_study_set(words, day, per_day, history, prev_ratio, wrong_ratio, rng=None) -> StudySet` | 단어장, 일차, N, 이력, 복습 비율, 난수 생성기(선택) | 신규·전날 복습·오답 복습 목록 (`card_order()`로 암기 순서 반환) | REQ-006, ADR-008 |
| `services/stats.py` | `aggregate(records) -> dict[str, WordStat]` | 이력 기록 | 단어별 시험 횟수, 오답 수, 마지막 출제일, 마지막 결과 | REQ-007, REQ-011 |
| `services/weight_calculator.py` | `weight_of(stat: WordStat | None, today: date) -> float` | 단어 통계, 기준일 | REQ-007 표 |
| `services/quiz_builder.py` | `build_quiz(words, stats, options, rng) -> list[Question]` | 단어장, 통계, 시험 옵션, 난수 생성기 | 문제 목록 | REQ-004, 007~009 |
| `services/grader.py` | `grade(question: Question, answer: str \| int) -> GradeResult` | 문제, 답안 | 정답 여부, 정답 표시 문자열 | REQ-009 |
| `services/report_builder.py` | `filter_period(records, period_days, today) -> list[HistoryRecord]` | 이력, 기간(7·30·None=전체), 기준일 | 기간 안의 이력 | 최근 N일은 오늘 포함 N일 |
| `services/report_builder.py` | `build_report(records, period_days, today, now, word_keys=None, skipped=0) -> str` | 이력, 기간, 기준일, 생성 시각, 단어장 키 집합(선택), 무시한 행 수 | 보고서 텍스트 | REQ-011. `word_keys`가 있으면 "단어장에 없는 단어" 수를 적는다. 구현 결과 반영 |
| `services/word_editor.py` | `validate_word_input(data, words, editing_key=None) -> list[str]` | 편집 입력, 단어 목록, 수정 중 키 | 오류 문구 목록 | REQ-001. 영단어 필수, 품사 4종, 뜻 1개 이상, 중복 금지 (ADR-013) |
| `services/word_editor.py` | `add_word` / `update_word` / `delete_word` | 단어 목록, 입력 또는 키 | 새 단어 목록 (번호 재부여) | 원본 목록은 바꾸지 않음 |
| `services/word_editor.py` | `day_layout_changed(saved_keys, draft) -> bool` | 저장된 키 순서, 초안 | 일차 구성이 바뀌었는지 | 키 순서 비교. 뜻·품사만 바뀌면 False (ADR-013) |
| `storage/word_csv.py` | `save_words_with_backup(path, words) -> str \| None` | 파일 경로, 단어 목록 | 백업 경로 또는 None | 저장 전 `.bak` 복사 후 원자적 교체 (ADR-013) |
| `storage/instance_lock.py` | `InstanceLock(data_dir, app_name)`, `acquire() -> None`, `release() -> None` | 데이터 폴더, 실행 이름 | 없음 | 잠금 파일 `.smartvoca.lock`. 주인 프로세스가 살아 있으면 `AlreadyRunningError`. 종료된 주인의 잠금은 치운다. 내용을 읽을 수 없는 잠금은 치우지 않고 거부한다 (ADR-012) |
| `services/report_builder.py` | `save_report(text, reports_dir, now) -> str` | 보고서 텍스트, 폴더, 생성 시각 | 저장 경로 | 같은 초 중복 시 `_2`, `_3`. 배타적 생성으로 덮어쓰지 않음 (데이터 설계서 8절) |

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
| 보고서 | 보고서 버튼 | `history_csv.read_history` → `report_builder.filter_period`(없으면 안내만) → `build_report` → `save_report` | 미리보기, 파일 경로 표시 |
| 단어장 불러오기 | 단어장 화면 "불러오기…" | `word_csv.load_words` → 메인 창이 단어 목록 교체, 홈·시험 설정 갱신 | 표 갱신, 건너뛴 행 링크 |
| 단어장 저장 | 단어장 화면 "저장…" | `word_csv.save_words` (임시 파일 교체) | 저장 완료 안내 |
| 설정 변경 | 툴바 "설정 ⚙" | `settings_dialog` (진행 중이면 차단, 하루 단어 수 변경 시 확인) → `json_store.save_settings` → 홈·시험 설정 갱신 | 변경 값 즉시 적용 |

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
| ADR-007 | 테스트 프레임워크: `unittest` 사용, `pytest`는 보류 | 확정 (Decision Records v1.2) |
| ADR-008 | 전날 복습 단어는 저장하지 않고 단어장 순서와 설정으로 계산 | 확정 (Decision Records v1.2) |
| ADR-012 | 웹 버전: Flask 로컬 서버, 데스크톱 유지 | 확정 (Decision Records v1.5) |
| ADR-013 | 단어장 편집은 메모리 초안에서 하고 저장 시 파일에 씀 | 확정 (Decision Records v1.6) |

ADR-007·008은 `Decision Records` v1.2에 추가되었다.

---

## 11. 웹 버전 구성 (v1.3 추가, ADR-012)

### 11.1 구성 원칙

- 웹은 `src/web/`에 둔다. 서비스 계층(`services/`)과 저장소 계층(`storage/`)은 데스크톱과 같은 코드를 쓴다.
- 데스크톱 `ui/main_window.py`가 맡던 학습 흐름(일차 계산 → 암기 → 진도 저장, 시험 출제 → 채점 → 이력 기록, 보고서, 설정 변경 차단)은 `src/web/controller.py`의 `StudyController`가 화면 없이 맡는다.
- `src/web/app.py`는 라우트와 입력 검사만 한다. 화면은 Jinja2 템플릿(`src/web/templates/`)이 그린다.
- 경로 상수는 `src/paths.py`에 두고 데스크톱(`src/main.py`)과 웹(`src/web/__main__.py`)이 함께 쓴다.

### 11.2 라우트

| 경로 | 메서드 | 역할 |
|------|--------|------|
| `/` | GET | 홈: 오늘 일차, 신규 단어 범위, 마지막 학습일 |
| `/memorize` | GET | 암기 카드. 세션이 없으면 시작 버튼 표시 |
| `/memorize/start` | POST | 오늘 일차 암기 세션 시작 |
| `/memorize/reveal` | POST | 뜻 보기. 카드당 1회만 암기 이력 기록 |
| `/memorize/previous` | POST | 이전 카드 |
| `/memorize/next` | POST | 다음 카드. 마지막 카드에서는 완료 처리(진도 저장) |
| `/memorize/abandon` | POST | 암기 그만두기. 진도는 바뀌지 않음 |
| `/quiz/setup` | GET | 시험 설정 (문제 수, 출제 방향, 문제 유형) |
| `/quiz/start` | POST | 시험 시작. 문제 수·방향·유형을 검사 |
| `/quiz` | GET | 현재 문제. 제출 후에는 정답 표시. 끝나면 결과 |
| `/quiz/submit` | POST | 답 제출. 문제당 1회 채점, 이력 기록 |
| `/quiz/next` | POST | 다음 문제 |
| `/quiz/retry` | POST | 같은 설정으로 다시 시험 |
| `/quiz/abandon` | POST | 시험 그만두기 |
| `/words` | GET | 단어장 조회 (영단어·뜻 검색, 건너뛴 행 표시). 읽기 전용 |
| `/settings` | GET, POST | 설정 조회·저장. 범위 검사, 하루 단어 수 변경 시 확인 체크 필수 |
| `/report` | GET, POST | 보고서 기간 선택, 생성, 파일 저장 (REQ-011) |
| `/words/new`, `/words/<key>/edit` | GET, POST | 단어 추가·수정 폼 (초안에 반영, 저장 전에는 파일이 바뀌지 않음) |
| `/words/<key>/delete` | POST | 초안에서 단어 삭제 |
| `/words/save` | POST | 초안을 단어장 파일에 저장. 일차 구성 변경·건너뛴 행이 있으면 확인 체크 필수 |
| `/words/discard` | POST | 저장하지 않은 초안을 버리고 파일 내용으로 되돌림 |
| `/words/import` | POST | CSV 업로드를 초안으로 읽음 (파일은 바뀌지 않음) |

### 11.3 데스크톱과 다른 점

- **세션 보관**: 암기·시험 진행 상태는 서버 메모리에 둔다. 서버를 끄면 진행 중 세션은 사라지고 진도와 이력 파일은 유지된다.
- **페이지 이동**: 데스크톱은 나갈 때 확인 후 진행 상황을 버린다. 웹은 페이지를 옮겨도 진행 상황을 유지하며, 다시 열면 이어서 진행한다. 새로 시작할 때만 기존 진행 상황을 버린다는 확인을 묻는다.
- **단어장**: 웹에서도 추가·수정·삭제와 저장을 한다. 편집은 초안에서 하고 "변경 저장"을 눌러야 파일에 반영된다 (11.6절, ADR-013).
- **설정**: 진행 중인 암기·시험이 있으면 저장을 막는다 (ADR-011). 하루 단어 수를 바꾸면 일차 구성이 바뀌므로 확인 체크를 해야 저장된다.

### 11.4 실행과 보안

- 실행: 프로젝트 루트에서 `python -m src.web`, 주소 `http://127.0.0.1:5000`.
- 주소를 `127.0.0.1`로 고정하고 디버그 모드를 끈다. 외부 네트워크에 열지 않는다.
- 템플릿은 자동 이스케이프를 쓴다. 단어장 내용이 HTML로 해석되지 않는다.
- 플래시 메시지 서명 키는 실행할 때마다 새로 만든다. 키를 파일에 저장하지 않는다.
- 공개 배포는 대상이 아니다 (ADR-012 제약).

### 11.5 데이터 공유

- 데스크톱과 웹은 같은 `data/` 파일(단어장, 설정, 진도, 이력, 보고서)을 쓴다.
- 데스크톱과 웹은 동시에 실행할 수 없다. 시작할 때 `data/.smartvoca.lock` 잠금을 잡고, 이미 살아 있는 실행이 있으면 거부한다 (`storage/instance_lock.py`). 종료된 실행이 남긴 잠금은 자동으로 치운다.
- 잠금이 없이 두 버전이 함께 쓰면 진도와 단어장이 마지막 저장으로 덮어써질 수 있으므로 잠금이 필요하다 (이슈 #14).


### 11.6 단어장 편집과 쓰기 (v1.4 추가, ADR-013)

- 편집 대상은 메모리 초안이다. 추가, 수정, 삭제, CSV 불러오기는 초안만 바꾸고, 저장해야 `data/voca_2000.csv`(웹) 또는 불러온 파일(데스크톱)에 쓴다.
- 저장 전 확인: 키 순서나 개수가 바뀌면 일차 구성 변경을, 건너뛴 행이 있으면 저장 시 사라짐을 알린다. 뜻·품사만 바꾸면 확인 없이 저장한다.
- 저장은 직전 파일을 `<원본>.bak`으로 복사한 뒤 원자적으로 교체한다. `.bak`은 `.gitignore`에 있다.
- 진행 중인 암기·시험이 있으면 편집, 저장, 불러오기, 취소를 모두 막는다.
- 검증 규칙과 일차 구성 판정은 `services/word_editor.py`에 있고, 데스크톱 대화상자와 웹 폼이 함께 쓴다.
- 초안 보호 (이슈 #13): 웹은 편집할 때마다 `data/voca_2000.csv.draft`에 초안을 자동 보관한다. 다음 실행 때 초안을 복원하고 안내를 띄운다. 저장하거나 변경을 취소하면 보관 파일을 지운다. 종료할 때 저장하지 않은 변경이 있으면 콘솔에 경고한다.
- 한계: 불러온 CSV의 건너뛴 행은 복원된 초안에 포함되지 않는다. 단어장 파일의 건너뛴 행만 표시된다.
- 데스크톱과 웹의 동시 편집은 잠금(11.5)으로 막는다.

---

## 변경 이력

| 버전 | 날짜 | 내용 |
|------|------|------|
| v1.0 | 2026-10-21 | 최초 작성 (초안) |
| v1.0 | 2026-10-28 | 승인, `docs/`로 이동 |
| v1.2 | 2026-11-18 | 4절 폴더 구조와 테스트 목록을 실제 구현에 맞춤. 6.1 `read_history` 추가. 6.2 `build_report` 시그니처(`now`, `word_keys`, `skipped`)와 `filter_period`, `save_report` 반영. 7절 단어장 불러오기·저장, 설정 변경 흐름 추가 |
| v1.5 | 2026-11-25 | 실행 잠금 반영 (ADR-012, `storage/instance_lock.py`): 4절 폴더 구조, 6.1절 인터페이스 표, 11.5절 데이터 공유 설명 갱신. 초안 보호 반영 (ADR-013): 11.6절 한계 설명 갱신 (이슈 #13, #14) |
| v1.4 | 2026-11-25 | 단어장 편집 반영: 4절 폴더 구조(`word_editor.py`, `word_edit_dialog.py`, 테스트 2개), 6.2절 편집 함수와 `save_words_with_backup`, 10절 ADR-013, 11.2절 단어장 라우트, 11.3절 단어장 설명 갱신, 11.6절 단어장 편집과 쓰기 추가 |
| v1.3 | 2026-11-25 | ADR-012 웹 버전 반영: 2절 기술 스택, 3절 계층, 4절 폴더 구조(`paths.py`, `web/`), 10절 ADR-012, 11절 웹 구성(라우트, 데스크톱과 차이, 실행·보안, 데이터 공유) 추가 |
| v1.1 | 2026-11-04 | 6.1 `load_settings` 반환형을 `SettingsLoadResult`로 변경 (경고 목록 전달). 6.2 `build_study_set`에서 `prev_day_words` 제거(ADR-008), 비율 인자 `prev_ratio`·`wrong_ratio`, 난수 생성기 `rng` 추가. 10절 ADR-007·008 확정 표시 |
