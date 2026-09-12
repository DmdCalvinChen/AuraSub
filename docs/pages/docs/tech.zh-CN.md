**AuraSub 视频翻译系统技术文档**

AuraSub 是一个面向专业内容、高度集成的智能视频翻译系统，能够自动化执行视频极速下载、音频提取、语音识别（ASR）、ASR 语音纠错、纯 LLM 语义分句、高质量多步翻译、双指针时间轴对齐，以及音视频硬件加速压制等一系列复杂操作。系统同时提供直观的 Web 界面与一键启动脚本。

对于开发人员，可以单步执行 `core` 下的每一个 `step__.py` 文件并在 `output` 下检查每一步的输出。

以下是系统的核心技术模块和工作流程：

1. **视频获取模块 (Video Acquisition)**:
   - `core/step1_ytdlp.py`: 集成现代化 `yt-dlp` 引擎，支持 Netscape 格式 Cookie 认证绕过防盗链与限制、Deno JS 动态解密加速、PyPI 启动自动更新自检，支持 1080p/4K/720p 多档画质与文件名安全清理。

2. **音频处理与语音识别模块 (Audio & ASR)**:
   - `core/step2_whisper.py`: 统一调度语音识别与词级时间戳提取。
   - `core/all_whisper_methods/mlx_whisper.py`: Apple Silicon Mac 专属引擎，利用 Metal GPU 与统一内存实现极速转录，并结合 PyTorch MPS 进行高精度强制对齐。
   - `core/all_whisper_methods/whisperX.py`: Windows NVIDIA CUDA 平台引擎，基于 WhisperX + CTranslate2 框架进行转录与对齐。
   - `core/all_whisper_methods/whisperXapi.py`: 基于 Replicate 云端 API 的 WhisperX 转录实现。

3. **文本预处理、纠错与语义分句模块 (NLP & Preprocessing)**:
   - `core/step2_5_add_punctuation.py`: 基于 LLM 对无标点的转录文本进行智能标点推断与语境从句还原。
   - `core/step2_6_asr_correction.py`: 基于自定义术语表（Glossary），在底层词级时间戳数据上直接进行 ASR 听错同音词与漏词的无损精准纠错。
   - `core/step3_semantic_chunking.py`: 基于纯 LLM 的语义智能分句，彻底取代机械式物理切词（如 SpaCy），确保断句符合专业长难句的语义边界。

4. **视频摘要与专业翻译模块 (Summarize & Translation)**:
   - `core/step4_1_summarize.py`: 利用 LLM 对视频内容进行智能摘要并提取核心主题术语。
   - `core/step4_2_translate_all.py`: 实现字幕文本的高效并发与批量化翻译。
   - `core/translate_once.py`: 结合正则单词边界匹配（防止全量注入污染上下文）与双层级推理强度控制（Reasoning Effort），采用三步翻译法（直译、意译、润色）生成地道字幕。

5. **时间轴对齐与字幕压制模块 (Timeline & Subtitle Integration)**:
   - `core/step6_generate_final_timeline.py`: 基于鲁棒的词级双指针（Two-Pointer）数学匹配算法，将翻译后的文本 1:1 无损绑定回底层时间戳，生成标准 SRT/ASS 文件。
   - `core/step7_merge_sub_to_vid.py`: 硬件自适应视频字幕压制引擎，自动检测并调用 Apple Silicon VideoToolbox 或 NVIDIA NVENC 硬件加速，支持中英文双语字号自定义与最长句单帧即时预览。

6. **音频处理与配音模块 (Audio & Dubbing)**:
   - `core/step8_gen_audio_task.py`: 生成音频任务，处理字幕以确保与时间轴相符。
   - `core/step10_gen_audio.py`: 从文本生成配音音频文件，并根据时间自动微调语速。
   - `core/step11_merge_audio_to_vid.py`: 将生成的配音音频与视频进行专业合成。
   - `core/step12_merge_dub_to_vid.py`: 结合人声与背景伴奏音轨合成最终带配音的视频。
   - `core/delete_retry_dubbing.py`: 删除中间生成的冗余音频文件。

7. **LLM 交互与系统配置模块 (LLM & Core Utils)**:
   - `core/ask_gpt.py`: 封装主流大模型（OpenAI、DeepSeek、Claude 等）交互接口，支持双层级推理控制与智能重试机制。
   - `core/prompts_storage.py`: 集中管理针对分句、标点、纠错、摘要、翻译等全流程优化的高性能 Prompt 模板。
   - `core/config_utils.py`: 线程安全读写 YAML 配置，实现 API Key 等敏感凭证向 `.secret` 文件的安全隔离。

8. **文本转语音（TTS）模块**:
   - `core/all_tts_functions/gpt_sovits_tts.py`: 使用 GPT-SoVITS 进行高拟真度多语种配音。
   - `core/all_tts_functions/azure_tts.py`: 利用 Azure 语音合成服务生成配音。
   - `core/all_tts_functions/openai_tts.py`: 使用 OpenAI TTS 服务将文本转换为语音。
   - `core/all_tts_functions/fish_tts.py`: 对接 Fish Audio TTS 接口。

9. **批量处理模块 (Batch Mode)**:
   - `batch/utils/batch_processor.py`: 批量处理视频任务，通过 Excel 配置表管理视频处理流水线。
   - `batch/utils/video_processor.py`: 单个视频全流程执行器，无缝接入最新的 ASR 纠错与纯 LLM 语义分句。
   - `batch/utils/settings_check.py`: 检查批处理输入文件与全局配置的一致性。

10. **Streamlit 交互界面 (WebUI)**:
    - `st.py`: 基于 Streamlit 的交互式 Web 应用，提供一站式参数调节、Cookie 凭证管理与流程控制。
    - `st_components/download_video_section.py`: 提供 YouTube 链接高速下载与本地音视频上传。
    - `st_components/sidebar_setting.py`: 侧边栏配置面板，方便切换模型、配置 API 与调整推理强度。
    - `st_components/imports_and_utils.py`: 界面组件公用辅助工具库。

AuraSub 系统通过上述现代化模块的协同工作，实现了从视频获取、智能纠错、语义理解、高精翻译到硬件加速压制的全流程自动化。
