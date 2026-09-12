**AuraSub Video Translation System Technical Documentation**

AuraSub is a precision-driven, highly integrated video translation system designed for professional content. It automates complex operations including accelerated video downloading, audio extraction, speech recognition (ASR), phonetic ASR correction, pure LLM semantic chunking, multi-step translation, robust two-pointer timeline alignment, and hardware-accelerated subtitle rendering. The system also provides an intuitive web interface and one-click launch scripts.

For developers, each `step__.py` file under the `core` directory can be executed individually, and the output of each step can be inspected under the `output` directory.

The following are the core technical modules and workflow of the system:

1. **Video Acquisition Module**:
   - `core/step1_ytdlp.py`: Integrates a modernized `yt-dlp` engine supporting Netscape-format Cookie authentication (bypassing bot checks and restrictions), Deno JS dynamic decryption acceleration, PyPI startup auto-updates, multi-resolution selection (1080p/4K/720p), and filename sanitization.

2. **Audio Processing and Speech Recognition Module**:
   - `core/step2_whisper.py`: Orchestrates speech recognition and word-level timestamp extraction.
   - `core/all_whisper_methods/mlx_whisper.py`: Dedicated Apple Silicon Mac engine utilizing Metal GPU and Unified Memory for ultra-fast local inference, combined with PyTorch MPS forced alignment.
   - `core/all_whisper_methods/whisperX.py`: Windows NVIDIA CUDA platform engine based on WhisperX + CTranslate2.
   - `core/all_whisper_methods/whisperXapi.py`: Replicate cloud-based WhisperX API implementation.

3. **Text Preprocessing, Correction, and Semantic Chunking Module**:
   - `core/step2_5_add_punctuation.py`: Employs an LLM to logically deduce punctuation and restore syntactic clauses from unpunctuated transcripts.
   - `core/step2_6_asr_correction.py`: Uses custom user glossaries to perform surgical, zero-loss phonetic ASR error corrections directly on underlying word-level timestamps before translation.
   - `core/step3_semantic_chunking.py`: Pure LLM-driven semantic chunking that completely supersedes mechanical NLP segmentation (e.g. SpaCy), ensuring natural clause boundaries for complex professional sentences.

4. **Summarization and Professional Translation Module**:
   - `core/step4_1_summarize.py`: Uses LLMs to intelligently summarize video content and extract core domain terminology.
   - `core/step4_2_translate_all.py`: Coordinates concurrent, high-throughput batch translation of subtitle chunks.
   - `core/translate_once.py`: Integrates exact regex word-boundary glossary injection (preventing context pollution) and two-tier reasoning effort controls with a 3-step translation workflow (literal, free, and polishing).

5. **Timeline Alignment and Subtitle Integration Module**:
   - `core/step6_generate_final_timeline.py`: Employs a robust word-level two-pointer matching algorithm to map translated text 1:1 back onto exact audio timestamps, generating standard SRT and ASS subtitle files.
   - `core/step7_merge_sub_to_vid.py`: Hardware-adaptive video subtitle burning engine automatically detecting and utilizing Apple Silicon VideoToolbox or NVIDIA NVENC hardware acceleration, supporting font size customization and instant single-frame preview.

6. **Audio Processing and Dubbing Module**:
   - `core/step8_gen_audio_task.py`: Prepares audio dubbing tasks, adjusting subtitle lengths for timing alignment.
   - `core/step10_gen_audio.py`: Generates dubbing audio from text and dynamically adapts speech rate.
   - `core/step11_merge_audio_to_vid.py`: Performs professional-level synthesis of dubbing audio with the original video.
   - `core/step12_merge_dub_to_vid.py`: Combines vocal tracks and background music with hardware-accelerated video rendering.
   - `core/delete_retry_dubbing.py`: Cleans up redundant intermediate audio files.

7. **LLM Interaction and System Utility Module**:
   - `core/ask_gpt.py`: Encapsulates standardized interfaces for multiple LLM providers (OpenAI, DeepSeek, Claude, etc.) with dual-tier reasoning controls and retry logic.
   - `core/prompts_storage.py`: Centrally manages fine-tuned prompt templates for punctuation, chunking, correction, summarization, and translation.
   - `core/config_utils.py`: Thread-safe YAML configuration manager with automatic sensitive key isolation into `.secret`.

8. **Text-to-Speech (TTS) Module**:
   - `core/all_tts_functions/gpt_sovits_tts.py`: Uses GPT-SoVITS for high-fidelity multi-language voice cloning.
   - `core/all_tts_functions/azure_tts.py`: Leverages Azure Speech Services for voice synthesis.
   - `core/all_tts_functions/openai_tts.py`: Uses OpenAI TTS service to generate speech.
   - `core/all_tts_functions/fish_tts.py`: Integrates Fish Audio TTS API.

9. **Batch Processing Module**:
   - `batch/utils/batch_processor.py`: Manages batch video processing workflows using Excel spreadsheets.
   - `batch/utils/video_processor.py`: Pipeline runner for single video jobs, seamlessly integrating ASR correction and pure LLM semantic chunking.
   - `batch/utils/settings_check.py`: Validates input batch files and configuration integrity.

10. **Streamlit Interface Module (WebUI)**:
    - `st.py`: Interactive web interface built on Streamlit with full workflow controls and real-time status display.
    - `st_components/download_video_section.py`: Video acquisition component supporting YouTube downloads with Cookie credentials and local video uploads.
    - `st_components/sidebar_setting.py`: Configuration panel for model selection, API credentials, and reasoning controls.
    - `st_components/imports_and_utils.py`: Reusable utility functions for WebUI components.

Through the close collaboration of these modern modules, AuraSub delivers end-to-end automation from video downloading and intelligent error correction to semantic translation and hardware-accelerated video synthesis.
