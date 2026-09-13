import os, subprocess, time, sys, re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
bin_dir = os.path.dirname(sys.executable)
if bin_dir not in os.environ.get('PATH', ''):
    os.environ['PATH'] = f"{bin_dir}:" + os.environ.get('PATH', '')
from core.config_utils import load_key
from core.step1_ytdlp import find_video_files
from rich import print as rprint
import cv2
import numpy as np
import platform

try:
    SRC_FONT_SIZE = load_key("subtitle.source_font_size")
    TRANS_FONT_SIZE = load_key("subtitle.target_font_size")
except Exception:
    SRC_FONT_SIZE = 15
    TRANS_FONT_SIZE = 18
def get_subtitle_fonts():
    """Get optimized default fonts for source and target subtitles based on OS."""
    sys_name = platform.system()
    if sys_name == 'Darwin':
        # macOS: Hiragino Sans GB (冬青黑体) is in /System/Library/Fonts/ and accessible by libass
        # avoiding sandbox permissions errors with PrivateFrameworks/PingFangUI.ttc
        return 'Arial', 'Hiragino Sans GB'
    elif sys_name == 'Windows':
        return 'Arial', 'Microsoft YaHei'
    else:
        # Linux
        return 'NotoSansCJK-Regular', 'NotoSansCJK-Regular'

FONT_NAME, TRANS_FONT_NAME = get_subtitle_fonts()

OUTPUT_DIR = "output"
OUTPUT_VIDEO = f"{OUTPUT_DIR}/output_sub.mp4"
SRC_SRT = f"{OUTPUT_DIR}/src.srt"
TRANS_SRT = f"{OUTPUT_DIR}/trans.srt"
COMBINED_ASS = f"{OUTPUT_DIR}/combined.ass"


def get_video_encoder():
    """Detect available hardware video encoder (VideoToolbox for Mac, NVENC for NVIDIA)."""
    try:
        result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True, errors='ignore')
        encoders_str = result.stdout
        if platform.system() == 'Darwin' and 'h264_videotoolbox' in encoders_str:
            return 'h264_videotoolbox', ['-c:v', 'h264_videotoolbox', '-b:v', '8000k']
        elif 'h264_nvenc' in encoders_str:
            return 'h264_nvenc', ['-c:v', 'h264_nvenc']
    except Exception:
        pass
    return 'libx264', ['-c:v', 'libx264']

def parse_srt(srt_path):
    """Parse an SRT file and return a list of (index, start_time, end_time, text) tuples."""
    if not os.path.exists(srt_path):
        return []
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = re.split(r'\n\s*\n', content.strip())
    entries = []
    for block in blocks:
        lines = [line for line in block.split('\n') if line.strip()]
        if len(lines) >= 3:
            idx = lines[0].strip()
            time_line = lines[1].strip()
            text = " ".join(lines[2:])
            try:
                start_str, end_str = time_line.split(' --> ')
                entries.append((idx, start_str.strip(), end_str.strip(), text))
            except ValueError:
                continue
    return entries

def srt_time_to_ass_time(srt_time):
    """Convert SRT time format '00:00:00,000' to ASS time format '0:00:00.00'."""
    h, m, s_ms = srt_time.split(':')
    s, ms = s_ms.split(',')
    # ASS uses centiseconds (2 digits)
    cs = int(ms) // 10
    return f"{int(h)}:{m}:{s}.{cs:02d}"

