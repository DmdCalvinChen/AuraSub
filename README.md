<div align="center">

# AuraSub
**Precision-Driven Semantic Translation & Dubbing for Professional Content**

[**English**](/README.md)｜[**中文**](/i18n/README.zh.md)

</div>

## 🌟 Overview

**AuraSub** is a specialized, enhanced branch derived from the original VideoLingo project. Compared to the original project, AuraSub's core differences lie in its **LLM-based intelligent sentence segmentation, phonetic ASR error correction, highly optimized terminology translation mechanism, two-tier reasoning control, and real-time subtitle preview customization.**

While the original project relies on traditional NLP algorithms for sentence breaking—which often fail and cause misaligned chunks when handling complex professional lectures—AuraSub completely abandons physical NLP slicing. Instead, it uses LLMs for logical, context-aware sentence segmentation, **delivering a massive leap in segmentation accuracy and contextual coherence** compared to the original project. Furthermore, AuraSub introduces a targeted phonetic correction engine that repairs misheard professional terms at the root timestamp level, without relying on "full-scale context injection" that pollutes the translation prompt.

### Core Differences & Features:
- **🧠 Pure LLM Intelligent Chunking:** Replaces mechanical NLP (e.g., SpaCy). It uses an LLM to logically deduce punctuation and segment unpunctuated transcripts into cohesive clauses, offering a massive leap in chunking quality.
- **🗣️ Zero-Loss ASR Phonetic Correction:** An exclusive pipeline that scans for misheard terms. It uses your custom glossary and regex word boundaries to surgically fix single or multi-word phonetic errors globally within the underlying timestamp data before translation begins.
- **📚 Optimized Terminology without Pollution:** Incorporates exact regex word-boundary matching during the translation phase. This allows the LLM to use your glossary accurately without being overwhelmed by massive "full-text terminology injections," effectively eliminating context pollution.
- **🪡 Robust Two-Pointer Alignment:** A custom alignment engine mathematically matches translated blocks back to their precise word-level audio timestamps, entirely avoiding the missing timeline issues of previous iterations.
- **🧠 Two-Tier Reasoning Control:** Allows configuring different reasoning intensities (e.g., `low`, `medium`, `high` via API request bodies) for hard vs. easy tasks in the WebUI to maximize translation quality and cost-efficiency.
- **🍪 Modernized Video Downloader with Cookie & Deno Support:**
  - **Cookie Management:** WebUI supports uploading Netscape-format `cookie.txt` (any filename) to seamlessly bypass YouTube bot verification, 403 Forbidden, and login/age restrictions.
  - **Auto-Updating yt-dlp Engine:** Automatically checks and upgrades to the latest PyPI release on startup.
  - **Deno JS Dynamic Decryption:** Native Deno integration solves YouTube `n-challenge` dynamic signature decoding without bandwidth throttling.
  - **Multi-Resolution Selector:** Choose between 1080p (default), Best Quality (4K/2K), 720p, 480p, with crystal-clear status and error diagnostics.
- **🍎 Apple Silicon Mac Hardware Acceleration & One-Click Start:**
  - Integrated **MLX-Whisper** engine utilizing Metal GPU and Unified Memory for ultra-fast local inference.
  - Forced alignment accelerated via PyTorch MPS (Metal Performance Shaders).
  - macOS Finder double-clickable `OneKeyStart.command` automatically discovers Conda paths and activates the environment.
- **🎨 Subtitle Style & Real-Time Preview:** Features a dedicated customization block for adjusting font sizes. Employs a unified ASS subtitle generation scheme for zero-overlap double-line text, and renders single-frame previews of the longest sentences instantly without repeating the translation workflow.
- **✅ Netflix-Standard Exclusivity:** Enforces strict single-line subtitles only, guaranteeing a clean, professional viewing experience.
- **🎙️ Advanced Dubbing:** Seamless integration with GPT-SoVITS, Azure, OpenAI TTS, and more for one-click multilingual dubbing.
- 🎥 **Solid Foundation:** Inherits VideoLingo's excellent frame.


### Language Support

**Input Languages:**
🇺🇸 English | 🇷🇺 Russian | 🇫🇷 French | 🇩🇪 German | 🇮🇹 Italian | 🇪🇸 Spanish | 🇯🇵 Japanese | 🇨🇳 Chinese

**Translation & Dubbing:**
Translation supports practically all languages powered by leading LLMs. Dubbing support depends on the chosen TTS provider.

