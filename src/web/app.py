#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - smartvoca - Flask 앱: 라우트와 입력 검사, 화면은 Jinja 템플릿에 맡김 (REQ-001~011, 웹 버전)
# 파일 위치: src/web/app.py

import os
import secrets
import tempfile

from flask import Flask, flash, redirect, render_template, request, url_for

from src.models.settings import Settings
from src.services.word_editor import WordInput
from src.services.quiz_builder import TYPE_CHOICE, TYPE_OX, TYPE_SHORT, DIRECTION_EN_KO, DIRECTION_KO_EN, DIRECTION_MIXED
from src.services.report_builder import PERIOD_7_DAYS, PERIOD_30_DAYS, PERIOD_ALL, PERIOD_LABELS
from src.storage.json_store import QUESTION_COUNT_MIN, RATIO_RANGE, WORDS_PER_DAY_RANGE
from src.storage.word_csv import WordFileError
from src.web.controller import StudyController, WebPaths

# 설정 화면은 비율을 %로 보여 준다 (설정 파일은 0~0.5 소수)
RATIO_PERCENT_MAX = RATIO_RANGE[1] * 100

PERIOD_OPTIONS = [
    ("7", PERIOD_7_DAYS, PERIOD_LABELS[PERIOD_7_DAYS]),
    ("30", PERIOD_30_DAYS, PERIOD_LABELS[PERIOD_30_DAYS]),
    ("all", PERIOD_ALL, PERIOD_LABELS[PERIOD_ALL]),
]
DIRECTION_OPTIONS = [DIRECTION_KO_EN, DIRECTION_EN_KO, DIRECTION_MIXED]
TYPE_OPTIONS = [TYPE_SHORT, TYPE_CHOICE, TYPE_OX]


