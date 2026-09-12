import streamlit as st
import os, sys
from st_components.imports_and_utils import *
from core.config_utils import load_key

# SET PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
bin_dir = os.path.dirname(sys.executable)
os.environ['PATH'] = f"{bin_dir}:/opt/homebrew/bin:/usr/local/bin:{current_dir}" + os.pathsep + os.environ.get('PATH', '')
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
    st.header("Translate and Generate Subtitles")
    with st.container(border=True):
        st.markdown("""
        <p style='font-size: 20px;'>
        This stage includes the following steps:
        <p style='font-size: 20px;'>
            1. WhisperX word-level transcription<br>
            2. Punctuation restoration (Zero-loss NLP)<br>
            3. ASR phonetic error correction (Terminology-driven)<br>
            4. Sentence logical segmentation (Context-aware LLM)<br>
            5. Summarization and multi-step translation<br>
            6. Generating timeline and subtitles
        """, unsafe_allow_html=True)

        if not os.path.exists("output/trans.srt"):
            if load_key("resolution") == "0x0":
                st.warning("⚠️ 'Burn-in Subtitles' is disabled in the sidebar! Processing now will only generate a blank/placeholder video. Please turn it ON in the sidebar to burn subtitles into your video.", icon="⚠️")
            if st.button("Start Processing Subtitles", key="text_processing_button"):
                if load_key("resolution") == "0x0":
                    st.error("❌ Cannot start processing: Please turn on 'Burn-in Subtitles' in the sidebar first!")
                    st.toast("⚠️ Please turn on 'Burn-in Subtitles' in the sidebar!", icon="⚠️")
                else:
                    process_text()
                    st.rerun()
        else:
            st.success("✅ Text processing complete! Please proceed to the 'Subtitle Style Preview' section below to configure and burn your subtitles.")
            download_subtitle_zip_button(text="Download All Srt Files")
            
            if st.button("Archive to 'history'", key="cleanup_in_text_processing"):
                cleanup()
                st.rerun()
            return True

def process_text():
    with st.spinner("Using Whisper for transcription..."):
        step2_whisperX.transcribe()
    with st.spinner("Adding Punctuation..."):
        from core import step2_5_add_punctuation
        step2_5_add_punctuation.add_punctuation_main()
    with st.spinner("ASR Error Correction..."):
        from core import step2_6_asr_correction
        step2_6_asr_correction.asr_correction_main()
    with st.spinner("Semantic Chunking based on words..."):
        from core import step3_semantic_chunking
        step3_semantic_chunking.split_by_semantic_chunking()
    with st.spinner("Summarizing and translating..."):
        step4_1_summarize.get_summary()
        if load_key("pause_before_translate"):
            st.warning("⚠️ PAUSE_BEFORE_TRANSLATE is enabled. Please edit `output/log/terminology.json` in the sidebar or file explorer, then click 'Continue Translation' below.")
            st.session_state.setdefault('translation_paused', True)
            if st.session_state.get('translation_paused', False):
                if st.button("Continue Translation", key="continue_translate"):
                    st.session_state['translation_paused'] = False
                    st.rerun()
                st.stop()
        step4_2_translate_all.translate_all()
    with st.spinner("Processing and aligning subtitles..."): 
        step6_generate_final_timeline.align_timestamp_main()
    
    st.success("Text processing complete! 🎉")
    st.balloons()

