#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - smartvoca - 데스크톱·웹이 함께 쓰는 데이터 경로 상수 (아키텍처 설계서 6.3절)
# 파일 위치: src/paths.py

import os

# 경로 상수는 이 파일에만 둔다 (아키텍처 설계서 6.3절)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
WORD_FILE = os.path.join(DATA_DIR, "voca_2000.csv")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
PROGRESS_FILE = os.path.join(DATA_DIR, "progress.json")
HISTORY_FILE = os.path.join(DATA_DIR, "study_history.csv")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
