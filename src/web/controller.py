#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - smartvoca - 웹 화면이 쓰는 학습 흐름: 홈 요약, 암기, 시험, 설정, 단어장, 보고서 (REQ-001~011)
# 파일 위치: src/web/controller.py

import random
import threading
from dataclasses import dataclass, field
from datetime import date, datetime

from src.models.progress import Progress
from src.models.settings import Settings
from src.models.word import Word
from src.services.day_planner import build_study_set, day_count, new_words_for_day
from src.services.grader import GradeResult
from src.services.memorize_session import MemorizeSession, complete_day
from src.services.quiz_builder import (
    DIRECTION_EN_KO,
    DIRECTION_KO_EN,
    DIRECTION_MIXED,
    TYPE_CHOICE,
    TYPE_OX,
    TYPE_SHORT,
    QuizOptions,
    build_quiz,
)
from src.services.quiz_session import QuizSession, new_session_id
from src.services.report_builder import build_report, filter_period, save_report
from src.services.stats import aggregate
from src.storage.history_csv import append_records, read_history, read_records
from src.storage.json_store import load_progress, load_settings, save_progress, save_settings
from src.services.word_editor import (
    WordInput,
    add_word,
    day_layout_changed,
    delete_word,
    find_word,
    update_word,
    validate_word_input,
)
from src.storage.word_csv import WordFileError, load_words, save_words_with_backup

NO_HISTORY_MESSAGE = "이력이 없습니다. 암기나 시험을 한 뒤 다시 시도하세요."
VALID_DIRECTIONS = (DIRECTION_KO_EN, DIRECTION_EN_KO, DIRECTION_MIXED)
VALID_TYPES = (TYPE_SHORT, TYPE_CHOICE, TYPE_OX)


@dataclass(frozen=True)
class WebPaths:
    """웹이 읽고 쓰는 파일 경로. 데스크톱과 같은 파일을 쓴다 (데이터 설계서 8절)."""

    word_file: str
    settings_file: str
    progress_file: str
    history_file: str
    reports_dir: str


@dataclass
class HomeInfo:
    day: int  # 0이면 단어장이 비어 있어 학습할 수 없음
    per_day: int
    total_words: int
    new_words: list[Word] = field(default_factory=list)
    last_study: date | None = None
    memorize_in_progress: bool = False
    quiz_in_progress: bool = False


@dataclass
class ReportResult:
    text: str = ""
    saved_path: str | None = None
    empty: bool = False  # 기간 안에 이력이 없음
    error: str = ""  # 저장 실패 원인 (미리보기만 보여 준다)


