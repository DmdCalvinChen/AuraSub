import os
import sys
import glob
import re
import shutil
import subprocess
import time
import json
import urllib.request
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config_utils import load_key

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COOKIE_FILENAME = "cookies.txt"

def sanitize_filename(filename: str) -> str:
    """Remove or replace illegal characters in filenames."""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.strip('. ')
    return filename if filename else 'video'

def find_deno_path() -> str | None:
    """Find local Deno JS runtime path for YouTube challenge decoding."""
    candidates = [
        os.environ.get("DENO_PATH"),
        os.path.expanduser("~/.deno/bin/deno"),
        "/opt/homebrew/bin/deno",
        "/usr/local/bin/deno",
        os.path.join(ROOT_DIR, "deno"),
        shutil.which("deno")
    ]
    for path in candidates:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return os.path.abspath(path)
    return None

def get_cookie_file() -> str | None:
    """Find existing Netscape cookie file in workspace."""
    search_paths = [
        os.path.join(ROOT_DIR, "cookies.txt"),
        os.path.join(ROOT_DIR, "cookie.txt"),
        os.path.join(ROOT_DIR, "output", "cookies.txt"),
        os.path.join(ROOT_DIR, "output", "cookie.txt"),
        os.path.expanduser("~/Downloads/cookies.txt"),
        os.path.expanduser("~/Downloads/cookie.txt"),
    ]
    for path in search_paths:
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            return os.path.abspath(path)
            
    # Search any .txt file with Netscape cookie signature in root
    for f in glob.glob(os.path.join(ROOT_DIR, "*.txt")):
        if os.path.isfile(f) and os.path.getsize(f) > 0:
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as file_obj:
                    header = file_obj.read(200)
                    if "Netscape HTTP Cookie File" in header or "# HTTP Cookie File" in header:
                        return os.path.abspath(f)
            except Exception:
                pass
    return None

def save_uploaded_cookie(file_bytes: bytes) -> str:
    """Save uploaded cookie file content to root cookies.txt."""
    cookie_path = os.path.join(ROOT_DIR, COOKIE_FILENAME)
    # Strip UTF-8 BOM if present
    if file_bytes.startswith(b'\xef\xbb\xbf'):
        file_bytes = file_bytes[3:]
    with open(cookie_path, "wb") as f:
        f.write(file_bytes)
    return cookie_path

def delete_cookie_file() -> bool:
    """Delete cookies.txt and cookie.txt in root directory."""
    deleted = False
    for name in ["cookies.txt", "cookie.txt"]:
        p = os.path.join(ROOT_DIR, name)
        if os.path.exists(p):
            try:
                if os.path.islink(p) or os.path.isfile(p):
                    os.remove(p)
                    deleted = True
            except Exception as e:
                print(f"Error removing cookie file {p}: {e}")
    return deleted

def check_cookie_status() -> dict:
    """Get current cookie status information."""
    cookie_path = get_cookie_file()
    if cookie_path and os.path.exists(cookie_path):
        stat = os.stat(cookie_path)
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        size_kb = round(stat.st_size / 1024, 1)
        return {
            "exists": True,
            "path": cookie_path,
            "filename": os.path.basename(cookie_path),
            "size_kb": size_kb,
            "mtime": mtime
        }
    return {"exists": False, "path": None, "filename": None, "size_kb": 0, "mtime": None}

def _parse_version(ver_str: str) -> list[int]:
    """Parse version string into integer tuple for accurate comparison."""
    if not ver_str or ver_str == "unknown":
        return []
    return [int(x) for x in re.findall(r'\d+', str(ver_str))]

