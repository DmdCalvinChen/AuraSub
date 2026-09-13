from core.ask_gpt import ask_gpt, check_api
import streamlit as st
from core.config_utils import update_key, load_key

def config_input(label, key, help=None, placeholder=None):
    """Generic config input handler"""
    curr_val = load_key(key)
    if curr_val is None:
        curr_val = ""
    val = st.text_input(label, value=str(curr_val), help=help, placeholder=placeholder)
    if val != str(curr_val):
        update_key(key, val)
    return val

def page_setting():
    with st.expander("LLM 模型配置", expanded=True):
        config_input("API_KEY", "api.key")
        config_input("BASE_URL", "api.base_url", help="OpenAI 兼容格式，将自动补充 /v1/chat/completions")
        
        c1, c2 = st.columns([4, 1])
        with c1:
            config_input("模型 (MODEL)", "api.model", help="点击右侧按钮检查基础 API 有效性")
        with c2:
            if st.button("📡", key="api_base_btn", help="测试基础 API 连通性"):
                st.toast("基础 API 密钥有效" if check_api("base") else "基础 API 密钥无效", 
                        icon="✅" if check_api("base") else "❌")
        
        st.markdown("---")
        
        # 高低难度任务独立多模型分流开关
        curr_split = bool(load_key("model_split.enabled"))
        split_enabled = st.toggle(
            "🎛️ 开启高/低难度任务独立模型配置",
            value=curr_split,
            help="为高难度推理任务（如分句、ASR纠错、意译润色）与轻量任务（直译、摘要等）分别配置不同的厂商、模型、密钥与推理强度"
        )
        if split_enabled != curr_split:
            update_key("model_split.enabled", split_enabled)
            st.rerun()
            
        reasoning_options = ["none", "low", "medium", "high"]
        
        if not split_enabled:
            st.markdown("**🧠 思考/推理强度 (Reasoning Effort)**")
            r1, r2 = st.columns(2)
            with r1:
                curr_hard = load_key("reasoning.hard_tasks") or "high"
                hard_tasks_effort = st.selectbox(
                    "困难任务推理强度", 
                    options=reasoning_options,
                    index=reasoning_options.index(curr_hard) if curr_hard in reasoning_options else 2,
                    help="用于语义分句、ASR纠错、意译润色、标点推断"
                )
                if hard_tasks_effort != curr_hard:
                    update_key("reasoning.hard_tasks", hard_tasks_effort)
                    
            with r2:
                curr_easy = load_key("reasoning.easy_tasks") or "low"
                easy_tasks_effort = st.selectbox(
                    "简单任务推理强度", 
                    options=reasoning_options,
                    index=reasoning_options.index(curr_easy) if curr_easy in reasoning_options else 1,
                    help="用于逐词直译、视频摘要、配音裁剪"
                )
                if easy_tasks_effort != curr_easy:
                    update_key("reasoning.easy_tasks", easy_tasks_effort)
                    
            st.caption("⚠️ **建议：** 翻译任务通常不建议使用 `high`，以兼顾响应速度与成本。")
        else:
            # 困难任务配置区
            st.markdown("##### 🧠 困难任务专属模型")
            st.caption("负责：语义智能分句、ASR 术语纠错、意译与润色、智能标点还原")
            config_input("困难任务 API_KEY", "model_split.hard_tasks.key", placeholder="留空则自动继承基础 API_KEY")
            config_input("困难任务 BASE_URL", "model_split.hard_tasks.base_url", placeholder="留空则自动继承基础 BASE_URL")
            
            hc1, hc2 = st.columns([4, 1])
            with hc1:
                config_input("困难任务 MODEL", "model_split.hard_tasks.model", placeholder="例如 o3-mini, deepseek-reasoner 等")
            with hc2:
                if st.button("📡", key="api_hard_btn", help="测试困难任务 API 连通性"):
                    st.toast("困难任务 API 有效" if check_api("hard") else "困难任务 API 无效", 
                            icon="✅" if check_api("hard") else "❌")
                            
            curr_h_effort = load_key("model_split.hard_tasks.reasoning_effort") or "high"
            h_effort = st.selectbox(
                "困难任务推理强度",
                options=reasoning_options,
                index=reasoning_options.index(curr_h_effort) if curr_h_effort in reasoning_options else 3,
                key="hard_tasks_split_effort"
            )
            if h_effort != curr_h_effort:
                update_key("model_split.hard_tasks.reasoning_effort", h_effort)
                
            st.markdown("---")
            # 简单任务配置区
            st.markdown("##### ⚡ 简单任务专属模型")
            st.caption("负责：逐词直译、视频内容摘要、字幕配音裁剪")
            config_input("简单任务 API_KEY", "model_split.easy_tasks.key", placeholder="留空则自动继承基础 API_KEY")
            config_input("简单任务 BASE_URL", "model_split.easy_tasks.base_url", placeholder="留空则自动继承基础 BASE_URL")
            
            ec1, ec2 = st.columns([4, 1])
            with ec1:
                config_input("简单任务 MODEL", "model_split.easy_tasks.model", placeholder="例如 gpt-4o-mini, deepseek-chat 等")
            with ec2:
                if st.button("📡", key="api_easy_btn", help="测试简单任务 API 连通性"):
                    st.toast("简单任务 API 有效" if check_api("easy") else "简单任务 API 无效", 
                            icon="✅" if check_api("easy") else "❌")
                            
            curr_e_effort = load_key("model_split.easy_tasks.reasoning_effort") or "low"
            e_effort = st.selectbox(
                "简单任务推理强度",
                options=reasoning_options,
                index=reasoning_options.index(curr_e_effort) if curr_e_effort in reasoning_options else 1,
                key="easy_tasks_split_effort"
            )
            if e_effort != curr_e_effort:
                update_key("model_split.easy_tasks.reasoning_effort", e_effort)
    
    with st.expander("转写和字幕设置", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            langs = {
                "🇺🇸 English": "en",
                "🇨🇳 简体中文": "zh",
                "🇪🇸 Español": "es",
                "🇷🇺 Русский": "ru",
                "🇫🇷 Français": "fr",
                "🇩🇪 Deutsch": "de",
                "🇮🇹 Italiano": "it",
                "🇯🇵 日本語": "ja"
            }
            lang = st.selectbox(
                "识别语言:", 
                options=list(langs.keys()),
                index=list(langs.values()).index(load_key("whisper.language"))
            )
            if langs[lang] != load_key("whisper.language"):
                update_key("whisper.language", langs[lang])

        with c2:
            target_language = st.text_input("目标语言", value=load_key("target_language"))
            if target_language != load_key("target_language"):
                update_key("target_language", target_language)

        demucs = st.toggle("人声分离增强", value=load_key("demucs"), help="推荐用于背景噪音较大的视频，但会增加处理时间")
        if demucs != load_key("demucs"):
            update_key("demucs", demucs)

        burn_subtitles = st.toggle("压制字幕", value=load_key("resolution") != "0x0", help="需要更长处理时间")
        
        resolution_options = {
            "1080p": "1920x1080",
            "360p": "640x360"
        }
            
        if burn_subtitles:
            selected_resolution = st.selectbox(
                "视频分辨率",
                options=list(resolution_options.keys()),
                index=list(resolution_options.values()).index(load_key("resolution")) if load_key("resolution") != "0x0" else 0
            )
            resolution = resolution_options[selected_resolution]
        else:
            resolution = "0x0"

        if resolution != load_key("resolution"):
            update_key("resolution", resolution)
        
    with st.expander("配音设置", expanded=True):
        tts_methods = ["azure_tts", "openai_tts", "fish_tts", "sf_fish_tts", "edge_tts", "gpt_sovits", "custom_tts"]
        select_tts = st.selectbox("TTS方法", options=tts_methods, index=tts_methods.index(load_key("tts_method")))
        if select_tts != load_key("tts_method"):
            update_key("tts_method", select_tts)

        # sub settings for each tts method
        if select_tts == "sf_fish_tts":
            config_input("SiliconFlow API密钥", "sf_fish_tts.api_key")
            
            # Add mode selection dropdown
            mode_options = {
                "preset": "preset",
                "custom": "clone(stable)",
                "dynamic": "clone(dynamic)"
            }
            selected_mode = st.selectbox(
                "模式选择",
                options=list(mode_options.keys()),
                format_func=lambda x: mode_options[x],
                index=list(mode_options.keys()).index(load_key("sf_fish_tts.mode")) if load_key("sf_fish_tts.mode") in mode_options.keys() else 0
            )
            if selected_mode != load_key("sf_fish_tts.mode"):
                update_key("sf_fish_tts.mode", selected_mode)
                
            if selected_mode == "preset":
                config_input("语音", "sf_fish_tts.voice")

        elif select_tts == "openai_tts":
            config_input("302ai API", "openai_tts.api_key")
            config_input("OpenAI语音", "openai_tts.voice")

        elif select_tts == "fish_tts":
            config_input("302ai API", "fish_tts.api_key")
            fish_tts_character = st.selectbox("Fish TTS角色", options=list(load_key("fish_tts.character_id_dict").keys()), index=list(load_key("fish_tts.character_id_dict").keys()).index(load_key("fish_tts.character")))
            if fish_tts_character != load_key("fish_tts.character"):
                update_key("fish_tts.character", fish_tts_character)

        elif select_tts == "azure_tts":
            config_input("302ai API", "azure_tts.api_key")
            config_input("Azure语音", "azure_tts.voice")
        
        elif select_tts == "gpt_sovits":
            st.info("配置GPT_SoVITS，请参考Github主页")
            config_input("SoVITS角色", "gpt_sovits.character")
            
            refer_mode_options = {1: "模式1：仅用提供的参考音频", 2: "模式2：仅用视频第1条语音做参考", 3: "模式3：使用视频每一条语音做参考"}
            selected_refer_mode = st.selectbox(
                "参考模式",
                options=list(refer_mode_options.keys()),
                format_func=lambda x: refer_mode_options[x],
                index=list(refer_mode_options.keys()).index(load_key("gpt_sovits.refer_mode")),
                help="配置GPT-SoVITS的参考音频模式"
            )
            if selected_refer_mode != load_key("gpt_sovits.refer_mode"):
                update_key("gpt_sovits.refer_mode", selected_refer_mode)
        elif select_tts == "edge_tts":
            config_input("Edge TTS语音", "edge_tts.voice")
