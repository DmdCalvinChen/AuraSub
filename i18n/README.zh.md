<div align="center">

# AuraSub
**面向专业内容的极致语义翻译与配音利器**

[**English**](/README.md)｜[**中文**](/i18n/README.zh.md)

</div>

## 🌟 简介

**AuraSub** 是基于原开源项目 VideoLingo 衍生出的一个强化分支。与原项目相比，AuraSub 最大的核心区别在于：**引入了基于大语言模型（LLM）的智能断句、基于发音同源的 ASR 语音纠错、高度优化的术语翻译机制、双层级推理强度控制，以及字幕样式定制与即时预览。**

原项目在使用传统 NLP 算法进行句子切分时，遇到专业长难句极易断句错乱。AuraSub 彻底抛弃了物理切片，采用 LLM 进行上下文逻辑断句，在断句切分的合理性上比原项目**实现了准确率与上下文连贯性的跨越式提升**。此外，针对专业领域的错位发音，AuraSub 能在不全量灌入破坏上下文的前提下，精准替换底层词汇时间轴，从而为你提供绝对专业、无断层翻译的硬核字幕体验。

### 核心区别与特性：
- **🧠 纯正 LLM 智能断句：** 放弃 SpaCy 等机械分词。利用大模型对毫无标点的听写稿进行标点推断与逻辑从句切分，断句质量有了质的飞跃。
- **🗣️ 无损 ASR 语音纠错引擎：** 独创全局发音纠错流程，对于 Whisper 听错的专业术语（如将 "macro" 听成 "micro"），系统会基于你提供的自定义术语表进行扫描，在翻译开始前直接在底层时间轴级安全、无缝地修复单词或多词短语。
- **📚 非全量灌入的术语优化：** 在翻译阶段引入正则级别的单词边界精确匹配（Regex Word Boundaries），让 LLM 既能参照术语表意译，又不会因为全量输入过大的术语库而造成上下文污染和幻觉。
- **🪡 强效双指针时间轴对齐：** 通过精心设计的单词级双指针匹配算法，将翻译好的长句 1:1 无损绑定回底层的时间戳，有效避免翻译丢失时间轴的问题。
- **🧠 双层级推理控制：** 支持在 WebUI 中直接为“复杂任务”（句法切分、翻译）和“简单任务”（直接翻译、总结）配置不同的推理强度 (Reasoning Effort)，最大化翻译质量与性价比。
- **🍪 现代化音视频极速下载模块（Cookie & Deno 支持）：**
  - **Cookie 交互式凭证管理**：WebUI 支持直接上传任意命名的 Netscape 格式 `cookie.txt`，轻松绕过 YouTube 403 Forbidden、登录与防机器人验证。
  - **启动自检与自动更新**：启动时自动比对 PyPI 官方最新版本，杜绝因第三方接口变动导致下载失效。
  - **Deno JS 动态解密加速**：原生挂载 Deno 运行时与 EJS 模块，解除 YouTube `n-challenge` 动态签名限速。
  - **多档画质与精准诊断**：支持 1080p 超清（默认）、最佳画质 (4K/2K)、720p、480p，并提供清晰的失败原因诊断与状态反馈。
- **🍎 Apple Silicon Mac 硬件加速与一键启动：**
  - 转录引擎全面接入 **MLX-Whisper**，利用 Metal GPU 与统一内存实现 Mac 本地极速转录。
  - 时间戳强制对齐适配 PyTorch MPS 硬件加速。
  - 提供 macOS Finder 双击直启脚本 `OneKeyStart.command`，自动探测 Conda 并调起服务。
- **🎨 字幕样式与即时预览：** 新增专门的字幕自定义模块，支持动态调节中英文字号。采用合并的 ASS 方案实现无重叠的双语排版，并在不重复翻译流程的情况下秒级提取最长句的单帧画面进行效果确认。
- **✅ 坚守单行标准：** 强制控制输出格式，绝无双行字幕，提供干净、专业的学术级观影体验。
- **🎙️ 多平台高质量配音：** 无缝对接 GPT-SoVITS、Azure 等主流 TTS，一键生成多语种配音。
- 🎥 **基础架构：** 继承自 VideoLingo 优秀的框架。

### 语言支持

**输入语言：**
🇺🇸 英语 | 🇷🇺 俄语 | 🇫🇷 法语 | 🇩🇪 德语 | 🇮🇹 意大利语 | 🇪🇸 西班牙语 | 🇯🇵 日语 | 🇨🇳 中文

**翻译与配音：**
翻译支持所有主流 LLM 所涵盖的语言。配音语言的支持情况取决于您所选择的 TTS 接口类型。

## 💻 官方支持平台与硬件要求

AuraSub 专为现代硬件加速与高精度推理而设计，官方优先支持以下两大计算平台：

