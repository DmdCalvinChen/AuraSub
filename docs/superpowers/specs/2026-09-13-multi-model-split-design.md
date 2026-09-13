# AuraSub 高低难度任务独立多模型与推理配置设计规范 (Design Spec)

## 1. 概述与设计目标
AuraSub 当前支持在同一 LLM 提供商与模型下对“困难任务”和“简单任务”分别指定不同的推理强度（`reasoning_effort`）。为了满足用户在不同阶段使用不同模型/厂商的需求（例如：使用高智力推理模型如 DeepSeek-R1 / o3-mini 处理分句和意译润色，使用低成本高速模型如 GPT-4o-mini / DeepSeek-V3 处理直译和摘要），本项目将高低难度任务的核心配置彻底解耦。

### 核心功能目标
1. **完全独立的模型与厂商配置**：困难任务与简单任务支持独立配置厂商 API 地址（`base_url`）、密钥（`key`）、模型名称（`model`）及推理强度（`reasoning_effort`）。
2. **纯 OpenAI 规范 Reasoning 传递**：采用标准的 `reasoning_effort` 参数（支持 `none` / `low` / `medium` / `high`），通过 `extra_body` 传递。
3. **安全隔离**：新增的 API 密钥自动被 `config_utils.py` 识别并存储至 `.secret`，杜绝明文写入 `config.yaml`。
4. **平滑回退（Fallback）与向下兼容**：若未开启分流或分流字段为空，自动继承基础 API 配置，确保原有项目行为不受影响。
5. **渐进式 WebUI 交互**：默认隐藏独立分流配置保持界面清爽；在侧边栏点击开启「🎛️ 高级模型分流配置」后动态展开困难与简单任务的专属配置面板，并提供独立的连通性测试按钮。

---

## 2. 架构设计与配置结构

### 2.1 `config.yaml` 配置结构演进

```yaml
# 基础/全局默认 API 配置
api:
  key: 'not here'
  base_url: 'https://api.openai.com/v1'
  model: 'gpt-4o'

# 高低难度任务独立多模型与推理配置 (Multi-Model Task Splitting)
model_split:
  enabled: false # 是否启用独立模型分流 (默认 False)
  hard_tasks:
    key: 'not here'
    base_url: '' # 留空时自动回退至 api.base_url
    model: ''    # 留空时自动回退至 api.model
    reasoning_effort: 'high' # none / low / medium / high
  easy_tasks:
    key: 'not here'
    base_url: '' # 留空时自动回退至 api.base_url
    model: ''    # 留空时自动回退至 api.model
    reasoning_effort: 'low'  # none / low / medium / high

# 全局推理强度设置 (当 model_split.enabled 为 false 时使用)
reasoning:
  hard_tasks: 'medium'
  easy_tasks: 'low'
```

### 2.2 `.secret` 安全隔离与读写机制
- `core/config_utils.py` 中的 `is_sensitive_key` 函数已实现 `key.endswith('.key')` 规则。
- `model_split.hard_tasks.key` 与 `model_split.easy_tasks.key` 将自动路由至本地 `.secret` 存储，在 `config.yaml` 中仅存储占位符 `'not here'`。

---

## 3. 核心调用逻辑设计 (`core/ask_gpt.py`)

### 3.1 任务分类矩阵
系统根据 `log_title` 判定当前调用的难度属性：

