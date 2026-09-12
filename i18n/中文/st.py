import streamlit as st
import os, sys
from st_components.imports_and_utils import *
from core.config_utils import load_key

# SET PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
bin_dir = os.path.dirname(sys.executable)
os.environ['PATH'] = f"{bin_dir}:/opt/homebrew/bin:/usr/local/bin:{current_dir}" + os.pathsep + os.environ.get('PATH', '')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="AuraSub", page_icon="docs/logo.svg")

@st.cache_resource(show_spinner=False)
def auto_check_ytdlp():
    from core.step1_ytdlp import check_and_update_ytdlp
    return check_and_update_ytdlp(force=False, timeout=3)

auto_check_ytdlp()

SUB_VIDEO = "output/output_sub.mp4"
DUB_VIDEO = "output/output_dub.mp4"

def text_processing_section():
    st.header("翻译和生成字幕")
    with st.container(border=True):
        st.markdown("""
        <p style='font-size: 20px;'>
        此阶段包含以下步骤：
        <p style='font-size: 20px;'>
            1. WhisperX 逐字转录<br>
            2. 标点符号恢复 (无损 NLP)<br>
            3. ASR 语音纠错 (基于自定义术语表)<br>
            4. LLM 智能上下文逻辑断句<br>
            5. 总结与多步翻译<br>
            6. 生成最终时间轴与字幕配置文件
        """, unsafe_allow_html=True)

        if not os.path.exists("output/trans.srt"):
            if load_key("resolution") == "0x0":
                st.warning("⚠️ 侧边栏中的'压制字幕到视频'已关闭！当前处理只会生成字幕文件。如果需要压制视频，请在侧边栏中开启该选项。", icon="⚠️")
            if st.button("开始处理字幕", key="text_processing_button"):
                if load_key("resolution") == "0x0":
                    st.error("❌ 无法开始处理：请先在侧边栏中开启'压制字幕到视频'！")
                    st.toast("⚠️ 请先在侧边栏开启'压制字幕到视频'！", icon="⚠️")
                else:
                    process_text()
                    st.rerun()
        else:
            st.success("✅ 字幕文件生成完毕！请在下方【字幕样式与即时预览】面板中确认样式并压制视频。")
            download_subtitle_zip_button(text="下载所有字幕文件")
            
            if st.button("归档到'历史记录'", key="cleanup_in_text_processing"):
                cleanup()
                st.rerun()
            return True

def process_text():
    with st.spinner("使用 Whisper 进行转录中..."):
        step2_whisperX.transcribe()
    with st.spinner("恢复标点符号中..."):
        from core import step2_5_add_punctuation
        step2_5_add_punctuation.add_punctuation_main()
    with st.spinner("ASR 发音纠错中..."):
        from core import step2_6_asr_correction
        step2_6_asr_correction.asr_correction_main()
    with st.spinner("LLM 智能断句中..."):
        from core import step3_semantic_chunking
        step3_semantic_chunking.split_by_semantic_chunking()
    with st.spinner("总结和翻译中..."):
        step4_1_summarize.get_summary()
        if load_key("pause_before_translate"):
            st.warning("⚠️ 翻译前暂停已开启。请编辑 `output/log/terminology.json` 中的术语表，完成后点击下方按钮继续。")
            st.session_state.setdefault('translation_paused', True)
            if st.session_state.get('translation_paused', False):
                if st.button("继续翻译", key="continue_translate"):
                    st.session_state['translation_paused'] = False
                    st.rerun()
                st.stop()
        step4_2_translate_all.translate_all()
    with st.spinner("处理和对齐字幕中..."): 
        from core import step6_generate_final_timeline
        step6_generate_final_timeline.align_timestamp_main()
    
    st.success("字幕文本处理完成！🎉")
    st.balloons()

