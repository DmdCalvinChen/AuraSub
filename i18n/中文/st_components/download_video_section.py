import streamlit as st
import os, sys, shutil
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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
    st.header("下载或上传视频")
    with st.container(border=True):
        try:
            video_file = find_video_files()
            if st.session_state.get('download_success_msg'):
                st.success(st.session_state.pop('download_success_msg'))

            st.video(video_file)
            st.info(f"🎬 当前视频文件: `{os.path.basename(video_file)}`")
            if st.button("删除并重新选择", key="delete_video_button", use_container_width=True):
                os.remove(video_file)
                if os.path.exists("output"):
                    shutil.rmtree("output")
                sleep(1)
                st.rerun()
            return True
        except Exception:
            if 'download_error_msg' in st.session_state:
                st.error(st.session_state.pop('download_error_msg'))
            if 'cookie_msg' in st.session_state:
                st.toast(st.session_state.pop('cookie_msg'))

            # 1. Cookie 与引擎设置
            cookie_info = check_cookie_status()
            deno_path = find_deno_path()

            with st.expander("🍪 Cookie 凭证与下载引擎设置", expanded=not cookie_info['exists']):
                col_c1, col_c2 = st.columns([2, 1])
                with col_c1:
                    if cookie_info['exists']:
                        st.markdown(f"**Cookie 状态:** 🟢 `已加载生效` (`{cookie_info['filename']}` - {cookie_info['size_kb']} KB, 更新时间: {cookie_info['mtime']})")
                    else:
                        st.markdown("**Cookie 状态:** ⚪ `未配置` (公开视频可直接下载；若遇 403 / 机器人验证 / 会员限制建议上传 Cookie.txt)")
                with col_c2:
                    if cookie_info['exists']:
                        if st.button("🗑️ 清除 Cookie", key="clear_cookie_btn", use_container_width=True):
                            delete_cookie_file()
                            st.session_state['cookie_msg'] = "Cookie 凭证已清除。"
                            st.rerun()

                uploaded_cookie = st.file_uploader(
                    "上传 Netscape 格式 Cookie 文件 (.txt，不限命名)",
                    type=["txt"],
                    key="cookie_uploader",
                    help="使用浏览器扩展（如 Get cookies.txt LOCALLY）导出 YouTube 的 cookie.txt 并上传即可。"
                )
                if uploaded_cookie:
                    try:
                        save_uploaded_cookie(uploaded_cookie.getvalue())
                        st.session_state['cookie_msg'] = "✅ Cookie 凭证上传成功并已生效！"
                        st.rerun()
                    except Exception as e:
                        st.error(f"保存 Cookie 失败: {e}")

                col_e1, col_e2 = st.columns([2, 1])
                with col_e1:
                    import yt_dlp.version
                    deno_status = "⚡ Deno JS 动态解密: 已开启" if deno_path else "⚪ Deno: 未检测到"
                    st.caption(f"yt-dlp 引擎版本: `v{yt_dlp.version.__version__}` | {deno_status}")
                with col_e2:
                    if st.button("🔄 检查 yt-dlp 更新", key="update_ytdlp_btn", use_container_width=True):
                        with st.spinner("正在检查官方最新版本..."):
                            res = check_and_update_ytdlp(force=False)
                            if res['updated']:
                                st.success(res['message'])
                            else:
                                st.info(res['message'])
                            sleep(1)
                            st.rerun()

            st.markdown("---")

            # 2. 链接下载
            st.subheader("📥 在线链接下载")
            col1, col2 = st.columns([3, 1])
            with col1:
                url = st.text_input("输入视频链接 (支持 YouTube, Bilibili 等):", placeholder="https://www.youtube.com/watch?v=...")
            with col2:
                res_dict = {
                    "1080p (超清) [默认]": "1080",
                    "最佳画质 (自动最高 4K/2K)": "best",
                    "4K (2160p)": "2160",
                    "2K (1440p)": "1440",
                    "720p (高清)": "720",
                    "480p (标清)": "480",
                }
                res_options = list(res_dict.keys())
                target_res = load_key("ytb_resolution")
                default_idx = 0
                for idx, k in enumerate(res_dict.values()):
                    if str(k) == str(target_res):
                        default_idx = idx
                        break
                res_display = st.selectbox("下载画质", options=res_options, index=default_idx)
                res = res_dict[res_display]

            if st.button("🚀 下载视频", key="download_button", use_container_width=True):
                if not url or not url.strip():
                    st.warning("请输入有效的视频链接！")
                else:
                    with st.spinner("正在下载视频（正在解析视频流与音频流）..."):
                        try:
                            download_video_ytdlp(url, resolution=res)
                            st.session_state['download_success_msg'] = "🎉 视频下载成功！"
                            st.rerun()
                        except Exception as e:
                            st.session_state['download_error_msg'] = str(e)
                            st.rerun()

            st.markdown("---")

            # 3. 本地上传
            st.subheader("📁 或上传本地音视频文件")
            uploaded_file = st.file_uploader(
                "选择本地音视频文件",
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
                    with st.spinner("正在使用 FFmpeg 将音频转换为视频容器..."):
                        convert_audio_to_video(os.path.join("output", clean_name))
                st.session_state['download_success_msg'] = "🎉 文件上传成功！"
                st.rerun()
            else:
                return False

def convert_audio_to_video(audio_file: str) -> str:
    output_video = 'output/black_screen.mp4'
    if not os.path.exists(output_video):
        print("🎵➡️🎬 正在使用FFmpeg将音频转换为视频......")
        ffmpeg_cmd = ['ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=640x360', '-i', audio_file, '-shortest', '-c:v', 'libx264', '-c:a', 'aac', '-pix_fmt', 'yuv420p', output_video]
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        print(f"🎵➡️🎬 已将 <{audio_file}> 转换为 <{output_video}>\n")
        # 删除音频文件
        os.remove(audio_file)
    return output_video