class StudyController:
    """학습 상태와 흐름을 가진다. 화면(HTML)을 모르므로 테스트하기 쉽다.

    암기·시험 세션은 서버 메모리에 둔다 (단일 사용자 로컬 실행 전제).
    모든 공개 메서드는 같은 잠금을 잡아 여러 요청이 동시에 와도 상태가 섞이지 않게 한다.
    """

    def __init__(self, paths: WebPaths, words: list[Word], skipped: list, settings: Settings,
                 progress: Progress, warnings: list[str] | None = None, load_error: str = ""):
        self._paths = paths
        self._words = words
        self._skipped = skipped
        self._settings = settings
        self._progress = progress
        self.warnings = warnings or []
        self.load_error = load_error
        self._memorize: MemorizeSession | None = None
        self._quiz: QuizSession | None = None
        self._quiz_options: QuizOptions | None = None
        self._last_result: GradeResult | None = None
        # 저장된 파일의 단어 키 순서. 초안과 비교해 일차 구성이 바뀌는지 판정한다 (ADR-013)
        self._saved_keys = [word.key for word in words]
        self._dirty = False  # 초안(메모리)에 저장하지 않은 변경이 있는지
        self._lock = threading.RLock()

    @classmethod
    def load(cls, paths: WebPaths) -> "StudyController":
        words: list[Word] = []
        skipped: list = []
        load_error = ""
        try:
            result = load_words(paths.word_file)
            words, skipped = result.words, result.skipped
        except FileNotFoundError:
            load_error = f"단어장 파일을 찾을 수 없습니다: {paths.word_file}"
        except WordFileError as error:
            load_error = f"단어장 형식 오류로 빈 단어장으로 시작합니다: {error}"

        settings_result = load_settings(paths.settings_file)
        progress = load_progress(paths.progress_file)
        return cls(paths, words, skipped, settings_result.settings, progress,
                   warnings=settings_result.warnings, load_error=load_error)

    # ---------- 공통 조회 ----------

    @property
    def words(self) -> list[Word]:
        return self._words

    @property
    def skipped(self) -> list:
        return self._skipped

    @property
    def word_dirty(self) -> bool:
        return self._dirty

    @property
    def word_file(self) -> str:
        return self._paths.word_file

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def progress(self) -> Progress:
        return self._progress

    @property
    def last_result(self) -> GradeResult | None:
        return self._last_result

    def today_day(self) -> int:
        """오늘의 일차 = min(현재 일차, 전체 일차 수). 단어가 없으면 0 (프로세스 설계 1장)."""
        with self._lock:
            return self._today_day()

    def _today_day(self) -> int:
        total = day_count(len(self._words), self._settings.words_per_day) if self._words else 0
        if total == 0:
            return 0
        return min(self._progress.current_day, total)

    def home_info(self) -> HomeInfo:
        with self._lock:
            day = self._today_day()
            per_day = self._settings.words_per_day
            new_words = new_words_for_day(self._words, day, per_day) if day else []
            return HomeInfo(
                day=day,
                per_day=per_day,
                total_words=len(self._words),
                new_words=new_words,
                last_study=self._progress.last_study_date,
                memorize_in_progress=self.memorize_in_progress(),
                quiz_in_progress=self.quiz_in_progress(),
            )

    def in_progress(self) -> bool:
        with self._lock:
            return self.memorize_in_progress() or self.quiz_in_progress()

    # ---------- 암기 ----------

    @property
    def memorize_session(self) -> MemorizeSession | None:
        return self._memorize

    def memorize_in_progress(self) -> bool:
        return self._memorize is not None and self._memorize.is_in_progress()

    def start_memorize(self) -> bool:
        """오늘 일차의 암기 세션을 시작한다. 단어가 없으면 False."""
        with self._lock:
            day = self._today_day()
            if day == 0:
                return False
            history = read_records(self._paths.history_file)
            study = build_study_set(
                self._words,
                day,
                self._settings.words_per_day,
                history,
                self._settings.prev_review_ratio,
                self._settings.wrong_review_ratio,
            )
            self._memorize = MemorizeSession.from_study_set(day, study)
            return True

    def memorize_reveal(self) -> None:
        with self._lock:
            if self._memorize is None:
                return
            record = self._memorize.reveal(datetime.now())
            if record is not None:
                append_records(self._paths.history_file, [record])

    def memorize_previous(self) -> None:
        with self._lock:
            if self._memorize is not None:
                self._memorize.previous()

    def memorize_next(self) -> int | None:
        """다음 카드로 간다. 마지막 카드에서 호출하면 암기를 완료하고 완료한 일차를 돌려준다."""
        with self._lock:
            session = self._memorize
            if session is None or session.current is None:
                return None
            if not session.is_last:
                session.next()
                return None
            session.next()  # 마지막 카드에서는 finished 상태가 된다
            day = session.day
            self._progress = complete_day(self._progress, day, date.today())
            save_progress(self._paths.progress_file, self._progress)
            self._memorize = None
            return day

    def memorize_abandon(self) -> None:
        with self._lock:
            self._memorize = None

    # ---------- 시험 ----------

    @property
    def quiz_session(self) -> QuizSession | None:
        return self._quiz

    def quiz_in_progress(self) -> bool:
        session = self._quiz
        return session is not None and not session.is_finished and (session.position > 0 or session.is_submitted)

    def start_quiz(self, count: int, direction: str, types: list[str]) -> None:
        """시험을 새로 만든다. 입력값이 잘못되면 ValueError를 던진다."""
        with self._lock:
            if not self._words:
                raise ValueError("단어장이 비어 있어 시험을 시작할 수 없습니다.")
            if not 1 <= count <= len(self._words):
                raise ValueError(f"문제 수는 1부터 {len(self._words)}까지 입력하세요.")
            if direction not in VALID_DIRECTIONS:
                raise ValueError("출제 방향을 다시 선택하세요.")
            if not types or any(qtype not in VALID_TYPES for qtype in types):
                raise ValueError("문제 유형을 하나 이상 선택하세요.")
            self._quiz_options = QuizOptions(
                count=count,
                direction=direction,
                question_types=list(types),
                per_day=self._settings.words_per_day,
                today=date.today(),
            )
            self._build_quiz()

    def retry_quiz(self) -> None:
        with self._lock:
            if self._quiz_options is None:
                raise ValueError("다시 시험할 설정이 없습니다.")
            self._build_quiz()

    def _build_quiz(self) -> None:
        stats = aggregate(read_records(self._paths.history_file))
        questions = build_quiz(self._words, stats, self._quiz_options, random.Random())
        self._quiz = QuizSession(session_id=new_session_id(datetime.now()), questions=questions)
        self._last_result = None

    def quiz_submit(self, answer: str | int) -> GradeResult:
        with self._lock:
            if self._quiz is None:
                raise RuntimeError("진행 중인 시험이 없습니다.")
            result, record = self._quiz.submit(answer, datetime.now())
            append_records(self._paths.history_file, [record])
            self._last_result = result
            return result

    def quiz_next(self) -> None:
        with self._lock:
            if self._quiz is None:
                return
            self._quiz.next()
            self._last_result = None

    def quiz_abandon(self) -> None:
        with self._lock:
            self._quiz = None
            self._last_result = None

    # ---------- 단어장 편집 (ADR-013) ----------
    # 편집은 메모리의 초안에서 한다. 저장 버튼을 눌러야 파일에 쓴다.

    def _ensure_words_editable(self) -> None:
        if self.in_progress():
            raise RuntimeError("진행 중인 학습을 끝낸 뒤 단어를 바꿔 주세요.")

    def add_word(self, data: WordInput) -> None:
        with self._lock:
            self._ensure_words_editable()
            errors = validate_word_input(data, self._words)
            if errors:
                raise ValueError(" ".join(errors))
            self._words = add_word(self._words, data)
            self._dirty = True

    def update_word(self, key: str, data: WordInput) -> None:
        with self._lock:
            self._ensure_words_editable()
            if find_word(self._words, key) is None:
                raise ValueError("단어를 찾을 수 없습니다.")
            errors = validate_word_input(data, self._words, editing_key=key)
            if errors:
                raise ValueError(" ".join(errors))
            self._words = update_word(self._words, key, data)
            self._dirty = True

    def delete_word(self, key: str) -> None:
        with self._lock:
            self._ensure_words_editable()
            if find_word(self._words, key) is None:
                raise ValueError("단어를 찾을 수 없습니다.")
            self._words = delete_word(self._words, key)
            self._dirty = True

    def word_save_warnings(self) -> list[str]:
        """저장 전에 확인받을 사항. 비어 있으면 바로 저장해도 된다."""
        with self._lock:
            warnings = []
            if day_layout_changed(self._saved_keys, self._words):
                warnings.append("단어 순서나 개수가 바뀌어 일차 구성이 달라집니다. 진도(현재 일차)는 그대로 유지됩니다.")
            if self._skipped:
                warnings.append(f"건너뛴 행 {len(self._skipped)}개는 저장하면 파일에서 사라집니다. 직전 파일은 .bak으로 남습니다.")
            return warnings

    def save_words(self, confirm: bool) -> str | None:
        """초안을 단어장 파일에 저장한다. 확인이 필요하면 확인 체크 없이는 저장하지 않는다."""
        with self._lock:
            self._ensure_words_editable()
            warnings = self.word_save_warnings()
            if warnings and not confirm:
                raise ValueError(" ".join(warnings))
            backup = save_words_with_backup(self._paths.word_file, self._words)
            self._saved_keys = [word.key for word in self._words]
            self._skipped = []
            self._dirty = False
            return backup

    def discard_word_changes(self) -> None:
        """저장하지 않은 초안을 버리고 파일에서 다시 읽는다."""
        with self._lock:
            self._ensure_words_editable()
            self._reload_from(self._paths.word_file)

    def import_words(self, path: str) -> None:
        """다른 CSV를 초안으로 읽는다. 파일에 저장하기 전까지는 바뀌지 않는다."""
        with self._lock:
            self._ensure_words_editable()
            try:
                result = load_words(path)
            except WordFileError as error:
                raise ValueError(f"단어장 형식이 맞지 않습니다: {error}") from error
            self._words = result.words
            self._skipped = result.skipped
            self._dirty = True

    def _reload_from(self, path: str) -> None:
        result = load_words(path)
        self._words = result.words
        self._skipped = result.skipped
        self._saved_keys = [word.key for word in self._words]
        self._dirty = False

    # ---------- 설정 ----------

    def update_settings(self, new_settings: Settings) -> None:
        """설정을 저장한다. 진행 중인 암기·시험이 있으면 바꾸지 않는다 (ADR-011)."""
        with self._lock:
            if self.in_progress():
                raise RuntimeError("진행 중인 학습을 끝낸 뒤 설정을 바꿔 주세요.")
            save_settings(self._paths.settings_file, new_settings)
            self._settings = new_settings

    # ---------- 보고서 ----------

    def make_report(self, period_days: int | None) -> ReportResult:
        """기간 보고서를 만들어 저장한다 (REQ-011). 이력이 없으면 파일을 만들지 않는다."""
        with self._lock:
            today = date.today()
            now = datetime.now()
            loaded = read_history(self._paths.history_file)
            if not filter_period(loaded.records, period_days, today):
                return ReportResult(empty=True)

            text = build_report(
                loaded.records,
                period_days,
                today,
                now,
                word_keys={word.key for word in self._words},
                skipped=loaded.skipped,
            )
            try:
                saved_path = save_report(text, self._paths.reports_dir, now)
            except OSError as error:
                return ReportResult(text=text, error=str(error))
            return ReportResult(text=text, saved_path=saved_path)
