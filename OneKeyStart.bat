@echo off
chcp 65001 >nul
echo 🚀 正在启动 AuraSub...

:: 尝试激活 conda 环境
call conda activate aurasub 2>nul
if %errorlevel% neq 0 (
    call conda activate aurasub_mac 2>nul
)

python -m streamlit run st.py
pause
