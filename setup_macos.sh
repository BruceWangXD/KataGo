#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ "$(uname -s)" != Darwin ]; then
  echo '此脚本用于 macOS；云环境请使用 bash install.sh。' >&2
  exit 1
fi
brew_bin="$(command -v brew || true)"
if [ -z "$brew_bin" ]; then
  for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    if [ -x "$candidate" ]; then brew_bin="$candidate"; break; fi
  done
fi
if [ -z "$brew_bin" ]; then
  echo '请先从 https://brew.sh 安装 Homebrew，然后重新运行 bash setup_macos.sh。' >&2
  exit 1
fi
if ! "$brew_bin" list --versions katago >/dev/null 2>&1; then
  "$brew_bin" install katago
fi
katago_bin="$("$brew_bin" --prefix)/bin/katago"
if [ ! -x "$katago_bin" ]; then
  echo 'KataGo 安装未生成可执行文件，请运行 brew reinstall katago 后重试。' >&2
  exit 1
fi
"$katago_bin" version
echo 'KataGo 引擎已就绪，模型已附带。运行 python3 app.py 开始对弈。'
