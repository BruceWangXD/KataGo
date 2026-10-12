#!/usr/bin/env bash
set -euo pipefail
cd /workspace
if [ ! -x /workspace/katago-tools/bin/cmake ]; then
  python -m venv /workspace/katago-tools
  /workspace/katago-tools/bin/pip install cmake==4.4.4
fi
if [ ! -d /workspace/katago-engine ]; then
  git clone https://github.com/lightvector/KataGo.git /workspace/katago-engine
  git -C /workspace/katago-engine checkout d91ea855110dae533f0aada947b2b7d78cc8a4e1
fi
if [ ! -d /workspace/eigen ]; then
  git clone https://github.com/eigenteam/eigen-git-mirror.git /workspace/eigen
  git -C /workspace/eigen checkout 36b95962756c1fce8e29b1f8bc45967f30773c00
fi
/workspace/katago-tools/bin/cmake -S /workspace/katago-engine/cpp -B /workspace/katago-build -DUSE_BACKEND=EIGEN -DEIGEN3_INCLUDE_DIRS=/workspace/eigen -DCMAKE_BUILD_TYPE=Release
/workspace/katago-tools/bin/cmake --build /workspace/katago-build -j 4
cd /workspace/KataGo
python -m unittest -v