| 任务类型 | 包含的 `log_title` | 涉及的执行文件 |
| :--- | :--- | :--- |
| 🧠 **困难任务 (Hard Tasks)** | `logical_chunking`<br>`asr_correction_*`<br>`translate_expressiveness`<br>`punctuation`<br>`sentence_splitbymeaning` | [step3_semantic_chunking.py](file:///Users/chen/code/AuraSub/core/step3_semantic_chunking.py)<br>[step2_6_asr_correction.py](file:///Users/chen/code/AuraSub/core/step2_6_asr_correction.py)<br>[translate_once.py](file:///Users/chen/code/AuraSub/core/translate_once.py)<br>[step2_5_add_punctuation.py](file:///Users/chen/code/AuraSub/core/step2_5_add_punctuation.py) |
| ⚡ **简单任务 (Easy Tasks)** | `translate_faithfulness`<br>`summary`<br>`subtitle_trim`<br>`tts_correct_text`<br>`default` 等 | [translate_once.py](file:///Users/chen/code/AuraSub/core/translate_once.py)<br>[step4_1_summarize.py](file:///Users/chen/code/AuraSub/core/step4_1_summarize.py)<br>[step8_1_gen_audio_task.py](file:///Users/chen/code/AuraSub/core/step8_1_gen_audio_task.py)<br>[all_tts_functions/tts_main.py](file:///Users/chen/code/AuraSub/core/all_tts_functions/tts_main.py) |

### 3.2 动态配置解析与客户端初始化
```python
def resolve_api_config(is_hard: bool):
    """根据任务难度和分流开关动态解析 API 配置与推理参数"""
    base_api = load_key("api")
    is_split_enabled = False
    try:
        is_split_enabled = load_key("model_split.enabled")
    except Exception:
        is_split_enabled = False

    if is_split_enabled:
        split_key = "model_split.hard_tasks" if is_hard else "model_split.easy_tasks"
        try:
            task_cfg = load_key(split_key)
            api_key = task_cfg.get("key") or base_api.get("key")
            base_url = task_cfg.get("base_url") or base_api.get("base_url")
            model = task_cfg.get("model") or base_api.get("model")
            effort = task_cfg.get("reasoning_effort") or ("high" if is_hard else "low")
            return api_key, base_url, model, effort
        except Exception:
            pass

    # Fallback to base configuration
    effort_key = "reasoning.hard_tasks" if is_hard else "reasoning.easy_tasks"
    effort = load_key(effort_key)
    return base_api.get("key"), base_api.get("base_url"), base_api.get("model"), effort
```

### 3.3 Reasoning 参数封装
- 当 `effort` 存在且其小写不为 `'none'` 时，注入 `completion_args["extra_body"] = {"reasoning_effort": effort}`。
- 在日志和控制台中明确输出：
  `[🧠 Hard Task] Target: https://api.openai.com/v1 | Model: o3-mini | Effort: high`
  `[⚡ Easy Task] Target: https://api.deepseek.com/v1 | Model: deepseek-chat | Effort: none`

### 3.4 API 有效性测试函数重构
在 [sidebar_setting.py](file:///Users/chen/code/AuraSub/st_components/sidebar_setting.py) 中，`check_api()` 升级为支持分别针对 `base`、`hard`、`easy` 三个配置块进行连通性测试：
- `check_api(target="base")`
- `check_api(target="hard")`
- `check_api(target="easy")`

---

## 4. WebUI 界面交互设计 (`sidebar_setting.py`)

在 WebUI 侧边栏的 `LLM Configuration`（LLM 配置）面板中：

1. **基础配置区（常驻）**：
   - `API_KEY` 输入框
   - `BASE_URL` 输入框
   - `MODEL` 模型输入框 + `📡` 连通性测试按钮
2. **高级分流开关**：
   - `st.toggle("🎛️ 开启高/低难度任务独立模型配置", value=load_key("model_split.enabled"), key="model_split_toggle")`
3. **未开启分流时**：
   - 保持现有的双列选择框：`Hard Tasks` 推理等级下拉框 + `Easy Tasks` 推理等级下拉框。
4. **开启分流时（动态展开）**：
   - **🧠 困难任务配置 (Hard Tasks: 语义分句 / ASR纠错 / 意译润色 / 标点还原)**：
     - `API_KEY`（占位提示：留空则使用基础 API_KEY）
     - `BASE_URL`（占位提示：留空则使用基础 BASE_URL）
     - `MODEL` + `📡` 测试按钮
     - `Reasoning Effort` 下拉选择 (`none`, `low`, `medium`, `high`)
   - **⚡ 简单任务配置 (Easy Tasks: 直译 / 全局摘要 / 语音裁剪等)**：
     - `API_KEY`（占位提示：留空则使用基础 API_KEY）
     - `BASE_URL`（占位提示：留空则使用基础 BASE_URL）
     - `MODEL` + `📡` 测试按钮
     - `Reasoning Effort` 下拉选择 (`none`, `low`, `medium`, `high`)

---

## 5. 验证与测试计划

1. **配置读写与安全隔离测试**：
   - 写入 `model_split.hard_tasks.key`，验证自动写入 `.secret` 且 `config.yaml` 保持 `'not here'`。
2. **单步调用路由测试**：
   - 运行 `ask_gpt` 模拟 `logical_chunking` 任务，验证正确读取 `model_split.hard_tasks` 中的模型与 URL。
   - 运行 `ask_gpt` 模拟 `summary` 任务，验证正确读取 `model_split.easy_tasks` 中的模型与 URL。
3. **Fallback 回退测试**：
   - 开启 `model_split.enabled` 但 `base_url`/`key` 留空，验证正确回退至基础 `api` 配置。
   - 关闭 `model_split.enabled`，验证完全按照全局基础 `api` 运行。
4. **WebUI 交互测试**：
   - 切换开关与修改各项参数，验证界面即时响应且无报错。
   - 分别点击三个 `📡` 测试按钮，验证能独立反馈各模型的连通性状态。