def create_app(paths: WebPaths, controller: StudyController | None = None,
               secret_key: str | None = None) -> Flask:
    """웹 앱을 만든다. controller를 주입하면 테스트에서 임시 파일 경로를 쓸 수 있다."""
    app = Flask(__name__)
    # 배포에서는 환경변수로 받은 고정 키를 쓴다. 로컬 실행은 매번 새로 만든다
    app.secret_key = secret_key or secrets.token_hex(16)
    ctrl = controller or StudyController.load(paths)
    app.config["CONTROLLER"] = ctrl  # 종료 경고 등 시작 스크립트가 쓴다

    @app.context_processor
    def inject_common():
        return {"in_progress": ctrl.in_progress(), "word_dirty": ctrl.word_dirty}

    # ---------- 홈 ----------

    @app.get("/")
    def home():
        return render_template(
            "home.html",
            info=ctrl.home_info(),
            load_error=ctrl.load_error,
            warnings=ctrl.warnings,
        )

    # ---------- 암기 ----------

    @app.get("/memorize")
    def memorize_page():
        session = ctrl.memorize_session
        return render_template("memorize.html", session=session, info=ctrl.home_info())

    @app.post("/memorize/start")
    def memorize_start():
        if not ctrl.start_memorize():
            flash("학습할 단어가 없습니다. 단어장을 확인하세요.", "error")
            return redirect(url_for("home"))
        return redirect(url_for("memorize_page"))

    @app.post("/memorize/reveal")
    def memorize_reveal():
        ctrl.memorize_reveal()
        return redirect(url_for("memorize_page"))

    @app.post("/memorize/previous")
    def memorize_previous():
        ctrl.memorize_previous()
        return redirect(url_for("memorize_page"))

    @app.post("/memorize/next")
    def memorize_next():
        completed_day = ctrl.memorize_next()
        if completed_day is None:
            return redirect(url_for("memorize_page"))
        flash(f"{completed_day}일차 암기를 마쳤습니다. 다음 학습은 {ctrl.today_day()}일차입니다.", "success")
        return redirect(url_for("home"))

    @app.post("/memorize/abandon")
    def memorize_abandon():
        ctrl.memorize_abandon()
        flash("진행 중이던 암기를 그만뒀습니다. 진도는 바뀌지 않았습니다.", "info")
        return redirect(url_for("home"))

    # ---------- 시험 ----------

    @app.get("/quiz/setup")
    def quiz_setup_page():
        if not ctrl.words:
            flash("단어장이 비어 있어 시험을 시작할 수 없습니다.", "error")
            return redirect(url_for("home"))
        return render_template(
            "quiz_setup.html",
            word_count=len(ctrl.words),
            default_count=min(ctrl.settings.default_question_count, len(ctrl.words)),
            directions=DIRECTION_OPTIONS,
            types=TYPE_OPTIONS,
            quiz_in_progress=ctrl.quiz_in_progress(),
        )

    @app.post("/quiz/start")
    def quiz_start():
        try:
            count = _parse_int(request.form.get("count"), "문제 수")
            direction = request.form.get("direction", "")
            types = request.form.getlist("types")
            ctrl.start_quiz(count, direction, types)
        except ValueError as error:
            flash(str(error), "error")
            return redirect(url_for("quiz_setup_page"))
        return redirect(url_for("quiz_page"))

    @app.get("/quiz")
    def quiz_page():
        session = ctrl.quiz_session
        if session is None:
            return redirect(url_for("quiz_setup_page"))
        if session.is_finished:
            return render_template("quiz_result.html", session=session)
        return render_template("quiz.html", session=session, result=ctrl.last_result)

    @app.post("/quiz/submit")
    def quiz_submit():
        session = ctrl.quiz_session
        if session is None or session.current is None or session.is_submitted:
            return redirect(url_for("quiz_page"))
        if session.current.qtype == TYPE_CHOICE:
            # 4지선다는 보기 번호(0~3)로 받는다. 번호가 없거나 잘못되면 다시 고르게 한다
            try:
                answer: str | int = int(request.form.get("choice", ""))
            except ValueError:
                flash("보기를 하나 고르세요.", "error")
                return redirect(url_for("quiz_page"))
        else:
            # 단답형은 입력 칸, OX는 O·X 버튼 값이 같은 이름으로 온다
            answer = request.form.get("answer", "")
        ctrl.quiz_submit(answer)
        return redirect(url_for("quiz_page"))

    @app.post("/quiz/next")
    def quiz_next():
        ctrl.quiz_next()
        return redirect(url_for("quiz_page"))

    @app.post("/quiz/retry")
    def quiz_retry():
        try:
            ctrl.retry_quiz()
        except ValueError as error:
            flash(str(error), "error")
            return redirect(url_for("quiz_setup_page"))
        return redirect(url_for("quiz_page"))

    @app.post("/quiz/abandon")
    def quiz_abandon():
        ctrl.quiz_abandon()
        return redirect(url_for("home"))

    # ---------- 단어장 ----------

    @app.get("/words")
    def words_page():
        query = request.args.get("q", "").strip().lower()
        words = ctrl.words
        if query:
            words = [
                word for word in words
                if query in word.english.lower() or any(query in meaning.lower() for meaning in word.meanings)
            ]
        return render_template(
            "words.html",
            words=words,
            query=request.args.get("q", "").strip(),
            total=len(ctrl.words),
            skipped=ctrl.skipped,
            word_file=ctrl.word_file,
            load_error=ctrl.load_error,
            save_warnings=ctrl.word_save_warnings(),
            draft_restored=ctrl.draft_restored,
            draft_error=ctrl.draft_error,
        )

    @app.get("/words/new")
    def word_new_page():
        return render_template("word_form.html", word=None, form=_empty_form(), errors=[], action=url_for("word_create"))

    @app.post("/words/new")
    def word_create():
        data = _word_input_from_form(request.form)
        try:
            ctrl.add_word(data)
        except (ValueError, RuntimeError) as error:
            return render_template("word_form.html", word=None, form=request.form, errors=[str(error)],
                                   action=url_for("word_create"))
        flash("단어를 추가했습니다. 저장해야 파일에 반영됩니다.", "success")
        return redirect(url_for("words_page"))

    @app.get("/words/<path:key>/edit")
    def word_edit_page(key: str):
        word = _find_word_or_none(ctrl, key)
        if word is None:
            flash("단어를 찾을 수 없습니다.", "error")
            return redirect(url_for("words_page"))
        return render_template("word_form.html", word=word, form=_form_from_word(word), errors=[],
                               action=url_for("word_update", key=key))

    @app.post("/words/<path:key>/edit")
    def word_update(key: str):
        data = _word_input_from_form(request.form)
        try:
            ctrl.update_word(key, data)
        except (ValueError, RuntimeError) as error:
            word = _find_word_or_none(ctrl, key)
            return render_template("word_form.html", word=word, form=request.form, errors=[str(error)],
                                   action=url_for("word_update", key=key))
        flash("단어를 고쳤습니다. 저장해야 파일에 반영됩니다.", "success")
        return redirect(url_for("words_page"))

    @app.post("/words/<path:key>/delete")
    def word_delete(key: str):
        try:
            ctrl.delete_word(key)
            flash("단어를 삭제했습니다. 저장해야 파일에 반영됩니다.", "success")
        except (ValueError, RuntimeError) as error:
            flash(str(error), "error")
        return redirect(url_for("words_page"))

    @app.post("/words/save")
    def words_save():
        confirm = bool(request.form.get("confirm_change"))
        try:
            backup = ctrl.save_words(confirm=confirm)
        except ValueError as error:
            flash(f"{error} 확인 체크 후 다시 저장하세요.", "error")
            return redirect(url_for("words_page"))
        except RuntimeError as error:
            flash(str(error), "error")
            return redirect(url_for("words_page"))
        except OSError as error:
            flash(f"파일을 저장하지 못했습니다. 기존 파일은 그대로 있습니다. (원인: {error})", "error")
            return redirect(url_for("words_page"))
        message = "단어장을 저장했습니다."
        if backup:
            message += f" 직전 파일은 {backup}에 남겼습니다."
        flash(message, "success")
        return redirect(url_for("words_page"))

    @app.post("/words/discard")
    def words_discard():
        if ctrl.word_dirty and not request.form.get("confirm_discard"):
            flash("저장하지 않은 변경이 사라집니다. 확인 체크 후 다시 시도하세요.", "error")
            return redirect(url_for("words_page"))
        try:
            ctrl.discard_word_changes()
        except (RuntimeError, OSError, WordFileError) as error:
            flash(f"파일을 다시 읽지 못했습니다. ({error})", "error")
            return redirect(url_for("words_page"))
        flash("저장하지 않은 변경을 버리고 파일 내용으로 되돌렸습니다.", "info")
        return redirect(url_for("words_page"))

    @app.post("/words/import")
    def words_import():
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            flash("불러올 CSV 파일을 선택하세요.", "error")
            return redirect(url_for("words_page"))
        if ctrl.word_dirty and not request.form.get("confirm_discard"):
            flash("저장하지 않은 변경이 사라집니다. 확인 체크 후 다시 불러오세요.", "error")
            return redirect(url_for("words_page"))
        fd, temp_path = tempfile.mkstemp(suffix=".csv")
        try:
            with os.fdopen(fd, "wb") as temp_file:
                upload.save(temp_file)
            ctrl.import_words(temp_path)
        except (ValueError, RuntimeError) as error:
            flash(str(error), "error")
            return redirect(url_for("words_page"))
        except (OSError, UnicodeDecodeError) as error:
            flash(f"파일을 읽지 못했습니다. ({error})", "error")
            return redirect(url_for("words_page"))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        flash("불러온 단어장을 초안으로 놓았습니다. 저장해야 파일에 반영됩니다.", "success")
        return redirect(url_for("words_page"))

    # ---------- 설정 ----------

    @app.get("/settings")
    def settings_page():
        return render_template(
            "settings.html",
            values=_settings_form_values(ctrl.settings),
            word_count=len(ctrl.words),
            ranges=_setting_ranges(len(ctrl.words)),
            in_progress=ctrl.in_progress(),
        )

    @app.post("/settings")
    def settings_save():
        if ctrl.in_progress():
            flash("진행 중인 학습을 끝낸 뒤 설정을 바꿔 주세요.", "error")
            return redirect(url_for("settings_page"))
        try:
            new_settings = _parse_settings(request.form, len(ctrl.words))
        except ValueError as error:
            flash(str(error), "error")
            return redirect(url_for("settings_page"))

        # 하루 단어 수가 바뀌면 일차 구성이 바뀐다. 확인 체크를 해야 저장한다 (UI 설계서 7장)
        changed_per_day = new_settings.words_per_day != ctrl.settings.words_per_day
        if changed_per_day and not request.form.get("confirm_change"):
            flash("하루 단어 수를 바꾸면 일차 구성이 바뀝니다. 확인 체크 후 다시 저장하세요.", "error")
            return redirect(url_for("settings_page"))

        try:
            ctrl.update_settings(new_settings)
        except OSError as error:
            flash(f"설정을 저장하지 못했습니다. 기존 설정은 그대로 있습니다. (원인: {error})", "error")
            return redirect(url_for("settings_page"))
        except RuntimeError as error:
            flash(str(error), "error")
            return redirect(url_for("settings_page"))
        flash("설정을 저장했습니다.", "success")
        return redirect(url_for("home"))

    # ---------- 보고서 ----------

    @app.get("/report")
    def report_page():
        return render_template("report.html", periods=PERIOD_OPTIONS, selected="7", result=None)

    @app.post("/report")
    def report_create():
        selected = request.form.get("period", "7")
        period_days = next((days for key, days, _label in PERIOD_OPTIONS if key == selected), PERIOD_7_DAYS)
        result = ctrl.make_report(period_days)
        return render_template("report.html", periods=PERIOD_OPTIONS, selected=selected, result=result)

    return app


