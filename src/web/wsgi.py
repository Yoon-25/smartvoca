#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - smartvoca - 배포용 WSGI 진입점: 환경변수 설정, 단어장 시드 복사, 경로 접두사 처리 (과제 배포 요건)
# 파일 위치: src/web/wsgi.py
# 실행(컨테이너): gunicorn -b 0.0.0.0:8080 --workers 1 src.web.wsgi:app

import os
import shutil

from src.paths import DATA_DIR
from src.web.app import create_app
from src.web.controller import WebPaths

# 컨테이너 안에서 단어장 시드 파일의 위치 (Dockerfile이 복사한다)
SEED_WORD_FILE = os.environ.get("WORD_SEED", "/app/seed/voca_2000.csv")


class PrefixMiddleware:
    """서버 주소가 /2026/voca-<학번>/ 같은 접두사 아래에 있을 때 쓴다.

    프록시가 접두사를 지우지 않고 넘기는 경우에만 필요하다 (APP_PREFIX 설정 시).
    앱 코드는 접두사 없이 `/` 기준으로 작성되어 있고, url_for가 접두사를 붙이도록 SCRIPT_NAME을 맞춘다.
    """

    def __init__(self, wsgi_app, prefix: str):
        self._app = wsgi_app
        self._prefix = prefix.rstrip("/")

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        if self._prefix and path.startswith(self._prefix):
            environ["SCRIPT_NAME"] = self._prefix
            environ["PATH_INFO"] = path[len(self._prefix):] or "/"
        return self._app(environ, start_response)


def _seed_data_if_missing(word_file: str, data_dir: str) -> None:
    """첫 실행 때 단어장이 볼륨에 없으면 시드 파일을 복사한다. 이후에는 볼륨의 파일을 쓴다."""
    os.makedirs(data_dir, exist_ok=True)
    if not os.path.exists(word_file) and os.path.exists(SEED_WORD_FILE):
        shutil.copyfile(SEED_WORD_FILE, word_file)


def build_app(environ=None):
    """환경변수로 앱을 만든다. SECRET_KEY가 없으면 시작하지 않는다."""
    env = os.environ if environ is None else environ
    secret_key = env.get("SECRET_KEY", "")
    if not secret_key:
        raise RuntimeError("SECRET_KEY 환경변수가 없어 시작할 수 없습니다.")

    data_dir = env.get("DATA_DIR") or DATA_DIR
    word_file = os.path.join(data_dir, "voca_2000.csv")
    _seed_data_if_missing(word_file, data_dir)
    paths = WebPaths(
        word_file=word_file,
        settings_file=os.path.join(data_dir, "settings.json"),
        progress_file=os.path.join(data_dir, "progress.json"),
        history_file=os.path.join(data_dir, "study_history.csv"),
        reports_dir=os.path.join(data_dir, "reports"),
    )
    app = create_app(paths, secret_key=secret_key)
    prefix = env.get("APP_PREFIX", "")
    if prefix:
        app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix)
    return app


def __getattr__(name: str):
    """gunicorn이 `app`을 처음 찾을 때만 앱을 만든다 (import만 해도 시작 실패하지 않도록).

    실행 잠금(InstanceLock)은 쓰지 않는다: 컨테이너는 재시작마다 PID 1이 되므로
    이전 잠금을 살아 있는 실행으로 오인할 수 있다. 대신 Dockerfile에서 워커를 1개로 고정한다.
    """
    if name == "app":
        built = build_app()
        globals()["app"] = built
        return built
    raise AttributeError(name)
