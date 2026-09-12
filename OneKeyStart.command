#!/bin/bash
# 进入当前脚本所在目录
cd "$(dirname "$0")"

# 1. 探测并初始化 Conda
CONDA_INITIALIZED=false

for conda_sh in \
    "$HOME/miniforge3/etc/profile.d/conda.sh" \
    "$HOME/miniconda3/etc/profile.d/conda.sh" \
    "$HOME/anaconda3/etc/profile.d/conda.sh" \
    "/opt/homebrew/Caskroom/miniforge/base/etc/profile.d/conda.sh" \
    "/opt/homebrew/anaconda3/etc/profile.d/conda.sh" \
    "/opt/homebrew/miniconda3/etc/profile.d/conda.sh" \
    "/usr/local/miniconda3/etc/profile.d/conda.sh" \
    "/usr/local/anaconda3/etc/profile.d/conda.sh"
do
    if [ -f "$conda_sh" ]; then
        source "$conda_sh"
        CONDA_INITIALIZED=true
        break
    fi
done

# 若未命中已知路径，尝试通过已有的 shell hook 初始化
if [ "$CONDA_INITIALIZED" = false ] && command -v conda >/dev/null 2>&1; then
    eval "$(conda shell.bash hook 2>/dev/null)"
    CONDA_INITIALIZED=true
fi

# 检查 Conda 是否可用
if ! command -v conda >/dev/null 2>&1; then
    echo ""
    echo "❌ 未检测到 Conda 环境管理器！"
    echo "💡 请先安装 Miniforge 或 Miniconda，然后重新运行本脚本。"
    echo "   推荐下载地址: https://github.com/conda-forge/miniforge"
    echo ""
    read -n 1 -s -r -p "按任意键退出..."
    echo ""
    exit 1
fi

# 2. 检查并激活虚拟环境
TARGET_ENV=""
if conda info --envs | grep -E "(^|[[:space:]])aurasub([[:space:]]|$)" >/dev/null 2>&1; then
    TARGET_ENV="aurasub"
fi

if [ -z "$TARGET_ENV" ]; then
    echo ""
    echo "⚠️ 未检测到虚拟环境 'aurasub'！"
    echo ""
    echo "👉 请先在终端中执行以下命令完成初始化："
    echo "   1. conda create -n aurasub python=3.10.0 -y"
    echo "   2. conda activate aurasub"
    echo "   3. python install.py"
    echo ""
    read -n 1 -s -r -p "按任意键退出..."
    echo ""
    exit 1
fi

echo "🚀 正在激活虚拟环境 [$TARGET_ENV] 并启动 AuraSub..."
conda activate "$TARGET_ENV"
python -m streamlit run st.py