def check_and_update_ytdlp(force: bool = False, timeout: int = 3) -> dict:
    """Check PyPI for latest yt-dlp release and update if needed."""
    try:
        import yt_dlp.version
        current_ver = yt_dlp.version.__version__
    except Exception:
        current_ver = "unknown"

    latest_ver = None
    update_needed = force

    # Query PyPI for latest version
    try:
        req = urllib.request.Request(
            "https://pypi.org/pypi/yt-dlp/json",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            latest_ver = data.get("info", {}).get("version")
            if latest_ver and current_ver != "unknown":
                curr_parsed = _parse_version(current_ver)
                latest_parsed = _parse_version(latest_ver)
                if latest_parsed > curr_parsed:
                    update_needed = True
    except Exception as e:
        print(f"yt-dlp update check notice (skipped): {e}")

    if update_needed:
        print(f"🔄 Upgrading yt-dlp (current: {current_ver} -> latest: {latest_ver or 'newest'})...")
        try:
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Reload module
            for mod_name in list(sys.modules.keys()):
                if mod_name == 'yt_dlp' or mod_name.startswith('yt_dlp.'):
                    del sys.modules[mod_name]
            import yt_dlp.version
            new_ver = yt_dlp.version.__version__
            return {
                "updated": True,
                "current_version": new_ver,
                "latest_version": latest_ver or new_ver,
                "message": f"已成功更新 yt-dlp 至最新版本 ({new_ver})"
            }
        except Exception as e:
            return {
                "updated": False,
                "current_version": current_ver,
                "latest_version": latest_ver or current_ver,
                "message": f"更新 yt-dlp 失败: {e}"
            }

    return {
        "updated": False,
        "current_version": current_ver,
        "latest_version": latest_ver or current_ver,
        "message": f"yt-dlp 已是最新版本 ({current_ver})"
    }

def download_video_ytdlp(url: str, save_path: str = 'output', resolution: str = '1080', custom_cookie_path: str = None, cutoff_time: float = None):
    """Download video with yt-dlp supporting cookies, Deno JS runtime, and friendly error handling."""
    if not url or not url.strip():
        raise ValueError("视频链接不能为空，请输入有效的 URL。")
    
    url = url.strip()
    os.makedirs(save_path, exist_ok=True)

    # Resolution format mapping
    res_str = str(resolution).lower().replace('p', '')
    if res_str in ['best', '最佳', 'max']:
        format_expr = 'bestvideo+bestaudio/best'
    elif res_str == '2160' or res_str == '4k':
        format_expr = 'bestvideo[height<=2160]+bestaudio/best[height<=2160]/best[height<=2160]/best'
    elif res_str == '1440' or res_str == '2k':
        format_expr = 'bestvideo[height<=1440]+bestaudio/best[height<=1440]/best[height<=1440]/best'
    elif res_str == '720':
        format_expr = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best[height<=720]/best'
    elif res_str == '480':
        format_expr = 'bestvideo[height<=480]+bestaudio/best[height<=480]/best[height<=480]/best'
    elif res_str == '360':
        format_expr = 'bestvideo[height<=360]+bestaudio/best[height<=360]/best[height<=360]/best'
    elif res_str == 'audio':
        format_expr = 'bestaudio/best'
    else:
        # Default 1080p
        format_expr = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best[height<=1080]/best'

    ydl_opts = {
        'format': format_expr,
        'outtmpl': f'{save_path}/%(title)s.%(ext)s',
        'noplaylist': True,
        'writethumbnail': True,
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegThumbnailsConvertor',
            'format': 'jpg',
        }],
        'quiet': False,
        'no_warnings': False,
    }

    # Cookie injection
    cookie_file = custom_cookie_path if (custom_cookie_path and os.path.exists(custom_cookie_path)) else get_cookie_file()
    if cookie_file:
        print(f"🍪 Using Cookie file: {cookie_file}")
        ydl_opts['cookiefile'] = cookie_file

    # Deno JS Runtime injection
    deno_path = find_deno_path()
    if deno_path:
        print(f"🚀 Using Deno JS runtime: {deno_path}")
        ydl_opts['js_runtimes'] = {'deno': {'path': deno_path}}
        ydl_opts['remote_components'] = {'ejs:github'}

    import yt_dlp
    from yt_dlp.utils import DownloadError

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except DownloadError as de:
        err_msg = str(de)
        if any(keyword in err_msg.lower() for keyword in ["sign in", "bot", "confirm you’re not a bot", "403", "forbidden", "login"]):
            raise RuntimeError("⚠️ YouTube 要求人机身份验证或账号登录凭证。请在页面上方上传有效的 Netscape 格式 cookies.txt 后重新尝试！") from de
        elif any(keyword in err_msg.lower() for keyword in ["video unavailable", "private video", "not available", "deleted"]):
            raise RuntimeError("⚠️ 视频不可用：该视频可能为私享视频、已下架或在当前地区受限，请核对链接。") from de
        elif any(keyword in err_msg.lower() for keyword in ["incompleteread", "timed out", "connection reset", "network is unreachable", "errno 60"]):
            raise RuntimeError("⚠️ 网络连接超时或中断：请检查您的网络连接或代理设置后重试。") from de
        else:
            raise RuntimeError(f"下载失败：{err_msg}") from de
    except Exception as e:
        raise RuntimeError(f"下载过程中发生未知异常：{str(e)}") from e

    # Check and rename files after download
    for file in os.listdir(save_path):
        if os.path.isfile(os.path.join(save_path, file)):
            filename, ext = os.path.splitext(file)
            new_filename = sanitize_filename(filename)
            if new_filename != filename:
                os.rename(os.path.join(save_path, file), os.path.join(save_path, new_filename + ext))

    # Cut the video to make demo if cutoff_time is set
    if cutoff_time:
        print(f"Cutoff time: {cutoff_time}, Now checking video duration...")
        video_file = find_video_files(save_path)
        
        import librosa
        duration = librosa.get_duration(filename=video_file)
        
        if duration > cutoff_time:
            print(f"Video duration ({duration:.2f}s) is longer than cutoff time. Cutting the video...")
            file_name, file_extension = os.path.splitext(video_file)
            trimmed_file = f"{file_name}_trim{file_extension}"
            ffmpeg_cmd = ['ffmpeg', '-y', '-i', video_file, '-t', str(cutoff_time), '-c', 'copy', trimmed_file]
            print("🎬 Start cutting video...")
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
            print(f"✅ Video has been cut to the first {cutoff_time} seconds")
            
            os.remove(video_file)
            os.rename(trimmed_file, video_file)
            print(f"Original file removed and trimmed file renamed to {os.path.basename(video_file)}")
        else:
            print(f"Video duration ({duration:.2f}s) is not longer than cutoff time. No need to cut.")

def find_video_files(save_path: str = 'output') -> str:
    """Find downloaded video file in save_path."""
    allowed_formats = load_key("allowed_video_formats")
    video_files = [file for file in glob.glob(save_path + "/*") if os.path.splitext(file)[1][1:].lower() in allowed_formats]
    
    if sys.platform.startswith('win'):
        video_files = [file.replace("\\", "/") for file in video_files]
    video_files = [file for file in video_files if not file.startswith("output/output")]
    
    if len(video_files) != 1:
        raise ValueError(f"找到的视频文件数量不唯一 (找到 {len(video_files)} 个)，请先清理 output 目录。")
    return video_files[0]

if __name__ == '__main__':
    url = input('Please enter the URL of the video you want to download: ')
    resolution = input('Please enter the desired resolution (1080/best/720, default 1080): ') or '1080'
    download_video_ytdlp(url, resolution=resolution)
    print(f"🎥 Video has been downloaded to {find_video_files()}")
