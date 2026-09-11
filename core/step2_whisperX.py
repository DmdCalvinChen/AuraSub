import os
import sys
bin_dir = os.path.dirname(sys.executable)
os.environ['PATH'] = f"{bin_dir}:/opt/homebrew/bin:/usr/local/bin" + os.pathsep + os.environ.get('PATH', '')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings
warnings.filterwarnings("ignore")

import whisperx
import torch
from typing import Dict
import librosa
from rich import print as rprint
import subprocess
import tempfile
import time

from core.config_utils import load_key
from core.all_whisper_methods.demucs_vl import demucs_main, RAW_AUDIO_FILE, VOCAL_AUDIO_FILE
from core.all_whisper_methods.whisperX_utils import process_transcription, convert_video_to_audio, split_audio, save_results, save_language, compress_audio, CLEANED_CHUNKS_EXCEL_PATH
from core.step1_ytdlp import find_video_files

MODEL_DIR = load_key("model_dir")
WHISPER_FILE = "output/audio/for_whisper.mp3"
ENHANCED_VOCAL_PATH = "output/audio/enhanced_vocals.mp3"

def check_hf_mirror() -> str:
    """Check and return the fastest HF mirror"""
    mirrors = {
        'Official': 'huggingface.co',
        'Mirror': 'hf-mirror.com'
    }
    fastest_url = f"https://{mirrors['Official']}"
    best_time = float('inf')
    rprint("[cyan]🔍 Checking HuggingFace mirrors...[/cyan]")
    for name, domain in mirrors.items():
        try:
            if os.name == 'nt':
                cmd = ['ping', '-n', '1', '-w', '3000', domain]
            else:
                cmd = ['ping', '-c', '1', '-W', '3', domain]
            start = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True)
            response_time = time.time() - start
            if result.returncode == 0:
                if response_time < best_time:
                    best_time = response_time
                    fastest_url = f"https://{domain}"
                rprint(f"[green]✓ {name}:[/green] {response_time:.2f}s")
        except:
            rprint(f"[red]✗ {name}:[/red] Failed to connect")
    if best_time == float('inf'):
        rprint("[yellow]⚠️ All mirrors failed, using default[/yellow]")
    rprint(f"[cyan]🚀 Selected mirror:[/cyan] {fastest_url} ({best_time:.2f}s)")
    return fastest_url

import platform

def is_mac_apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine() == "arm64"

