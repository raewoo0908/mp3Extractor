import os
import tempfile
import uuid
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import yt_dlp
import threading
import time
import logging
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 임시 파일 저장소 (실제 운영에서는 Redis나 데이터베이스 사용 권장)
extraction_tasks = {}

class YouTubeExtractor:
    def __init__(self):
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': '%(title)s.%(ext)s',
        }
    
    def extract_audio(self, url, task_id):
        try:
            logger.info(f"Task {task_id}: Starting extraction for {url}")
            extraction_tasks[task_id]['status'] = 'processing'
            extraction_tasks[task_id]['progress'] = 0
            
            # 임시 디렉토리 생성
            with tempfile.TemporaryDirectory() as temp_dir:
                self.ydl_opts['outtmpl'] = os.path.join(temp_dir, '%(title)s.%(ext)s')
                
                # 진행 상황 콜백
                def progress_hook(d):
                    if d['status'] == 'downloading':
                        if 'total_bytes' in d and d['total_bytes']:
                            progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
                            extraction_tasks[task_id]['progress'] = min(progress, 99)
                        elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                            progress = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                            extraction_tasks[task_id]['progress'] = min(progress, 99)
                
                self.ydl_opts['progress_hooks'] = [progress_hook]
                
                # 첫 번째 시도: 기본 설정으로
                try:
                    with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                        # 비디오 정보 가져오기
                        info = ydl.extract_info(url, download=False)
                        title = info.get('title', 'unknown_title')
                        
                        # 오디오 다운로드
                        ydl.download([url])
                        
                        # 생성된 MP3 파일 찾기
                        mp3_files = [f for f in os.listdir(temp_dir) if f.endswith('.mp3')]
                        if mp3_files:
                            mp3_file = mp3_files[0]
                            file_path = os.path.join(temp_dir, mp3_file)
                            
                            # 파일을 영구 저장소로 복사
                            final_path = f"downloads/{task_id}_{secure_filename(mp3_file)}"
                            os.makedirs("downloads", exist_ok=True)
                            
                            with open(file_path, 'rb') as src, open(final_path, 'wb') as dst:
                                dst.write(src.read())
                            
                            extraction_tasks[task_id]['status'] = 'completed'
                            extraction_tasks[task_id]['progress'] = 100
                            extraction_tasks[task_id]['file_path'] = final_path
                            extraction_tasks[task_id]['title'] = title
                            logger.info(f"Task {task_id}: Extraction completed successfully")
                            return
                        else:
                            raise Exception("MP3 파일을 찾을 수 없습니다")
                            
                except Exception as first_error:
                    logger.warning(f"Task {task_id}: First attempt failed, trying alternative format: {str(first_error)}")
                    
                    # 두 번째 시도: 대체 포맷으로
                    fallback_opts = self.ydl_opts.copy()
                    fallback_opts['format'] = 'worstaudio/worst'  # 가장 낮은 품질이지만 안정적
                    fallback_opts['extractaudio'] = True
                    fallback_opts['audioformat'] = 'mp3'
                    fallback_opts['audioquality'] = '0'  # 최저 품질
                    
                    with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        title = info.get('title', 'unknown_title')
                        
                        ydl.download([url])
                        
                        # 생성된 파일 찾기 (확장자 상관없이)
                        audio_files = [f for f in os.listdir(temp_dir) if f.endswith(('.mp3', '.m4a', '.webm', '.ogg'))]
                        if audio_files:
                            audio_file = audio_files[0]
                            file_path = os.path.join(temp_dir, audio_file)
                            
                            # MP3로 변환 (FFmpeg 사용)
                            mp3_filename = f"{os.path.splitext(audio_file)[0]}.mp3"
                            mp3_path = os.path.join(temp_dir, mp3_filename)
                            
                            import subprocess
                            try:
                                subprocess.run([
                                    'ffmpeg', '-i', file_path, '-acodec', 'libmp3lame', 
                                    '-ab', '128k', mp3_path
                                ], check=True, capture_output=True)
                                
                                final_path = f"downloads/{task_id}_{secure_filename(mp3_filename)}"
                                os.makedirs("downloads", exist_ok=True)
                                
                                with open(mp3_path, 'rb') as src, open(final_path, 'wb') as dst:
                                    dst.write(src.read())
                                
                                extraction_tasks[task_id]['status'] = 'completed'
                                extraction_tasks[task_id]['progress'] = 100
                                extraction_tasks[task_id]['file_path'] = final_path
                                extraction_tasks[task_id]['title'] = title
                                logger.info(f"Task {task_id}: Extraction completed with fallback method")
                                return
                                
                            except subprocess.CalledProcessError as ffmpeg_error:
                                raise Exception(f"FFmpeg 변환 실패: {str(ffmpeg_error)}")
                        else:
                            raise Exception("오디오 파일을 찾을 수 없습니다")
                        
        except Exception as e:
            logger.error(f"Task {task_id}: Extraction failed - {str(e)}")
            extraction_tasks[task_id]['status'] = 'failed'
            extraction_tasks[task_id]['error'] = str(e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/extract', methods=['POST'])
def extract_audio():
    try:
        data = request.get_json()
        youtube_url = data.get('url')
        
        if not youtube_url:
            return jsonify({'error': 'YouTube URL이 필요합니다'}), 400
        
        # 작업 ID 생성
        task_id = str(uuid.uuid4())
        
        # 작업 정보 초기화
        extraction_tasks[task_id] = {
            'status': 'pending',
            'progress': 0,
            'url': youtube_url,
            'created_at': time.time()
        }
        
        # 백그라운드에서 추출 작업 시작
        extractor = YouTubeExtractor()
        thread = threading.Thread(target=extractor.extract_audio, args=(youtube_url, task_id))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'task_id': task_id,
            'status': 'pending',
            'message': '오디오 추출이 시작되었습니다'
        })
        
    except Exception as e:
        logger.error(f"Extract request failed: {str(e)}")
        return jsonify({'error': '서버 오류가 발생했습니다'}), 500

