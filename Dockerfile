FROM python:3.11.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 실행 사용자 UID 10001 (권한 없이 실행). 쓰기는 /data(볼륨)와 /tmp만 한다
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app \
 && mkdir -p /data /app/seed \
 && chown 10001:10001 /data

WORKDIR /app

# 의존성은 빌드 때 설치한다. 실행 중에는 인터넷이 필요 없다
COPY requirements-web.txt ./
RUN pip install --no-cache-dir -r requirements-web.txt

COPY src ./src
COPY data/voca_2000.csv /app/seed/voca_2000.csv

ENV DATA_DIR=/data \
    WORD_SEED=/app/seed/voca_2000.csv

USER 10001

EXPOSE 8080

# 운영용 서버 gunicorn. 워커는 1개로 고정한다 (단일 인스턴스, 파일 저장 방식)
CMD ["gunicorn", "-b", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--access-logfile", "-", "src.web.wsgi:app"]
