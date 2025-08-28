#!/bin/bash

# YouTube MP3 추출기 - 맥북 개발 환경 구축 스크립트

set -e

echo "🚀 YouTube MP3 추출기 개발 환경을 구축합니다..."

# Homebrew 확인 및 설치
echo "🍺 Homebrew를 확인합니다..."
if ! command -v brew &> /dev/null; then
    echo "Homebrew가 설치되어 있지 않습니다. 설치를 시작합니다..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "✅ Homebrew가 이미 설치되어 있습니다"
fi

# FFmpeg 설치 (yt-dlp에서 필요)
echo "🎵 FFmpeg를 설치합니다..."
if ! command -v ffmpeg &> /dev/null; then
    brew install ffmpeg
    echo "✅ FFmpeg 설치 완료"
else
    echo "✅ FFmpeg가 이미 설치되어 있습니다"
fi

# Python 가상환경 생성
echo "🐍 Python 가상환경을 생성합니다..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ 가상환경 생성 완료"
else
    echo "✅ 가상환경이 이미 존재합니다"
fi

# 가상환경 활성화 및 의존성 설치
echo "📦 Python 의존성을 설치합니다..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ 의존성 설치 완료"

# downloads 디렉토리 생성
echo "📁 downloads 디렉토리를 생성합니다..."
mkdir -p downloads

# 권한 설정 (소유자만 읽기/쓰기 가능, 다른 사용자는 읽기만)
chmod 755 downloads
echo "✅ downloads 디렉토리 권한 설정 완료 (755)"

# 소유권 확인 (현재 사용자가 소유자인지 확인)
if [ "$(stat -f %Su downloads)" != "$(whoami)" ]; then
    echo "⚠️  downloads 디렉토리 소유권을 현재 사용자로 변경합니다..."
    sudo chown $(whoami):$(id -gn) downloads
    echo "✅ 소유권 변경 완료"
fi

# Docker 확인 (선택사항)
echo "🐳 Docker 상태를 확인합니다..."
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        echo "✅ Docker가 실행 중입니다"
        echo "Docker로 테스트하려면: docker-compose up --build"
    else
        echo "⚠️  Docker가 설치되어 있지만 실행되지 않았습니다"
        echo "Docker Desktop을 실행해주세요"
    fi
else
    echo "⚠️  Docker가 설치되어 있지 않습니다"
    echo "Docker Desktop for Mac을 설치하려면: https://www.docker.com/products/docker-desktop"
fi

echo ""
echo "🎉 개발 환경 구축이 완료되었습니다!"
echo ""
echo "📱 애플리케이션 실행 방법:"
echo "1. 가상환경 활성화: source venv/bin/activate"
echo "2. Flask 실행: python app.py"
echo "3. 브라우저에서 접속: http://localhost:5000"
echo ""
echo "🐳 Docker로 테스트하려면:"
echo "docker-compose up --build"
echo ""
echo "📝 개발 팁:"
echo "- 가상환경을 활성화한 후 pip install로 추가 패키지 설치"
echo "- app.py 수정 후 Flask가 자동으로 재시작됩니다"
echo "- downloads/ 폴더에 추출된 MP3 파일이 저장됩니다"
