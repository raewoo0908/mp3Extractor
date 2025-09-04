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

# app
app = Flask(__name__)
CORS(app)

# Constant
MAX_CONCURRENT_TASKS = 20

# Logging configuration
logging.basicConfig(format = '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d:%(funcName)s - %(message)s', 
                    level = logging.INFO)
logger = logging.getLogger(__name__)

class TaskManager:
    def __init__(self):  # 동시 처리 가능한 최대 작업 수
        self.extraction_tasks = {}  # 여러 작업을 동시에 관리
        self.task_lock = threading.Lock()
        self.max_concurrent_tasks = MAX_CONCURRENT_TASKS
    
    def create_task(self, youtube_url) -> tuple[dict, None | str]:
        """Create a new task"""
        with self.task_lock:
            # 동시 작업 수 제한 확인
            if len(self.extraction_tasks) >= self.max_concurrent_tasks:
                return None, "Maximum number of concurrent tasks reached. Please try again later."
            
            # 새 태스크 생성
            task_id = str(uuid.uuid4())
            self.extraction_tasks[task_id] = {
                'task_id': task_id,
                'status': 'pending',
                'progress': 0, 
                'url': youtube_url,
                'created_at': time.time()
            }
            
            logger.info(f"Created new task: {task_id}, total tasks: {len(self.extraction_tasks)}")
            return self.extraction_tasks[task_id], None
    
    def get_task(self, task_id) -> dict | None:
        """Get a specific task"""
        return self.extraction_tasks.get(task_id)
    
    def get_all_tasks(self) -> dict:
        """Get all tasks"""
        return self.extraction_tasks.copy()
    
    def update_task_status(self, task_id, status, progress=None, **kwargs):
        """Update a task's status"""
        if task_id in self.extraction_tasks:
            self.extraction_tasks[task_id]['status'] = status
            if progress is not None:
                self.extraction_tasks[task_id]['progress'] = progress
            for key, value in kwargs.items():
                self.extraction_tasks[task_id][key] = value
    
    def complete_task(self, task_id, file_path, title):
        """Complete a task"""
        if task_id in self.extraction_tasks:
            self.extraction_tasks[task_id]['status'] = 'completed'
            self.extraction_tasks[task_id]['progress'] = 100
            self.extraction_tasks[task_id]['file_path'] = file_path
            self.extraction_tasks[task_id]['title'] = title
            logger.info(f"Task {task_id} completed successfully")
            logger.info(f"Current tasks: {len(self.extraction_tasks)}")
    
    def fail_task(self, task_id, error):
        """Fail a task"""
        if task_id in self.extraction_tasks:
            self.extraction_tasks[task_id]['status'] = 'failed'
            self.extraction_tasks[task_id]['error'] = str(error)
            logger.error(f"Task {task_id} failed: {error}")

    def delete_task(self, task_id):
        """Delete a task"""
        if task_id in self.extraction_tasks:
            del self.extraction_tasks[task_id]
            logger.info(f"Deleted task: {task_id}")
    
    def cleanup_old_tasks(self):
        """Clean up old tasks. if the task is older than 5 minutes, delete the task"""
        tasks_to_remove = []
        curr_time = time.time()

        with self.task_lock:
            # find the tasks older than 5 minutes
            for task_id, task in self.extraction_tasks.items():
                if curr_time - task['created_at'] > 300:
                    tasks_to_remove.append(task_id)

            for task_id in tasks_to_remove:
                # delete the file
                if 'file_path' in self.extraction_tasks[task_id]:
                    try:
                        if os.path.exists(self.extraction_tasks[task_id]['file_path']):
                            os.remove(self.extraction_tasks[task_id]['file_path'])
                            logger.info(f"Removed file: {self.extraction_tasks[task_id]['file_path']}")
                        else:
                            logger.warning(f"File does not exist: {self.extraction_tasks[task_id]['file_path']}")
                    except Exception as e:
                        logger.warning(f"Failed to remove file: {e}")
                
                # delete the task
                self.delete_task(task_id)

        return len(tasks_to_remove)
    
    def get_task_count(self) -> int:
        """Get the number of tasks"""
        return len(self.extraction_tasks)
    
    def get_task_by_status(self, status) -> dict:
        """Get tasks by status"""
        return {task_id: task for task_id, task in self.extraction_tasks.items() 
                if task['status'] == status}

