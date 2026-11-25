# 스마트 보카 (VocaFlashcard)

2,000개 영단어를 일차별로 나눠 암기하고, 시험으로 확인하는 단어장 앱입니다.
수업 과제로 웹 앱을 만들고, 학교 서버에 Docker 컨테이너로 올립니다.

## 구현한 요구사항 (REQ 기준, 과제 VOCA-FR 대응은 명세서 8절 참고)

| ID | 내용 | 상태 |
|----|------|------|
| REQ-001, REQ-002 | 단어장 CSV 불러오기·저장, 편집(추가·수정·삭제), 검색 | 구현 (웹, 데스크톱) |
| REQ-003 | 일차별 암기, 뜻 보기, 이력 기록 | 구현 |
| REQ-004, REQ-007~009 | 시험 (문제 수, 출제 방향, 단답형·4지선다·OX, 채점) | 구현 |
| REQ-005, REQ-006 | 일차 진도, 복습 단어 섞기, 설정 | 구현 |
| REQ-010, REQ-011 | 이력 저장, 보고서 | 구현 |
| 통계 (추이, 자주 틀린 단어) | 웹 통계 화면 | 보고서 텍스트만 구현, 웹 추이 화면은 미구현 |

## 실행 방법

### 웹 (개발용, 로컬)
```
pip install -r requirements-web.txt
python -m src.web
```
브라우저에서 `http://127.0.0.1:5000`을 엽니다.

### 웹 (Docker, 배포와 같은 방식)
```
docker build -t voca-app .
docker run --rm -p 8080:8080 -e SECRET_KEY=change-me -v voca-data:/data voca-app
```
브라우저에서 `http://127.0.0.1:8080`을 엽니다.

### 데스크톱 (PyQt6)
```
pip install -r requirements.txt
python -m src.main
```

## 데이터와 DB

- 현재 저장 방식: 단어장은 CSV, 진도·설정은 JSON, 이력은 CSV 파일입니다 (`data/` 또는 컨테이너의 `/data`).
- 과제 기준 DB: **SQLite** (`DB_PATH=/data/voca.db`)로 전환하는 작업이 남아 있습니다. 전환 전까지는 위 파일 방식으로 동작합니다.
- 환경변수: `SECRET_KEY`(필수), `DATA_DIR`(데이터 폴더), `WORD_SEED`(최초 단어장 시드), `APP_PREFIX`(프록시가 접두사를 넘길 때만).

## 문서

- `docs/`: 기획서, 요구사항 명세서, 아키텍처 설계서, 데이터 설계서, 프로세스 설계서, 결정 기록(ADR), 테스트 정의서
- `CLAUDE.md`: 작업 방식과 산출물 위치

## 테스트

```
python -m unittest discover -s tests -t .
```