def subtitle_customization_section():
    if os.path.exists("output/trans.srt"):
        st.header("Subtitle Style Preview")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                target_size = st.slider("Target Language Size", 5, 40, load_key("subtitle.target_font_size"))
            with col2:
                source_size = st.slider("Source Language Size", 5, 40, load_key("subtitle.source_font_size"))
            
            if st.button("Generate Preview Frame", key="generate_preview"):
                if load_key("resolution") == "0x0":
                    st.error("❌ Cannot preview: Please turn on 'Burn-in Subtitles' in the sidebar first!")
                    st.toast("⚠️ Enable 'Burn-in Subtitles' first!", icon="⚠️")
                else:
                    from core.config_utils import update_key
                    update_key("subtitle.target_font_size", target_size)
                    update_key("subtitle.source_font_size", source_size)
                    st.session_state.preview_generated = True
                    from core.step7_merge_sub_to_vid import generate_preview_frame
                    with st.spinner("Finding longest sentence and generating preview..."):
                        preview_path = generate_preview_frame(target_size, source_size)
                        if preview_path and os.path.exists(preview_path):
                            try:
                                st.image(preview_path, use_container_width=True)
                            except TypeError:
                                st.image(preview_path, use_column_width=True)
                        else:
                            st.warning("Failed to generate preview.")
            
            if os.path.exists("output/trans.srt"):
                # Ensure the user must preview the current slider values before merging
                current_target = load_key("subtitle.target_font_size")
                current_source = load_key("subtitle.source_font_size")
                
                is_preview_valid = (
                    target_size == current_target and 
                    source_size == current_source and 
                    st.session_state.get('preview_generated', False)
                )
                
                button_label = "Re-merge Subtitles with New Style" if os.path.exists(SUB_VIDEO) else "Burn Subtitles to Video"
                
                if st.button(button_label, key="remerge_subtitles"):
                    if not is_preview_valid:
                        st.error("❌ Please click 'Generate Preview Frame' first to preview your changes before burning!")
                        st.toast("⚠️ Generate preview first!", icon="⚠️")
                    elif load_key("resolution") == "0x0":
                        st.error("❌ Cannot burn subtitles: Please turn on 'Burn-in Subtitles' in the sidebar first!")
                        st.toast("⚠️ Enable 'Burn-in Subtitles' first!", icon="⚠️")
                    else:
                        from core.config_utils import update_key
                        update_key("subtitle.target_font_size", target_size)
                        update_key("subtitle.source_font_size", source_size)
                        from core import step7_merge_sub_to_vid
                        with st.spinner("Burning subtitles to video..."):
                            step7_merge_sub_to_vid.merge_subtitles_to_video()
                        st.success("Subtitles burned successfully! 🎉")
                        st.rerun()
                
                if os.path.exists(SUB_VIDEO):
                    if load_key("resolution") != "0x0":
                        st.video(SUB_VIDEO)

def audio_processing_section():
    st.header("Dubbing")
    with st.container(border=True):
        st.markdown("""
        <p style='font-size: 20px;'>
        This stage includes the following steps:
        <p style='font-size: 20px;'>
            1. Generate audio tasks and chunks<br>
            2. Extract reference audio<br>
            3. Generate and merge audio files<br>
            4. Merge final audio into video
        """, unsafe_allow_html=True)
        if not os.path.exists(DUB_VIDEO):
            if st.button("Start Audio Processing", key="audio_processing_button"):
                process_audio()
                st.rerun()
        else:
            st.success("Audio processing is complete! You can check the audio files in the `output` folder.")
            if load_key("resolution") != "0x0": 
                st.video(DUB_VIDEO) 
            if st.button("Delete dubbing files", key="delete_dubbing_files"):
                delete_dubbing_files()
                st.rerun()
            if st.button("Archive to 'history'", key="cleanup_in_audio_processing"):
                cleanup()
                st.rerun()

def process_audio():
    with st.spinner("Generate audio tasks"): 
        step8_1_gen_audio_task.gen_audio_task_main()
        step8_2_gen_dub_chunks.gen_dub_chunks()
    with st.spinner("Extract refer audio"):
        step9_extract_refer_audio.extract_refer_audio_main()
    with st.spinner("Generate all audio"):
        step10_gen_audio.gen_audio()
    with st.spinner("Merge full audio"):
        step11_merge_full_audio.merge_full_audio()
    with st.spinner("Merge dubbing to the video"):
        step12_merge_dub_to_vid.merge_video_audio()
    
    st.success("Audio processing complete! 🎇")
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
