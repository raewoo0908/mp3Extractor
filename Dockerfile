FROM python:3.11-slim

# 시스템 패키지 업데이트 및 FFmpeg 설치
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사 (.dockerignore로 제어)
COPY . .

# downloads 디렉토리 생성
RUN mkdir -p downloads

# 포트 노출
EXPOSE 5001

# 환경 변수 설정
ENV FLASK_APP=app.py
ENV FLASK_DEBUG=0
ENV PYTHONUNBUFFERED=1

# 애플리케이션 실행
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--timeout", "300", "--workers", "1", "app:app"]
# CMD ["python", "app.py"]