class YouTubeExtractor:
    def __init__(self, task_manager):
        self.task_manager = task_manager
        
        # 쿠키 파일 경로 설정
        cookie_file = self._get_cookie_file_path()
        
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': '%(title)s.%(ext)s',
            'progress_hooks': [],
            'noplaylist': True,
            'extract_flat': False
        }
        
        # 쿠키 파일이 존재하면 추가
        if cookie_file:
            self.ydl_opts['cookiefile'] = cookie_file
            self._log_cookie_info(cookie_file)
        else:
            logger.warning("⚠️ No cookie file found - using guest mode")
    
    def _get_cookie_file_path(self):
        """쿠키 파일 경로를 찾아서 반환"""
        # 우선순위별로 쿠키 파일 경로 확인
        cookie_paths = [
            '/app/cookies.txt',        # Docker 컨테이너 내부
            './cookies.txt',           # 현재 디렉토리
            os.path.expanduser('~/cookies.txt')  # 홈 디렉토리
        ]
        
        for path in cookie_paths:
            if os.path.exists(path):
                logger.info(f"✅ Cookie file found: {path}")
                return path
        
        return None
    
    def _log_cookie_info(self, cookie_file):
        """쿠키 파일 정보 로깅"""
        try:
            with open(cookie_file, 'r') as f:
                content = f.read()
            
            # 쿠키 통계
            lines = [line for line in content.split('\n') if not line.startswith('#') and line.strip()]
            youtube_cookies = [line for line in lines if 'youtube.com' in line or 'google.com' in line]
            
            # 로그인 정보 확인
            has_login = any('LOGIN_INFO' in line for line in youtube_cookies)
            has_visitor = any('VISITOR_INFO1_LIVE' in line for line in youtube_cookies)
            
            logger.info(f"🍪 Cookie file loaded: {cookie_file}")
            logger.info(f"📊 Total cookies: {len(youtube_cookies)} YouTube/Google cookies")
            logger.info(f"🔐 Authentication: {'Logged in account' if has_login else 'Guest session'}")
            logger.info(f"👤 Visitor tracking: {'Present' if has_visitor else 'None'}")
            
            # 쿠키 파일 생성 시간
            import datetime
            mtime = os.path.getmtime(cookie_file)
            cookie_date = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"📅 Cookie file last modified: {cookie_date}")
            
        except Exception as e:
            logger.warning(f"❌ Could not analyze cookie file: {e}")

    def get_biggest_mp3_file(self, temp_dir) -> str | None:
        """Select the biggest MP3 file (usually the main audio)"""
        mp3_files = [f for f in os.listdir(temp_dir) if f.endswith('.mp3')]
    
        if not mp3_files:
            return None
        
        # Sort by file size and select the biggest file
        mp3_files_with_size = []
        for file in mp3_files:
            file_path = os.path.join(temp_dir, file)
            file_size = os.path.getsize(file_path)
            mp3_files_with_size.append((file, file_size))
        
        # Sort by size (descending)
        mp3_files_with_size.sort(key=lambda x: x[1], reverse=True)
        
        # Return the name of biggest file.
        return mp3_files_with_size[0][0]  
        
    def extract_audio(self, url, task_id):
        try:
            logger.info(f"Task {task_id}: Starting extraction for {url}")
            
            # Update the status to processing
            self.task_manager.update_task_status(task_id, 'processing', 0)
            
            # Create a temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                self.ydl_opts['outtmpl'] = os.path.join(temp_dir, '%(title)s.%(ext)s')
                
                # Progress callback
                def progress_hook(d):
                    if d['status'] == 'downloading':
                        if 'total_bytes' in d and d['total_bytes']:
                            progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
                            self.task_manager.update_task_status(task_id, 'processing', min(progress, 99))
                        elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                            progress = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                            self.task_manager.update_task_status(task_id, 'processing', min(progress, 99))
                
                self.ydl_opts['progress_hooks'] = [progress_hook]
                
                # First trial: with basic settings
                try:
                    with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                        # Get video information
                        info = ydl.extract_info(url, download=False)
                        title = info.get('title', 'unknown_title')
                        logger.debug(f"Task {task_id}: Video title: {title}")
                        
                        # Download the audio
                        ydl.download([url])
                        logger.debug(f"Task {task_id}: Audio downloaded")
                        
                        # Find the created MP3 file
                        mp3_files = [f for f in os.listdir(temp_dir) if f.endswith('.mp3')]
                        if mp3_files:
                            # Get the biggest MP3 file
                            mp3_file = self.get_biggest_mp3_file(temp_dir)
                            file_path = os.path.join(temp_dir, mp3_file)
                            
                            # Copy the file to the permanent storage
                            final_path = f"downloads/{secure_filename(mp3_file)}"
                            os.makedirs("downloads", exist_ok=True)
                            
                            with open(file_path, 'rb') as src, open(final_path, 'wb') as dst:
                                dst.write(src.read())
                            
                            # Complete the task
                            self.task_manager.complete_task(task_id, final_path, title)
                            return
                        else:
                            raise Exception("Cannot find the MP3 file")
                            
                except Exception as first_error:
                    logger.warning(f"Task {task_id}: First attempt failed, trying alternative format: {str(first_error)}")
                    
                    # Second trial: with alternative format
                    fallback_opts = self.ydl_opts.copy()
                    fallback_opts['format'] = 'worstaudio/worst'
                    fallback_opts['extractaudio'] = True
                    fallback_opts['audioformat'] = 'mp3'
                    fallback_opts['audioquality'] = '0'
                    
                    with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        title = info.get('title', 'unknown_title')
                        
                        ydl.download([url])
                        
                        # Find the created file (any extension)
                        audio_files = [f for f in os.listdir(temp_dir) if f.endswith(('.mp3', '.m4a', '.webm', '.ogg'))]
                        if audio_files:
                            audio_file = audio_files[0]
                            file_path = os.path.join(temp_dir, audio_file)
                            
                            # Convert to MP3 (using FFmpeg)
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
                                
                                # Complete the task
                                self.task_manager.complete_task(task_id, final_path, title)
                                return
                                
                            except subprocess.CalledProcessError as ffmpeg_error:
                                raise Exception(f"FFmpeg conversion failed: {str(ffmpeg_error)}")
                        else:
                            raise Exception("Cannot find the audio file")
                        
        except Exception as e:
            logger.error(f"Task {task_id}: Extraction failed - {str(e)}")
            self.task_manager.fail_task(task_id, str(e))
            self.task_manager.delete_task(task_id)