def generate_combined_ass(target_size, source_size, output_ass_path=COMBINED_ASS):
    """Generate a combined ASS file from src.srt and trans.srt with different font sizes."""
    src_entries = parse_srt(SRC_SRT)
    trans_entries = parse_srt(TRANS_SRT)
    
    # Build a lookup from (start, end) -> text for source
    src_map = {}
    for idx, start, end, text in src_entries:
        src_map[(start, end)] = text
    
    # ASS header
    ass_content = f"""[Script Info]
Title: Combined Subtitles
ScriptType: v4.00+
PlayResX: 384
PlayResY: 288
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{TRANS_FONT_NAME},{target_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,1,1,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    for idx, start, end, trans_text in trans_entries:
        src_text = src_map.get((start, end), "")
        ass_start = srt_time_to_ass_time(start)
        ass_end = srt_time_to_ass_time(end)
        
        # Use inline override: target language (bigger) on top, source language (smaller) below
        # \fs sets font size, \fn sets font name, \N is a hard line break
        combined_text = (
            f"{{\\fn{TRANS_FONT_NAME}\\fs{target_size}}}{trans_text}"
            f"\\N"
            f"{{\\fn{FONT_NAME}\\fs{source_size}}}{src_text}"
        )
        
        ass_content += f"Dialogue: 0,{ass_start},{ass_end},Default,,0,0,0,,{combined_text}\n"
    
    with open(output_ass_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)
    
    return output_ass_path

def merge_subtitles_to_video():
    RESOLUTION = load_key("resolution")
    TARGET_WIDTH, TARGET_HEIGHT = RESOLUTION.split('x')
    video_file = find_video_files()
    os.makedirs(os.path.dirname(OUTPUT_VIDEO), exist_ok=True)

    # Check resolution
    if RESOLUTION == '0x0':
        rprint("[bold yellow]Warning: A 0-second black video will be generated as a placeholder as Resolution is set to 0x0.[/bold yellow]")

        # Create a black frame
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, 1, (1920, 1080))
        out.write(frame)
        out.release()

        rprint("[bold green]Placeholder video has been generated.[/bold green]")
        return

    if not os.path.exists(SRC_SRT) or not os.path.exists(TRANS_SRT):
        print("Subtitle files not found in the 'output' directory.")
        exit(1)

    # Generate combined ASS with configured font sizes
    ass_path = generate_combined_ass(TRANS_FONT_SIZE, SRC_FONT_SIZE)

    ffmpeg_cmd = [
        'ffmpeg', '-i', video_file,
        '-vf', (
            f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
            f"ass={ass_path}"
        ),
    ]

    encoder_name, encoder_args = get_video_encoder()
    if encoder_name == 'h264_videotoolbox':
        rprint("[bold green]Apple Silicon VideoToolbox hardware encoder detected, will use Apple GPU acceleration.[/bold green]")
    elif encoder_name == 'h264_nvenc':
        rprint("[bold green]NVIDIA GPU encoder (NVENC) detected, will use GPU acceleration.[/bold green]")
    else:
        rprint("[bold yellow]No hardware GPU encoder detected, using CPU encoder (libx264).[/bold yellow]")
    
    ffmpeg_cmd.extend(encoder_args)
    
    ffmpeg_cmd.extend(['-y', OUTPUT_VIDEO])

    print("🎬 Start merging subtitles to video...")
    start_time = time.time()
    process = subprocess.Popen(ffmpeg_cmd)

    try:
        process.wait()
        if process.returncode == 0:
            print(f"\n✅ Done! Time taken: {time.time() - start_time:.2f} seconds")
        else:
            print("\n❌ FFmpeg execution error")
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        if process.poll() is None:
            process.kill()

def find_longest_subtitle_time(srt_path):
    if not os.path.exists(srt_path):
        return "0.0"
    
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = re.split(r'\n\s*\n', content.strip())
    max_len = -1
    target_time_seconds = 0.0
    
    for block in blocks:
        lines = [line for line in block.split('\n') if line.strip()]
        if len(lines) >= 3:
            time_line = lines[1]
            text = "".join(lines[2:])
            if len(text) > max_len:
                max_len = len(text)
                try:
                    start_str = time_line.split(' --> ')[0].strip()
                    end_str = time_line.split(' --> ')[1].strip()
                    
                    def time_to_sec(t_str):
                        h, m, s_ms = t_str.split(':')
                        s, ms = s_ms.split(',')
                        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0
                    
                    start_sec = time_to_sec(start_str)
                    end_sec = time_to_sec(end_str)
                    target_time_seconds = (start_sec + end_sec) / 2.0
                except Exception as e:
                    print(f"Error parsing subtitle time: {e}")
                    pass
    
    return str(target_time_seconds)

def generate_preview_frame(target_size, source_size):
    RESOLUTION = load_key("resolution")
    video_file = find_video_files()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    OUTPUT_PREVIEW = f"{OUTPUT_DIR}/preview.jpg"
    
    if not video_file or not os.path.exists(TRANS_SRT):
        return None

    target_time = find_longest_subtitle_time(TRANS_SRT)

    TARGET_WIDTH, TARGET_HEIGHT = RESOLUTION.split('x')
    if RESOLUTION == '0x0':
        TARGET_WIDTH, TARGET_HEIGHT = "1920", "1080"

    # Generate combined ASS with requested font sizes
    ass_path = generate_combined_ass(target_size, source_size)

    ffmpeg_cmd = [
        'ffmpeg', '-i', video_file, '-ss', target_time,
        '-vf', (
            f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
            f"ass={ass_path}"
        ),
        '-vframes', '1',
        '-y', OUTPUT_PREVIEW
    ]

    try:
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        if os.path.exists(OUTPUT_PREVIEW):
            return OUTPUT_PREVIEW
    except Exception as e:
        print(f"Error generating preview: {e}")
    return None

if __name__ == "__main__":
    merge_subtitles_to_video()