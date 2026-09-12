import streamlit as st
import os, sys, shutil
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config_utils import load_key
from core.step1_ytdlp import (
    download_video_ytdlp,
    find_video_files,
    save_uploaded_cookie,
    delete_cookie_file,
    check_cookie_status,
    check_and_update_ytdlp,
    find_deno_path
)
from time import sleep
import re
import subprocess

def download_video_section():
    st.header("Download or Upload Video")
    with st.container(border=True):
        try:
            video_file = find_video_files()
            if st.session_state.get('download_success_msg'):
                st.success(st.session_state.pop('download_success_msg'))

            st.video(video_file)
            st.info(f"🎬 Current Video: `{os.path.basename(video_file)}`")
            if st.button("Delete and Reselect", key="delete_video_button", use_container_width=True):
                os.remove(video_file)
                if os.path.exists("output"):
                    shutil.rmtree("output")
                sleep(1)
                st.rerun()
            return True
        except Exception:
            # Display any cached error or feedback messages
            if 'download_error_msg' in st.session_state:
                st.error(st.session_state.pop('download_error_msg'))
            if 'cookie_msg' in st.session_state:
                st.toast(st.session_state.pop('cookie_msg'))

            # 1. Cookie & Engine Status Expander
            cookie_info = check_cookie_status()
            deno_path = find_deno_path()

            with st.expander("🍪 Cookie & Download Engine Settings", expanded=not cookie_info['exists']):
                col_c1, col_c2 = st.columns([2, 1])
                with col_c1:
                    if cookie_info['exists']:
                        st.markdown(f"**Cookie Status:** 🟢 `Active` (`{cookie_info['filename']}` - {cookie_info['size_kb']} KB, updated: {cookie_info['mtime']})")
                    else:
                        st.markdown("**Cookie Status:** ⚪ `Not Loaded` (Public videos can download directly; upload Cookie.txt if encountering 403 or bot check)")
                with col_c2:
                    if cookie_info['exists']:
                        if st.button("🗑️ Clear Cookie", key="clear_cookie_btn", use_container_width=True):
                            delete_cookie_file()
                            st.session_state['last_uploaded_cookie'] = None
                            st.session_state['cookie_msg'] = "Cookie has been cleared."
                            st.rerun()

                uploaded_cookie = st.file_uploader(
                    "Upload Netscape format Cookie file (.txt, any filename)",
                    type=["txt"],
                    key="cookie_uploader",
                    help="Export your cookies (e.g. via 'Get cookies.txt LOCALLY' extension) and upload here."
                )
                if uploaded_cookie is not None:
                    cookie_id = f"{uploaded_cookie.name}_{uploaded_cookie.size}"
                    if st.session_state.get('last_uploaded_cookie') != cookie_id:
                        try:
                            save_uploaded_cookie(uploaded_cookie.getvalue())
                            st.session_state['last_uploaded_cookie'] = cookie_id
                            st.session_state['cookie_msg'] = "✅ Cookie uploaded and saved successfully!"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to save cookie: {e}")

                col_e1, col_e2 = st.columns([2, 1])
                with col_e1:
                    import yt_dlp.version
                    deno_status = "⚡ Deno JS Acceleration: Enabled" if deno_path else "⚪ Deno: Not detected"
                    st.caption(f"yt-dlp Engine: `v{yt_dlp.version.__version__}` | {deno_status}")
                with col_e2:
                    if st.button("🔄 Check yt-dlp Update", key="update_ytdlp_btn", use_container_width=True):
                        with st.spinner("Checking for updates..."):
                            res = check_and_update_ytdlp(force=False)
                            if res['updated']:
                                st.success(res['message'])
                            else:
                                st.info(res['message'])
                            sleep(1)
                            st.rerun()

            st.markdown("---")

            # 2. Download from Link
            st.subheader("📥 Download from URL")
            col1, col2 = st.columns([3, 1])
            with col1:
                url = st.text_input("Enter video link (YouTube, Bilibili, etc.):", placeholder="https://www.youtube.com/watch?v=...")
            with col2:
                res_dict = {
                    "1080p (FHD) [Default]": "1080",
                    "Best Quality (4K/2K/Auto)": "best",
                    "4K (2160p)": "2160",
                    "2K (1440p)": "1440",
                    "720p (HD)": "720",
                    "480p (SD)": "480",
                }
                res_options = list(res_dict.keys())
                target_res = load_key("ytb_resolution")
                default_idx = 0
                for idx, k in enumerate(res_dict.values()):
                    if str(k) == str(target_res):
                        default_idx = idx
                        break
                res_display = st.selectbox("Resolution", options=res_options, index=default_idx)
                res = res_dict[res_display]

            if st.button("🚀 Download Video", key="download_button", use_container_width=True):
                if not url or not url.strip():
                    st.warning("Please enter a valid video URL.")
                else:
                    with st.spinner("Downloading video... (Parsing streams & fetching media)"):
                        try:
                            download_video_ytdlp(url, resolution=res)
                            st.session_state['download_success_msg'] = "🎉 Video downloaded successfully!"
                            st.rerun()
                        except Exception as e:
                            st.session_state['download_error_msg'] = str(e)
                            st.rerun()

            st.markdown("---")

            # 3. Direct File Upload
            st.subheader("📁 Or Upload Local File")
            uploaded_file = st.file_uploader(
                "Select local video or audio file",
                type=load_key("allowed_video_formats") + load_key("allowed_audio_formats"),
                key="local_file_uploader"
            )
            if uploaded_file:
                if os.path.exists("output"):
                    shutil.rmtree("output")
                os.makedirs("output", exist_ok=True)
                
                raw_name = uploaded_file.name.replace(' ', '_')
                name, ext = os.path.splitext(raw_name)
                clean_name = re.sub(r'[^\w\-_\.]', '', name) + ext.lower()
                
                with open(os.path.join("output", clean_name), "wb") as f:
                    f.write(uploaded_file.getbuffer())

                if clean_name.split('.')[-1] in load_key("allowed_audio_formats"):
                    with st.spinner("Converting audio to video container..."):
                        convert_audio_to_video(os.path.join("output", clean_name))
                st.session_state['download_success_msg'] = "🎉 File uploaded successfully!"
                st.rerun()
            else:
                return False

def convert_audio_to_video(audio_file: str) -> str:
    output_video = 'output/black_screen.mp4'
    if not os.path.exists(output_video):
        print("🎵➡️🎬 Converting audio to video with FFmpeg ......")
        ffmpeg_cmd = ['ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=640x360', '-i', audio_file, '-shortest', '-c:v', 'libx264', '-c:a', 'aac', '-pix_fmt', 'yuv420p', output_video]
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        print(f"🎵➡️🎬 Converted <{audio_file}> to <{output_video}> with FFmpeg\n")
        # delete audio file
        os.remove(audio_file)
    return output_video
