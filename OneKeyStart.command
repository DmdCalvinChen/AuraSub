#!/bin/bash
# 进入当前脚本所在目录
cd "$(dirname "$0")"

# 寻找并加载 Conda 环境配置
if [ -f "$HOME/miniforge3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniforge3/etc/profile.d/conda.sh"
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
elif [ -f "/opt/homebrew/Caskroom/miniforge/base/etc/profile.d/conda.sh" ]; then
    source "/opt/homebrew/Caskroom/miniforge/base/etc/profile.d/conda.sh"
fi

# 激活 macOS 专属环境 aurasub_mac（或 fallback 到 aurasub）
if conda info --envs | grep -q "aurasub_mac"; then
    conda activate aurasub_mac
elif conda info --envs | grep -q "aurasub"; then
    conda activate aurasub
fi

echo "🚀 正在启动 AuraSub Mac 硬件加速版..."
python -m streamlit run st.py