@app.route('/api/status/<task_id>')
def get_status(task_id):
    if task_id not in extraction_tasks:
        return jsonify({'error': '작업을 찾을 수 없습니다'}), 404
    
    task = extraction_tasks[task_id]
    return jsonify(task)

@app.route('/api/download/<task_id>')
def download_file(task_id):
    if task_id not in extraction_tasks:
        return jsonify({'error': '작업을 찾을 수 없습니다'}), 404
    
    task = extraction_tasks[task_id]
    if task['status'] != 'completed':
        return jsonify({'error': '작업이 아직 완료되지 않았습니다'}), 400
    
    file_path = task.get('file_path')
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': '파일을 찾을 수 없습니다'}), 404
    
    title = task.get('title', 'audio')
    return send_file(
        file_path,
        as_attachment=True,
        download_name=f"{title}.mp3",
        mimetype='audio/mpeg'
    )

@app.route('/api/cleanup', methods=['POST'])
def cleanup_old_tasks():
    """오래된 작업 정리 (24시간 이상)"""
    try:
        current_time = time.time()
        old_tasks = []
        
        for task_id, task in extraction_tasks.items():
            if current_time - task['created_at'] > 86400:  # 24시간
                old_tasks.append(task_id)
                # 파일 삭제
                if 'file_path' in task and os.path.exists(task['file_path']):
                    os.remove(task['file_path'])
        
        for task_id in old_tasks:
            del extraction_tasks[task_id]
        
        return jsonify({'message': f'{len(old_tasks)}개의 오래된 작업이 정리되었습니다'})
        
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        return jsonify({'error': '정리 작업에 실패했습니다'}), 500

if __name__ == '__main__':
    # downloads 디렉토리 생성
    os.makedirs("downloads", exist_ok=True)
    
    # 개발 모드에서는 디버그 활성화
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    # 프로덕션 모드
    os.makedirs("downloads", exist_ok=True)