## 💻 Supported Platforms & Requirements

AuraSub is optimized for high-performance neural inference and officially supports two primary hardware platforms:

| Platform | Hardware Acceleration | Requirements |
| :--- | :--- | :--- |
| 🍎 **Apple Silicon Mac** | Metal GPU / Unified Memory (`MLX-Whisper` + PyTorch `MPS`) | M1 / M2 / M3 / M4 Series, macOS 13+ |
| 🎮 **Windows** | NVIDIA CUDA (`WhisperX` + CTranslate2) | NVIDIA GPU (GTX 1060+ / RTX Series, 6GB+ VRAM) |

> ⚠️ **Notice**: **Intel-based Macs (x86_64) are NOT supported** due to the absence of Apple Unified Memory and MLX Metal acceleration.

## Installation

> **Note (Windows with NVIDIA GPU):** Please complete the following steps first:
> 1. Install [CUDA Toolkit 12.6](https://developer.download.nvidia.com/compute/cuda/12.6.0/local_installers/cuda_12.6.0_560.76_windows.exe)
> 2. Install [CUDNN 9.3.0](https://developer.download.nvidia.com/compute/cudnn/9.3.0/local_installers/cudnn_9.3.0_windows.exe)
> 3. Add `C:\Program Files\NVIDIA\CUDNN\v9.3\bin\12.6` to your system PATH
> 4. Restart your computer

> **Note (FFmpeg Required):** Install via package manager:
> - macOS: ```brew install ffmpeg``` (via [Homebrew](https://brew.sh/))
> - Windows: ```choco install ffmpeg``` (via [Chocolatey](https://chocolatey.org/))

1. Clone the repository

```bash
git clone https://github.com/YourOrg/AuraSub.git
cd AuraSub
```

2. Install dependencies (requires `python=3.10`)

```bash
conda create -n aurasub python=3.10.0 -y
conda activate aurasub
python install.py
```

3. Start the application

- **Option A (Double-Click - Recommended)**:
  - macOS: Double-click [`OneKeyStart.command`](OneKeyStart.command) in Finder.
  - Windows: Double-click [`OneKeyStart.bat`](OneKeyStart.bat) in File Explorer.

- **Option B (Terminal)**:
  ```bash
  streamlit run st.py
  ```

## 📝 Custom Terminology & ASR Correction
AuraSub features a powerful context-based phonetic correction engine. While it can automatically fix common misheard words, providing a domain-specific glossary will significantly enhance accuracy:
1. In the project root, duplicate `custom_terms_template.xlsx` and rename it to `custom_terms.xlsx`.
2. Enter your specialized vocabulary (e.g., `buccal`, `Anchorage`) into the first column of the spreadsheet.
3. During processing, AuraSub will prioritize your glossary to regex-scan and automatically surgically repair misheard terms within the raw audio timeline.

## API Configuration
AuraSub supports OpenAI-like API formats for reasoning and translation:
- Supported LLMs: Supports virtually all current mainstream large models (as long as they can output JSON format, they can complete this workflow perfectly).
- Supported TTS: `azure-tts`, `openai-tts`, `fish-tts`, `GPT-SoVITS`, `edge-tts`, and more.

## Current Limitations

1. WhisperX transcription performance may be affected by heavy background noise (using wav2vec alignment). For best results on professional content, clean audio tracks are preferred.
2. Due to strict JSON schema validation in the LLM pipeline, using weaker, non-reasoning LLMs may cause intermediate step failures. If this occurs, delete the `output` folder and retry with a stronger model (e.g., GPT-4o, Claude 3.5, or DeepSeek).
3. The dubbing feature synchronizes speaking rates dynamically, but language structural differences mean it may require manual tweaking for absolute perfection.
4. **Multilingual recognition** defaults to the primary detected language due to WhisperX's specialized single-language alignment constraint.

## 📄 License & Attribution

This project is licensed under the **Apache 2.0 License**.

**AuraSub** is an independent, heavily refactored fork and evolution of [VideoLingo](https://github.com/Huanshere/VideoLingo), originally created by **Huanshere**. We sincerely thank the original author for the foundational engineering architecture, which made this semantic-focused evolution possible.

Special thanks to the following open-source projects for their underlying capabilities:
[whisperX](https://github.com/m-bain/whisperX), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [json_repair](https://github.com/mangiucugna/json_repair), [BELLE](https://github.com/LianjiaTech/BELLE)
