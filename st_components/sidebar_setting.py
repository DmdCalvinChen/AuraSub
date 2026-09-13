from core.ask_gpt import ask_gpt, check_api
import streamlit as st
from core.config_utils import update_key, load_key

def config_input(label, key, help=None, placeholder=None):
    """Generic config input handler"""
    try:
        curr_val = load_key(key)
    except KeyError:
        curr_val = ""
    if curr_val is None:
        curr_val = ""
    val = st.text_input(label, value=str(curr_val), help=help, placeholder=placeholder)
    if val != str(curr_val):
        update_key(key, val)
    return val

def page_setting():
    with st.expander("LLM Configuration", expanded=True):
        config_input("API_KEY", "api.key")
        config_input("BASE_URL", "api.base_url", help="Openai format, will add /v1/chat/completions automatically")
        
        c1, c2 = st.columns([4, 1])
        with c1:
            config_input("MODEL", "api.model", help="click to check API validity 👉")
        with c2:
            if st.button("📡", key="api_base_btn", help="Test Base API connection"):
                st.toast("Base API Key is valid" if check_api("base") else "Base API Key is invalid", 
                        icon="✅" if check_api("base") else "❌")
        
        st.markdown("---")
        
        # Advanced Multi-Model Task Splitting
        curr_split = bool(load_key("model_split.enabled"))
        split_enabled = st.toggle(
            "🎛️ Advanced Multi-Model Configuration",
            value=curr_split,
            help="Configure separate providers, models, keys, and reasoning efforts for Hard Tasks vs Easy Tasks"
        )
        if split_enabled != curr_split:
            update_key("model_split.enabled", split_enabled)
            st.rerun()
            
        reasoning_options = ["none", "low", "medium", "high"]
        
        if not split_enabled:
            st.markdown("**🧠 Thinking / Reasoning Effort**")
            r1, r2 = st.columns(2)
            with r1:
                curr_hard = load_key("reasoning.hard_tasks") or "high"
                hard_tasks_effort = st.selectbox(
                    "Hard Tasks", 
                    options=reasoning_options,
                    index=reasoning_options.index(curr_hard) if curr_hard in reasoning_options else 2,
                    help="Chunking, ASR Correction, Expressive Translation, Punctuation"
                )
                if hard_tasks_effort != curr_hard:
                    update_key("reasoning.hard_tasks", hard_tasks_effort)
                    
            with r2:
                curr_easy = load_key("reasoning.easy_tasks") or "low"
                easy_tasks_effort = st.selectbox(
                    "Easy Tasks", 
                    options=reasoning_options,
                    index=reasoning_options.index(curr_easy) if curr_easy in reasoning_options else 1,
                    help="Summarization, Direct Translation"
                )
                if easy_tasks_effort != curr_easy:
                    update_key("reasoning.easy_tasks", easy_tasks_effort)
                    
            st.caption("⚠️ **Tip:** Not recommended to use `high`. Translation tasks are not that complex.")
        else:
            # Hard Tasks Section
            st.markdown("##### 🧠 Hard Tasks Model")
            st.caption("For Semantic Chunking, ASR Correction, Expressive Translation, Punctuation")
            config_input("Hard Tasks API_KEY", "model_split.hard_tasks.key", placeholder="Leave empty to use Base API_KEY")
            config_input("Hard Tasks BASE_URL", "model_split.hard_tasks.base_url", placeholder="Leave empty to use Base BASE_URL")
            
            hc1, hc2 = st.columns([4, 1])
            with hc1:
                config_input("Hard Tasks MODEL", "model_split.hard_tasks.model", placeholder="e.g. o3-mini, deepseek-reasoner")
            with hc2:
                if st.button("📡", key="api_hard_btn", help="Test Hard Tasks API"):
                    st.toast("Hard Tasks API is valid" if check_api("hard") else "Hard Tasks API is invalid", 
                            icon="✅" if check_api("hard") else "❌")
                            
            curr_h_effort = load_key("model_split.hard_tasks.reasoning_effort") or "high"
            h_effort = st.selectbox(
                "Hard Tasks Reasoning Effort",
                options=reasoning_options,
                index=reasoning_options.index(curr_h_effort) if curr_h_effort in reasoning_options else 3,
                key="hard_tasks_split_effort"
            )
            if h_effort != curr_h_effort:
                update_key("model_split.hard_tasks.reasoning_effort", h_effort)
                
            st.markdown("---")
            # Easy Tasks Section
            st.markdown("##### ⚡ Easy Tasks Model")
            st.caption("For Direct Translation, Video Summary, Subtitle Trim")
            config_input("Easy Tasks API_KEY", "model_split.easy_tasks.key", placeholder="Leave empty to use Base API_KEY")
            config_input("Easy Tasks BASE_URL", "model_split.easy_tasks.base_url", placeholder="Leave empty to use Base BASE_URL")
            
            ec1, ec2 = st.columns([4, 1])
            with ec1:
                config_input("Easy Tasks MODEL", "model_split.easy_tasks.model", placeholder="e.g. gpt-4o-mini, deepseek-chat")
            with ec2:
                if st.button("📡", key="api_easy_btn", help="Test Easy Tasks API"):
                    st.toast("Easy Tasks API is valid" if check_api("easy") else "Easy Tasks API is invalid", 
                            icon="✅" if check_api("easy") else "❌")
                            
            curr_e_effort = load_key("model_split.easy_tasks.reasoning_effort") or "low"
            e_effort = st.selectbox(
                "Easy Tasks Reasoning Effort",
                options=reasoning_options,
                index=reasoning_options.index(curr_e_effort) if curr_e_effort in reasoning_options else 1,
                key="easy_tasks_split_effort"
            )
            if e_effort != curr_e_effort:
                update_key("model_split.easy_tasks.reasoning_effort", e_effort)
    
    with st.expander("Subtitles Settings", expanded=True):
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
                "Recog Lang",
                options=list(langs.keys()),
                index=list(langs.values()).index(load_key("whisper.language"))
            )
            if langs[lang] != load_key("whisper.language"):
                update_key("whisper.language", langs[lang])

        with c2:
            target_language = st.text_input("Target Lang", value=load_key("target_language"))
            if target_language != load_key("target_language"):
                update_key("target_language", target_language)

        demucs = st.toggle("Vocal separation enhance", value=load_key("demucs"), help="Recommended for videos with loud background noise, but will increase processing time")
        if demucs != load_key("demucs"):
            update_key("demucs", demucs)
        
        burn_subtitles = st.toggle("Burn-in Subtitles", value=load_key("resolution") != "0x0", help="takes longer time")
        
        resolution_options = {
            "1080p": "1920x1080",
            "360p": "640x360"
        }
        
        if burn_subtitles:
            selected_resolution = st.selectbox(
                "Video Resolution",
                options=list(resolution_options.keys()),
                index=list(resolution_options.values()).index(load_key("resolution")) if load_key("resolution") != "0x0" else 0
            )
            resolution = resolution_options[selected_resolution]
        else:
            resolution = "0x0"

        if resolution != load_key("resolution"):
            update_key("resolution", resolution)
        
    with st.expander("Dubbing Settings", expanded=True):
        tts_methods = ["azure_tts", "openai_tts", "fish_tts", "sf_fish_tts", "edge_tts", "gpt_sovits", "custom_tts"]
        select_tts = st.selectbox("TTS Method", options=tts_methods, index=tts_methods.index(load_key("tts_method")))
        if select_tts != load_key("tts_method"):
            update_key("tts_method", select_tts)

        # sub settings for each tts method
        if select_tts == "sf_fish_tts":
            config_input("SiliconFlow API Key", "sf_fish_tts.api_key")
            
            # Add mode selection dropdown
            mode_options = {
                "preset": "Preset",
                "custom": "Refer_stable",
                "dynamic": "Refer_dynamic"
            }
            selected_mode = st.selectbox(
                "Mode Selection",
                options=list(mode_options.keys()),
                format_func=lambda x: mode_options[x],
                index=list(mode_options.keys()).index(load_key("sf_fish_tts.mode")) if load_key("sf_fish_tts.mode") in mode_options.keys() else 0
            )
            if selected_mode != load_key("sf_fish_tts.mode"):
                update_key("sf_fish_tts.mode", selected_mode)
                
            if selected_mode == "preset":
                config_input("Voice", "sf_fish_tts.voice")

        elif select_tts == "openai_tts":
            config_input("302ai API", "openai_tts.api_key")
            config_input("OpenAI Voice", "openai_tts.voice")

        elif select_tts == "fish_tts":
            config_input("302ai API", "fish_tts.api_key")
            fish_tts_character = st.selectbox("Fish TTS Character", options=list(load_key("fish_tts.character_id_dict").keys()), index=list(load_key("fish_tts.character_id_dict").keys()).index(load_key("fish_tts.character")))
            if fish_tts_character != load_key("fish_tts.character"):
                update_key("fish_tts.character", fish_tts_character)

        elif select_tts == "azure_tts":
            config_input("302ai API", "azure_tts.api_key")
            config_input("Azure Voice", "azure_tts.voice")
        
        elif select_tts == "gpt_sovits":
            st.info("Please refer to Github homepage for GPT_SoVITS configuration")
            config_input("SoVITS Character", "gpt_sovits.character")
            
            refer_mode_options = {1: "Mode 1: Use provided reference audio only", 2: "Mode 2: Use first audio from video as reference", 3: "Mode 3: Use each audio from video as reference"}
            selected_refer_mode = st.selectbox(
                "Refer Mode",
                options=list(refer_mode_options.keys()),
                format_func=lambda x: refer_mode_options[x],
                index=list(refer_mode_options.keys()).index(load_key("gpt_sovits.refer_mode")),
                help="Configure reference audio mode for GPT-SoVITS"
            )
            if selected_refer_mode != load_key("gpt_sovits.refer_mode"):
                update_key("gpt_sovits.refer_mode", selected_refer_mode)
        elif select_tts == "edge_tts":
            config_input("Edge TTS Voice", "edge_tts.voice")