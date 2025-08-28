# YouTube MP3 추출기 🎵

YouTube 비디오에서 고품질 MP3 오디오를 추출하는 웹 서비스입니다. 밴드 멤버들이 쉽게 사용할 수 있도록 설계되었습니다.

## ✨ 주요 기능

- YouTube URL 입력으로 간편한 MP3 추출
- 실시간 진행 상황 표시
- 고품질 MP3 변환 (192kbps)
- 웹 기반 인터페이스로 어디서든 접근 가능
- Docker 컨테이너화로 쉬운 배포

## 🏗️ 아키텍처

### 백엔드 (Python Flask)
- **YouTube 다운로드**: yt-dlp 라이브러리 사용
- **오디오 변환**: FFmpeg를 통한 MP3 변환
- **비동기 처리**: 백그라운드에서 추출 작업 수행
- **RESTful API**: 프론트엔드와 통신

### 프론트엔드 (HTML/CSS/JavaScript)
- **반응형 디자인**: 모바일과 데스크톱 모두 지원
- **실시간 업데이트**: AJAX를 통한 진행 상황 모니터링
- **사용자 친화적**: 직관적인 인터페이스

## 🚀 빠른 시작

### 로컬 개발 환경

1. **의존성 설치**
   ```bash
   pip install -r requirements.txt
   ```

2. **FFmpeg 설치** (macOS)
   ```bash
   brew install ffmpeg
   ```

3. **애플리케이션 실행**
   ```bash
   python app.py
   ```

4. **브라우저에서 접속**
   ```
   http://localhost:5000
   ```

### Docker 사용

1. **Docker 이미지 빌드 및 실행**
   ```bash
   docker-compose up --build
   ```

2. **브라우저에서 접속**
   ```
   http://localhost:5000
   ```

## ☁️ 클라우드 배포

### AWS EC2 배포

1. **EC2 인스턴스 생성** (Ubuntu 20.04 LTS 권장)
2. **Docker 설치**
   ```bash
   sudo apt update
   sudo apt install docker.io docker-compose
   sudo usermod -aG docker $USER
   ```
3. **프로젝트 클론 및 실행**
   ```bash
   git clone <your-repo>
   cd mp3Extractor
   docker-compose up -d
   ```

### Google Cloud Platform

1. **Compute Engine 인스턴스 생성**
2. **Docker 설치 및 실행** (위와 동일)
3. **방화벽 규칙 설정** (포트 5000 허용)

### Azure

1. **Virtual Machine 생성**
2. **Docker 설치 및 실행**
3. **Network Security Group 설정**

## 📁 프로젝트 구조

```
mp3Extractor/
├── app.py                 # Flask 메인 애플리케이션
├── requirements.txt       # Python 의존성
├── Dockerfile            # Docker 이미지 설정
├── docker-compose.yml    # Docker Compose 설정
├── templates/
│   └── index.html        # 메인 HTML 템플릿
├── static/
│   ├── css/
│   │   └── style.css     # 스타일시트
│   └── js/
│       └── app.js        # 프론트엔드 JavaScript
├── downloads/            # 추출된 MP3 파일 저장소
└── README.md             # 프로젝트 문서
```

## 🔧 API 엔드포인트

- `GET /` - 메인 페이지
- `POST /api/extract` - MP3 추출 시작
- `GET /api/status/<task_id>` - 작업 상태 확인
- `GET /api/download/<task_id>` - MP3 파일 다운로드
- `POST /api/cleanup` - 오래된 작업 정리

## ⚠️ 주의사항

- YouTube의 이용약관을 준수하여 사용하세요
- 개인적인 용도로만 사용하세요
- 저작권이 있는 콘텐츠는 사용하지 마세요
- 서버 리소스 사용량을 모니터링하세요

## 🛠️ 개발 및 확장

### 새로운 기능 추가
- **플레이리스트 지원**: 여러 비디오 일괄 처리
- **다양한 포맷**: WAV, FLAC 등 추가 오디오 포맷
- **사용자 인증**: 로그인 시스템 추가
- **히스토리 관리**: 추출 기록 저장 및 관리

### 성능 최적화
- **Redis 캐싱**: 작업 상태 및 결과 캐싱
- **클라우드 스토리지**: S3, GCS 등으로 파일 저장
- **로드 밸런싱**: 여러 인스턴스로 트래픽 분산
- **CDN**: 정적 파일 전송 최적화

## 📞 지원

문제가 발생하거나 기능 요청이 있으시면 이슈를 생성해주세요.

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