| 平台类型 | 硬件加速方案 | 最低/推荐要求 |
| :--- | :--- | :--- |
| 🍎 **Apple Silicon Mac** | Metal GPU / 统一内存 (`MLX-Whisper` + PyTorch `MPS`) | M1 / M2 / M3 / M4 系列芯片，macOS 13+ |
| 🎮 **Windows** | NVIDIA CUDA 硬件加速 (`WhisperX` + CTranslate2) | NVIDIA 独立显卡（GTX 1060+ / RTX 系列，建议 6GB+ 显存） |

> ⚠️ **重要提示**：**不再支持 Intel 架构 Mac (x86_64)**。因缺乏 Apple Silicon 统一内存与 Metal MLX 支持，CPU 转写推理性能极低，请使用 M 系列 Mac 或搭载 NVIDIA 显卡的 Windows 设备。

## 安装

> **注意 (Windows NVIDIA GPU 用户):** 需要先完成以下步骤以启用 CUDA 加速：
> 1. 安装 [CUDA Toolkit 12.6](https://developer.download.nvidia.com/compute/cuda/12.6.0/local_installers/cuda_12.6.0_560.76_windows.exe)
> 2. 安装 [CUDNN 9.3.0](https://developer.download.nvidia.com/compute/cudnn/9.3.0/local_installers/cudnn_9.3.0_windows.exe)
> 3. 将 `C:\Program Files\NVIDIA\CUDNN\v9.3\bin\12.6` 添加到系统环境变量 PATH 中
> 4. 重启电脑

> **注意 (必须安装 FFmpeg):** 请通过包管理器安装：
> - macOS：```brew install ffmpeg```（通过 [Homebrew](https://brew.sh/))
> - Windows：```choco install ffmpeg```（通过 [Chocolatey](https://chocolatey.org/))

1. 克隆仓库

```bash
git clone https://github.com/YourOrg/AuraSub.git
cd AuraSub
```

2. 安装依赖（需要 `python=3.10`）

```bash
conda create -n aurasub python=3.10.0 -y
conda activate aurasub
python install.py
```

3. 启动应用

```bash
streamlit run st.py
```

### Docker
还可以选择使用 Docker（要求 CUDA 12.4 和 NVIDIA Driver 版本 >550）：

```bash
docker build -t aurasub .
docker run -d -p 8501:8501 --gpus all aurasub
```

## 📝 自定义术语与 ASR 纠错
AuraSub 拥有强大的基于上下文的发音纠错能力（如将 "to" 自动纠正为 "two"）。如果你有强相关的垂直领域专业术语，可以通过以下步骤进一步提升准确率：
1. 在项目根目录下，复制 `custom_terms_template.xlsx` 并重命名为 `custom_terms.xlsx`。
2. 在该表格的第一列填入你的专业术语（如 `buccal`, `Anchorage`）。
3. 运行项目时，AuraSub 会优先基于你的术语表进行正则级扫描并自动修复原始时间轴中的听写错误。

## API 配置
AuraSub 支持 OpenAI-Like 格式的 API 调用，用于驱动核心的语义切分与翻译引擎：
- 支持目前市面上的绝大多数主流大模型（能够输出 JSON 格式即可完美跑通该流程）。
- 配音(TTS)接口支持：`azure-tts`, `openai-tts`, `fish-tts`, `GPT-SoVITS`, `edge-tts` 等。

## 当前限制
1. WhisperX 底层转录（wav2vec对齐）对重度背景噪音较敏感。对于专业领域内容，建议输入音轨较为纯净的视频，或者前置开启人声分离。
2. 整个处理管线高度依赖 LLM 返回的严格 JSON 格式化数据，如果使用较弱或不具备深度思考能力的模型，容易在中间过程因解析错误而中断。若发生此情况，请删除 `output` 文件夹并更换更强的模型重新运行。
3. 动态语速匹配虽已做了工程优化，但在语言长度结构差异极大的语种对之间，TTS 配音依然可能需要少量的人工微调。
4. **多语言视频转录识别**：受限于 WhisperX 强制对齐单词级字幕时使用的是单语言特化模型，当前流程默认仅保留并识别主要语言。

## 📄 许可证与鸣谢

本项目采用 **Apache 2.0 许可证** 开源。

**AuraSub** 是基于原开源项目 [VideoLingo](https://github.com/Huanshere/VideoLingo) 的一次独立演进（Fork/Derivative Work）。原项目由 **Huanshere** 创立，我们在此向原作者表示最诚挚的感谢——是 VideoLingo 优秀的底层工程架构，孕育了如今以“专注语义与专业翻译”为核心理念的 AuraSub。

同时，衷心感谢以下开源项目为本工具底层能力提供的支持：
[whisperX](https://github.com/m-bain/whisperX), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [json_repair](https://github.com/mangiucugna/json_repair), [BELLE](https://github.com/LianjiaTech/BELLE)
