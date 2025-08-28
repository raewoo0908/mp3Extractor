let currentTaskId = null;
let statusCheckInterval = null;

// DOM 요소들
const urlInput = document.getElementById('youtube-url');
const extractBtn = document.getElementById('extract-btn');
const progressSection = document.getElementById('progress-section');
const resultSection = document.getElementById('result-section');
const errorSection = document.getElementById('error-section');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const statusMessage = document.getElementById('status-message');
const videoTitle = document.getElementById('video-title');
const errorMessage = document.getElementById('error-message');

// MP3 추출 시작
async function startExtraction() {
    const url = urlInput.value.trim();
    
    if (!url) {
        showError('YouTube URL을 입력해주세요.');
        return;
    }
    
    if (!isValidYouTubeUrl(url)) {
        showError('유효한 YouTube URL을 입력해주세요.');
        return;
    }
    
    try {
        // UI 상태 변경
        setExtractingState();
        
        // API 호출
        const response = await fetch('/api/extract', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentTaskId = data.task_id;
            showProgress();
            startStatusChecking();
        } else {
            showError(data.error || '추출 요청에 실패했습니다.');
        }
        
    } catch (error) {
        console.error('Extraction error:', error);
        showError('네트워크 오류가 발생했습니다. 다시 시도해주세요.');
    }
}

// YouTube URL 유효성 검사
function isValidYouTubeUrl(url) {
    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/;
    return youtubeRegex.test(url);
}

// 추출 중 상태 설정
function setExtractingState() {
    extractBtn.disabled = true;
    extractBtn.textContent = '🔄 추출 중...';
    urlInput.disabled = true;
}

// 진행 상황 표시
function showProgress() {
    progressSection.style.display = 'block';
    resultSection.style.display = 'none';
    errorSection.style.display = 'none';
    progressFill.style.width = '0%';
    progressText.textContent = '0%';
    statusMessage.textContent = 'YouTube 비디오를 다운로드하고 있습니다...';
}

// 상태 확인 시작
function startStatusChecking() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
    
    statusCheckInterval = setInterval(checkStatus, 2000); // 2초마다 확인
}

// 상태 확인
async function checkStatus() {
    if (!currentTaskId) return;
    
    try {
        const response = await fetch(`/api/status/${currentTaskId}`);
        const data = await response.json();
        
        if (response.ok) {
            updateProgress(data);
            
            if (data.status === 'completed') {
                clearInterval(statusCheckInterval);
                showResult(data);
            } else if (data.status === 'failed') {
                clearInterval(statusCheckInterval);
                showError(data.error || '오디오 추출에 실패했습니다.');
            }
        } else {
            clearInterval(statusCheckInterval);
            showError('상태 확인에 실패했습니다.');
        }
        
    } catch (error) {
        console.error('Status check error:', error);
    }
}

// 진행 상황 업데이트
function updateProgress(data) {
    if (data.progress !== undefined) {
        progressFill.style.width = `${data.progress}%`;
        progressText.textContent = `${Math.round(data.progress)}%`;
    }
    
    if (data.status === 'processing') {
        statusMessage.textContent = '오디오를 MP3로 변환하고 있습니다...';
    }
}

// 결과 표시
function showResult(data) {
    progressSection.style.display = 'none';
    resultSection.style.display = 'block';
    errorSection.style.display = 'none';
    
    if (data.title) {
        videoTitle.textContent = `제목: ${data.title}`;
    }
    
    // UI 상태 복원
    resetUIState();
}

// 오류 표시
function showError(message) {
    progressSection.style.display = 'none';
    resultSection.style.display = 'none';
    errorSection.style.display = 'block';
    errorMessage.textContent = message;
    
    // UI 상태 복원
    resetUIState();
}

// UI 상태 복원
function resetUIState() {
    extractBtn.disabled = false;
    extractBtn.textContent = '🎵 MP3 추출 시작';
    urlInput.disabled = false;
}

// 파일 다운로드
function downloadFile() {
    if (!currentTaskId) return;
    
    const downloadUrl = `/api/download/${currentTaskId}`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = '';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// 폼 초기화
function resetForm() {
    urlInput.value = '';
    progressSection.style.display = 'none';
    resultSection.style.display = 'none';
    errorSection.style.display = 'none';
    currentTaskId = null;
    
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
}

// Enter 키 이벤트 처리
urlInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        startExtraction();
    }
});

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 입력 필드에 포커스
    urlInput.focus();
});
