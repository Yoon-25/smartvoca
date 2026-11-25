#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - smartvoca - 실행 진입점 점검: 데스크톱·웹 시작 모듈이 가져와지고 main을 가진다 (이슈 #14)
# 파일 위치: tests/test_entrypoints.py

import importlib
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class EntrypointImportTest(unittest.TestCase):

    def test_ISSUE14_desktop_entrypoint_imports_and_exposes_main(self):
        module = importlib.import_module("src.main")
        self.assertTrue(callable(module.main))

    def test_ISSUE14_web_entrypoint_imports_and_exposes_main(self):
        module = importlib.import_module("src.web.__main__")
        self.assertTrue(callable(module.main))


if __name__ == "__main__":
    unittest.main()