def _parse_int(raw: str | None, label: str) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{label}은(는) 정수로 입력하세요.")


def _parse_float(raw: str | None, label: str) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{label}은(는) 숫자로 입력하세요.")


def _settings_form_values(settings: Settings) -> dict:
    return {
        "words_per_day": settings.words_per_day,
        # :g 로 쓰면 20.0 대신 20, 12.5 는 12.5 로 보인다
        "prev_review_percent": f"{settings.prev_review_ratio * 100:g}",
        "wrong_review_percent": f"{settings.wrong_review_ratio * 100:g}",
        "default_question_count": settings.default_question_count,
    }


def _setting_ranges(word_count: int) -> dict:
    return {
        "words_per_day": WORDS_PER_DAY_RANGE,
        "ratio_percent": (0, RATIO_PERCENT_MAX),
        "question_count": (QUESTION_COUNT_MIN, max(QUESTION_COUNT_MIN, word_count)),
    }


def _parse_settings(form, word_count: int) -> Settings:
    """설정 화면 입력을 검사해 Settings로 바꾼다. 범위를 벗어나면 ValueError (데이터 설계서 6.1절)."""
    words_per_day = _parse_int(form.get("words_per_day"), "하루 단어 수")
    prev_percent = _parse_float(form.get("prev_review_percent"), "전날 복습 비율")
    wrong_percent = _parse_float(form.get("wrong_review_percent"), "오답 복습 비율")
    question_count = _parse_int(form.get("default_question_count"), "기본 문제 수")

    low, high = WORDS_PER_DAY_RANGE
    if not low <= words_per_day <= high:
        raise ValueError(f"하루 단어 수는 {low}~{high} 사이로 입력하세요.")
    for label, percent in (("전날 복습 비율", prev_percent), ("오답 복습 비율", wrong_percent)):
        if not 0 <= percent <= RATIO_PERCENT_MAX:
            raise ValueError(f"{label}은(는) 0~{RATIO_PERCENT_MAX:g}% 사이로 입력하세요.")
    max_count = max(QUESTION_COUNT_MIN, word_count)
    if not QUESTION_COUNT_MIN <= question_count <= max_count:
        raise ValueError(f"기본 문제 수는 {QUESTION_COUNT_MIN}~{max_count} 사이로 입력하세요.")

    return Settings(
        words_per_day=words_per_day,
        prev_review_ratio=round(prev_percent / 100, 4),
        wrong_review_ratio=round(wrong_percent / 100, 4),
        default_question_count=question_count,
    )


def _word_input_from_form(form) -> WordInput:
    return WordInput(
        english=form.get("english", ""),
        pos=form.get("pos", ""),
        meaning_text=form.get("meanings", ""),
    )


def _empty_form() -> dict:
    return {"english": "", "pos": "명사", "meanings": ""}


def _form_from_word(word) -> dict:
    return {"english": word.english, "pos": word.pos, "meanings": " / ".join(word.meanings)}


def _find_word_or_none(ctrl: StudyController, key: str):
    return next((word for word in ctrl.words if word.key == key), None)
