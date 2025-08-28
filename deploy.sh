#!/bin/bash

# YouTube MP3 추출기 배포 스크립트
# Ubuntu 20.04+ 서버에서 실행

set -e

echo "🚀 YouTube MP3 추출기 배포를 시작합니다..."

# 시스템 업데이트
echo "📦 시스템 패키지를 업데이트합니다..."
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
echo "🔧 필수 패키지를 설치합니다..."
sudo apt install -y curl wget git unzip software-properties-common apt-transport-https ca-certificates gnupg lsb-release

# Docker 설치
echo "🐳 Docker를 설치합니다..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo usermod -aG docker $USER
    echo "✅ Docker 설치 완료"
else
    echo "✅ Docker가 이미 설치되어 있습니다"
fi

# Docker Compose 설치
echo "🐳 Docker Compose를 설치합니다..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose 설치 완료"
else
    echo "✅ Docker Compose가 이미 설치되어 있습니다"
fi

# Nginx 설치
echo "🌐 Nginx를 설치합니다..."
if ! command -v nginx &> /dev/null; then
    sudo apt install -y nginx
    sudo systemctl enable nginx
    sudo systemctl start nginx
    echo "✅ Nginx 설치 완료"
else
    echo "✅ Nginx가 이미 설치되어 있습니다"
fi

# 방화벽 설정
echo "🔥 방화벽을 설정합니다..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
echo "✅ 방화벽 설정 완료"

# 프로젝트 디렉토리 생성
echo "📁 프로젝트 디렉토리를 생성합니다..."
PROJECT_DIR="/opt/mp3-extractor"
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR

# 프로젝트 파일 복사 (현재 디렉토리에서)
echo "📋 프로젝트 파일을 복사합니다..."
cp -r . $PROJECT_DIR/
cd $PROJECT_DIR

# downloads 디렉토리 권한 설정
mkdir -p downloads
chmod 755 downloads

# Nginx 설정
echo "⚙️ Nginx 설정을 업데이트합니다..."
sudo cp nginx.conf /etc/nginx/sites-available/mp3-extractor
sudo ln -sf /etc/nginx/sites-available/mp3-extractor /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

# Docker 컨테이너 실행
echo "🐳 Docker 컨테이너를 실행합니다..."
docker-compose up -d --build

# 서비스 상태 확인
echo "🔍 서비스 상태를 확인합니다..."
sleep 10
if curl -f http://localhost:5000/ > /dev/null 2>&1; then
    echo "✅ 애플리케이션이 성공적으로 실행되었습니다!"
else
    echo "❌ 애플리케이션 실행에 실패했습니다. 로그를 확인해주세요."
    docker-compose logs
fi

# 시스템 서비스 등록 (선택사항)
echo "🔄 시스템 서비스로 등록합니다..."
cat > mp3-extractor.service << EOF
[Unit]
Description=YouTube MP3 Extractor
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

sudo cp mp3-extractor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mp3-extractor.service

echo "🎉 배포가 완료되었습니다!"
echo ""
echo "📱 서비스 접속: http://$(curl -s ifconfig.me)"
echo "📁 프로젝트 디렉토리: $PROJECT_DIR"
echo "📊 서비스 상태: sudo systemctl status mp3-extractor"
echo "📝 로그 확인: docker-compose logs -f"
echo ""
echo "⚠️  도메인을 설정하려면 nginx.conf의 server_name을 수정하고 SSL 인증서를 설정하세요."