# Start background tasks

def make_downloads_directory():
    """Make the downloads directory"""
    os.makedirs("downloads", exist_ok=True)

def start_periodic_cleanup_thread():
    """Make the periodic cleanup thread"""
    cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
    cleanup_thread.start()
    logger.info("Background tasks started")

def periodic_cleanup():
    """Periodically clean up completed tasks"""
    while True:
        try:
            time.sleep(60)  # 1 minute
            cleaned_count = task_manager.cleanup_old_tasks()
            if cleaned_count > 0:
                logger.info(f"Periodic cleanup: {cleaned_count} tasks cleaned")
        except Exception as e:
            logger.error(f"Periodic cleanup failed: {e}")

# Global TaskManager instance
task_manager = TaskManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/extract', methods=['POST'])
def create_task_and_extract():
    try:
        data = request.get_json()
        youtube_url = data.get('url')
        
        if not youtube_url:
            return jsonify({'error': 'YouTube URL is required'}), 400
        
        # Create a new task
        task, error = task_manager.create_task(youtube_url)
        
        if error:
            return jsonify({'error': error}), 429  # Too Many Requests
        
        # Start the extraction job in the background
        extractor = YouTubeExtractor(task_manager)
        threading.Thread(
            target=extractor.extract_audio, 
            args=(youtube_url, task['task_id']),
            daemon=True
            ).start()
        
        return jsonify({
            'task_id': task['task_id'],
            'status': 'pending',
            'message': 'Audio extraction started',
            'total_tasks': task_manager.get_task_count()
        })
        
    except Exception as e:
        logger.error(f"Extract request failed: {str(e)}")
        return jsonify({'error': 'Server error occurred'}), 500

@app.route('/api/status/<task_id>')
def get_status(task_id):
    """특정 태스크 상태 조회"""
    task = task_manager.get_task(task_id)
    
    if not task:
        return jsonify({'error': 'Cannot find the task'}), 404
    
    return jsonify(task)

@app.route('/api/status')
def get_all_status():
    """Get all tasks status"""
    tasks = task_manager.get_all_tasks()
    return jsonify({
        'total_tasks': len(tasks),
        'tasks': tasks
    })

@app.route('/api/download/<task_id>')
def download_file(task_id):
    """Download the file of a specific task"""
    task = task_manager.get_task(task_id)
    
    if task is None:
        return jsonify({'error': 'Cannot find the task'}), 404
    
    if task['status'] != 'completed':
        return jsonify({'error': 'The task is not completed yet'}), 400
    
    file_path = task.get('file_path')
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'Cannot find the file'}), 404
    
    title = task.get('title', 'audio')

    response = send_file(
        file_path,
        as_attachment=True,
        download_name=f"{title}.mp3",
        mimetype='audio/mpeg'
    )

    task_manager.update_task_status(task_id, 'downloaded')

    task_manager.delete_task(task_id)

    return response

# 모든 라우트 등록 후 백그라운드 작업 시작
make_downloads_directory()
start_periodic_cleanup_thread()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)