def subtitle_customization_section():
    if os.path.exists("output/trans.srt"):
        st.header("字幕样式与即时预览")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                target_size = st.slider("目标语言（中文字幕）字号", 5, 40, load_key("subtitle.target_font_size"))
            with col2:
                source_size = st.slider("源语言（英文字幕）字号", 5, 40, load_key("subtitle.source_font_size"))
            
            if st.button("生成单帧预览", key="generate_preview"):
                if load_key("resolution") == "0x0":
                    st.error("❌ 无法预览：请先在侧边栏开启'压制字幕到视频'选项！")
                    st.toast("⚠️ 请先开启'压制字幕到视频'！", icon="⚠️")
                else:
                    from core.config_utils import update_key
                    update_key("subtitle.target_font_size", target_size)
                    update_key("subtitle.source_font_size", source_size)
                    st.session_state.preview_generated = True
                    from core.step7_merge_sub_to_vid import generate_preview_frame
                    with st.spinner("正在寻找最长句子并生成预览画面..."):
                        preview_path = generate_preview_frame(target_size, source_size)
                        if preview_path and os.path.exists(preview_path):
                            try:
                                st.image(preview_path, use_container_width=True)
                            except TypeError:
                                st.image(preview_path, use_column_width=True)
                        else:
                            st.warning("预览生成失败。")
            
            if os.path.exists("output/trans.srt"):
                # Ensure the user must preview the current slider values before merging
                current_target = load_key("subtitle.target_font_size")
                current_source = load_key("subtitle.source_font_size")
                
                is_preview_valid = (
                    target_size == current_target and 
                    source_size == current_source and 
                    st.session_state.get('preview_generated', False)
                )
                
                button_label = "重新压制 (应用新样式)" if os.path.exists(SUB_VIDEO) else "确认样式并开始压制视频"
                
                if st.button(button_label, key="remerge_subtitles"):
                    if not is_preview_valid:
                        st.error("❌ 压制前请务必先点击『生成单帧预览』确认最终样式！")
                        st.toast("⚠️ 请先生成预览！", icon="⚠️")
                    elif load_key("resolution") == "0x0":
                        st.error("❌ 无法压制字幕：请先在侧边栏开启'压制字幕到视频'选项！")
                        st.toast("⚠️ 请先开启'压制字幕到视频'！", icon="⚠️")
                    else:
                        from core.config_utils import update_key
                        update_key("subtitle.target_font_size", target_size)
                        update_key("subtitle.source_font_size", source_size)
                        from core import step7_merge_sub_to_vid
                        with st.spinner("正在将字幕硬编码压制到视频中（这可能需要一分钟左右）..."):
                            step7_merge_sub_to_vid.merge_subtitles_to_video()
                        st.success("视频压制成功！🎉")
                        st.rerun()
                
                if os.path.exists(SUB_VIDEO):
                    if load_key("resolution") != "0x0":
                        st.video(SUB_VIDEO)

def audio_processing_section():
    st.header("配音")
    with st.container(border=True):
        st.markdown("""
        <p style='font-size: 20px;'>
        此阶段包含以下步骤：
        <p style='font-size: 20px;'>
            1. 生成音频任务和分段<br>
            2. 提取参考音频<br>
            3. 生成和合并音频文件<br>
            4. 将最终音频合并到视频中
        """, unsafe_allow_html=True)
        if not os.path.exists(DUB_VIDEO):
            if st.button("开始处理配音", key="audio_processing_button"):
                process_audio()
                st.rerun()
        else:
            st.success("音频处理完成！你可以在 `output` 文件夹中查看音频文件。")
            if load_key("resolution") != "0x0": 
                st.video(DUB_VIDEO) 
            if st.button("删除配音临时文件", key="delete_dubbing_files"):
                delete_dubbing_files()
                st.rerun()
            if st.button("归档到'历史记录'", key="cleanup_in_audio_processing"):
                cleanup()
                st.rerun()

def process_audio():
    with st.spinner("生成音频任务中"): 
        step8_1_gen_audio_task.gen_audio_task_main()
        step8_2_gen_dub_chunks.gen_dub_chunks()
    with st.spinner("提取参考音频中"):
        step9_extract_refer_audio.extract_refer_audio_main()
    with st.spinner("生成所有音频中"):
        step10_gen_audio.gen_audio()
    with st.spinner("合并完整音频中"):
        step11_merge_full_audio.merge_full_audio()
    with st.spinner("将配音合并到视频中"):
        step12_merge_dub_to_vid.merge_video_audio()
    
    st.success("音频处理完成！🎇")
    st.balloons()

def main():
    st.markdown("<h1 style='text-align: center; color: #144070; margin-bottom: 30px;'>AuraSub</h1>", unsafe_allow_html=True)
    st.markdown(button_style, unsafe_allow_html=True)
    # add settings
    with st.sidebar:
        page_setting()
        st.markdown(give_star_button, unsafe_allow_html=True)
    download_video_section()
    text_processing_section()
    subtitle_customization_section()
    audio_processing_section()

if __name__ == "__main__":
    main()
