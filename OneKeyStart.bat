@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ====================================================
echo           🎬  AuraSub 视频字幕与配音工具  🎬         
echo ====================================================
echo.

:: 1. 尝试直接调用 conda activate
set "ENV_FOUND="
call conda activate aurasub 2>nul
if %errorlevel% equ 0 (
    set "ENV_FOUND=aurasub"
    goto :START_APP
)

call conda activate aurasub_mac 2>nul
if %errorlevel% equ 0 (
    set "ENV_FOUND=aurasub_mac"
    goto :START_APP
)

:: 2. 如果直接激活失败，尝试加载常见 Conda 路径
for %%P in (
    "%USERPROFILE%\miniconda3\Scripts\activate.bat"
    "%USERPROFILE%\anaconda3\Scripts\activate.bat"
    "%USERPROFILE%\miniforge3\Scripts\activate.bat"
    "C:\ProgramData\miniconda3\Scripts\activate.bat"
    "C:\ProgramData\anaconda3\Scripts\activate.bat"
    "C:\ProgramData\miniforge3\Scripts\activate.bat"
    "C:\miniconda3\Scripts\activate.bat"
    "C:\anaconda3\Scripts\activate.bat"
) do (
    if exist %%P (
        call %%P aurasub 2>nul
        if not errorlevel 1 (
            set "ENV_FOUND=aurasub"
            goto :START_APP
        )
        call %%P aurasub_mac 2>nul
        if not errorlevel 1 (
            set "ENV_FOUND=aurasub_mac"
            goto :START_APP
        )
    )
)

:: 3. 若均未找到环境，给出清晰指引
echo.
echo [31m[错误] 未检测到名为 'aurasub' 的 Conda 虚拟环境！[0m
echo.
echo 请先按照 README 指引在 Anaconda / Miniconda Prompt 中执行初始化：
echo   1. conda create -n aurasub python=3.10.0 -y
echo   2. conda activate aurasub
echo   3. python install.py
echo.
pause
exit /b 1

:START_APP
echo 🚀 已激活虚拟环境 [%ENV_FOUND%]，正在启动 AuraSub WebUI...
python -m streamlit run st.py
pause
