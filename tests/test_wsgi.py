#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - smartvoca - 배포용 WSGI 진입점 테스트: 시크릿 키, 시드 복사, 경로 접두사, 실행 잠금 미사용 (과제 배포 요건)
# 파일 위치: tests/test_wsgi.py

import csv
import os
import tempfile
import unittest
from unittest import mock

from src.web import wsgi

SEED_ROWS = [("apple", "명사", "사과"), ("book", "명사", "책"), ("cat", "명사", "고양이")]


def _write_seed(path: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as seed_file:
        writer = csv.writer(seed_file)
        writer.writerow(["번호", "영단어", "품사", "뜻"])
        for number, (english, pos, meaning) in enumerate(SEED_ROWS, start=1):
            writer.writerow([number, english, pos, meaning])


class WsgiBuildTest(unittest.TestCase):

    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = temp_dir.name
        self.seed_path = os.path.join(self.root, "seed.csv")
        self.data_dir = os.path.join(self.root, "data")
        _write_seed(self.seed_path)
        self.env = {"SECRET_KEY": "test-secret-key", "DATA_DIR": self.data_dir}
        patcher = mock.patch.object(wsgi, "SEED_WORD_FILE", self.seed_path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_ISSUE15_build_refuses_to_start_without_secret_key(self):
        with self.assertRaises(RuntimeError):
            wsgi.build_app({"DATA_DIR": self.data_dir})

    def test_ISSUE15_first_run_seeds_word_file_into_data_dir(self):
        wsgi.build_app(self.env)
        word_file = os.path.join(self.data_dir, "voca_2000.csv")
        self.assertTrue(os.path.exists(word_file))
        with open(word_file, encoding="utf-8") as word_file_obj:
            self.assertIn("apple", word_file_obj.read())

    def test_ISSUE15_existing_word_file_is_not_overwritten(self):
        os.makedirs(self.data_dir)
        word_file = os.path.join(self.data_dir, "voca_2000.csv")
        with open(word_file, "w", encoding="utf-8") as existing:
            existing.write("번호,영단어,품사,뜻\n1,keep,명사,유지\n")
        wsgi.build_app(self.env)
        with open(word_file, encoding="utf-8") as existing:
            self.assertIn("keep", existing.read())

    def test_ISSUE15_instance_lock_is_not_used_in_container(self):
        wsgi.build_app(self.env)
        self.assertFalse(os.path.exists(os.path.join(self.data_dir, ".smartvoca.lock")))

    def test_ISSUE15_app_responds_at_root(self):
        client = wsgi.build_app(self.env).test_client()
        self.assertEqual(client.get("/").status_code, 200)

    def test_ISSUE15_prefixed_requests_are_served_and_links_keep_prefix(self):
        env = dict(self.env, APP_PREFIX="/2026/voca-test")
        client = wsgi.build_app(env).test_client()
        response = client.get("/2026/voca-test/words")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('href="/2026/voca-test/memorize"', body)

    def test_ISSUE15_prefix_middleware_leaves_other_paths_alone(self):
        calls = []

        def inner(environ, start_response):
            calls.append((environ["SCRIPT_NAME"], environ["PATH_INFO"]))
            start_response("200 OK", [])
            return [b""]

        middleware = wsgi.PrefixMiddleware(inner, "/2026/voca-test")
        middleware({"PATH_INFO": "/2026/voca-test", "SCRIPT_NAME": ""}, lambda *_a: None)
        middleware({"PATH_INFO": "/other", "SCRIPT_NAME": ""}, lambda *_a: None)
        self.assertEqual(calls[0], ("/2026/voca-test", "/"))
        self.assertEqual(calls[1], ("", "/other"))


if __name__ == "__main__":
    unittest.main()