def transcribe_audio(audio_file: str, start: float, end: float) -> Dict:
    os.environ['HF_ENDPOINT'] = check_hf_mirror() #? don't know if it's working...
    WHISPER_LANGUAGE = load_key("whisper.language")
    whisper_language = None if 'auto' in str(WHISPER_LANGUAGE) else WHISPER_LANGUAGE

    use_mlx = False
    if is_mac_apple_silicon():
        try:
            import mlx_whisper
            use_mlx = True
        except ImportError:
            use_mlx = False

    if use_mlx:
        device = "mlx_gpu"
        rprint(f"🚀 Starting [bold cyan]MLX-Whisper on Apple Silicon GPU (Metal / Unified Memory)[/bold cyan] ...")
    else:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        rprint(f"🚀 Starting WhisperX using device: {device} ...")
    
    if device == "cuda":
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        batch_size = 16 if gpu_mem > 8 else 2
        compute_type = "float16" if torch.cuda.is_bf16_supported() else "int8"
        rprint(f"[cyan]🎮 GPU memory:[/cyan] {gpu_mem:.2f} GB, [cyan]📦 Batch size:[/cyan] {batch_size}, [cyan]⚙️ Compute type:[/cyan] {compute_type}")
    elif device == "mlx_gpu":
        rprint(f"[cyan]🍎 Mac GPU Acceleration:[/cyan] MLX Unified Memory Enabled")
    else:
        batch_size = 1
        compute_type = "int8"
        rprint(f"[cyan]📦 Batch size:[/cyan] {batch_size}, [cyan]⚙️ Compute type:[/cyan] {compute_type}")
    rprint(f"[green]▶️ Starting transcription for segment {start:.2f}s to {end:.2f}s...[/green]")
    
    try:
        # Create temp file with wav format for better compatibility
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            temp_audio_path = temp_audio.name
        
        # Extract audio segment using ffmpeg
        ffmpeg_cmd = f'ffmpeg -y -i "{audio_file}" -ss {start} -t {end-start} -vn -ar 32000 -ac 1 "{temp_audio_path}"'
        subprocess.run(ffmpeg_cmd, shell=True, check=True, capture_output=True)
        
        try:
            # Load audio segment with librosa
            audio_segment, sample_rate = librosa.load(temp_audio_path, sr=16000)
        finally:
            # Clean up temp file
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)

        if use_mlx:
            import mlx_whisper
            model_key = str(load_key("whisper.model"))
            mlx_model_map = {
                "large-v3": "mlx-community/whisper-large-v3-mlx",
                "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
                "turbo": "mlx-community/whisper-large-v3-turbo",
                "medium": "mlx-community/whisper-medium-mlx",
                "small": "mlx-community/whisper-small-mlx",
                "base": "mlx-community/whisper-base-mlx",
                "tiny": "mlx-community/whisper-tiny-mlx",
            }
            local_model_turbo = os.path.join(MODEL_DIR, "whisper-large-v3-turbo")
            local_model_large = os.path.join(MODEL_DIR, "whisper-large-v3-mlx")
            local_model_custom = os.path.join(MODEL_DIR, model_key)
            
            if os.path.exists(local_model_custom):
                mlx_model = local_model_custom
                rprint(f"[green]📥 Loading local MLX model from:[/green] {local_model_custom} ...")
            elif model_key in ["large-v3-turbo", "turbo"] and os.path.exists(local_model_turbo):
                mlx_model = local_model_turbo
                rprint(f"[green]📥 Loading local MLX model from:[/green] {local_model_turbo} ...")
            elif model_key == "large-v3" and os.path.exists(local_model_large):
                mlx_model = local_model_large
                rprint(f"[green]📥 Loading local MLX model from:[/green] {local_model_large} ...")
            else:
                if WHISPER_LANGUAGE == 'zh':
                    mlx_model = mlx_model_map.get(model_key, "mlx-community/whisper-large-v3-turbo")
                else:
                    mlx_model = mlx_model_map.get(model_key, model_key)
                rprint(f"[green]📥 Loading MLX model:[/green] {mlx_model} ...")
            result = mlx_whisper.transcribe(
                audio_segment,
                path_or_hf_repo=mlx_model,
                language=whisper_language,
                word_timestamps=True,
            )
        else:
            if WHISPER_LANGUAGE == 'zh':
                model_name = "Huan69/Belle-whisper-large-v3-zh-punct-fasterwhisper"
                local_model = os.path.join(MODEL_DIR, "Belle-whisper-large-v3-zh-punct-fasterwhisper")
            else:
                model_name = load_key("whisper.model")
                local_model = os.path.join(MODEL_DIR, model_name)
                
            if os.path.exists(local_model):
                rprint(f"[green]📥 Loading local WHISPER model:[/green] {local_model} ...")
                model_name = local_model
            else:
                rprint(f"[green]📥 Using WHISPER model from HuggingFace:[/green] {model_name} ...")

            vad_options = {"vad_onset": 0.500,"vad_offset": 0.363}
            asr_options = {"temperatures": [0],"initial_prompt": "",}
            rprint("[bold yellow]**You can ignore warning of `Model was trained with torch 1.10.0+cu102, yours is 2.0.0+cu118...`**[/bold yellow]")
            model = whisperx.load_model(model_name, device, compute_type=compute_type, language=whisper_language, vad_options=vad_options, asr_options=asr_options, download_root=MODEL_DIR)

            rprint("[bold green]note: You will see Progress if working correctly[/bold green]")
            result = model.transcribe(audio_segment, batch_size=batch_size, print_progress=True)

            del model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        # Save language
        save_language(result['language'])
        if result['language'] == 'zh' and WHISPER_LANGUAGE != 'zh':
            raise ValueError("Please specify the transcription language as zh and try again!")

        # Align whisper output
        align_device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        rprint(f"[cyan]🪡 Running Wav2Vec2 forced alignment on device: {align_device} ...[/cyan]")
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=align_device)
        result = whisperx.align(result["segments"], model_a, metadata, audio_segment, align_device, return_char_alignments=False)

        # Free GPU resources again
        del model_a
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif torch.backends.mps.is_available():
            torch.mps.empty_cache()

        # Adjust timestamps
        for segment in result['segments']:
            segment['start'] += start
            segment['end'] += start
            for word in segment.get('words', []):
                if 'start' in word:
                    word['start'] += start
                if 'end' in word:
                    word['end'] += start
        return result
    except Exception as e:
        rprint(f"[red]WhisperX processing error:[/red] {e}")
        raise

def enhance_vocals(vocals_ratio=2.50):
    """Enhance vocals audio volume"""
    if not load_key("demucs"):
        return RAW_AUDIO_FILE
        
    try:
        print(f"[cyan]🎙️ Enhancing vocals with volume ratio: {vocals_ratio}[/cyan]")
        ffmpeg_cmd = (
            f'ffmpeg -y -i "{VOCAL_AUDIO_FILE}" '
            f'-filter:a "volume={vocals_ratio}" '
            f'"{ENHANCED_VOCAL_PATH}"'
        )
        subprocess.run(ffmpeg_cmd, shell=True, check=True, capture_output=True)
        
        return ENHANCED_VOCAL_PATH
    except subprocess.CalledProcessError as e:
        print(f"[red]Error enhancing vocals: {str(e)}[/red]")
        return VOCAL_AUDIO_FILE  # Fallback to original vocals if enhancement fails
    
def transcribe():
    if os.path.exists(CLEANED_CHUNKS_EXCEL_PATH):
        rprint("[yellow]⚠️ Transcription results already exist, skipping transcription step.[/yellow]")
        return
    
    # step0 Convert video to audio
    video_file = find_video_files()
    convert_video_to_audio(video_file)

    # step1 Demucs vocal separation:
    if load_key("demucs"):
        demucs_main()
    
    # step2 Compress audio
    choose_audio = enhance_vocals() if load_key("demucs") else RAW_AUDIO_FILE
    whisper_audio = compress_audio(choose_audio, WHISPER_FILE)

    # step3 Extract audio
    segments = split_audio(whisper_audio)
    
    # step4 Transcribe audio
    all_results = []
    for start, end in segments:
        result = transcribe_audio(whisper_audio, start, end)
        all_results.append(result)
    
    # step5 Combine results
    combined_result = {'segments': []}
    for result in all_results:
        combined_result['segments'].extend(result['segments'])
    
    # step6 Process df
    df = process_transcription(combined_result)
    save_results(df)
        
if __name__ == "__main__":
    transcribe()