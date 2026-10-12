# 弈 · Python + KataGo 围棋网页

原生 Canvas 棋盘，Python 标准库 HTTP 后端，通过官方 KataGo GTP 子进程对弈。无需 Python 第三方库。支持 9/13/19 路、选择黑白、提子、停一手、AI 认输、逐手悔棋。非法落子与劫由 KataGo 判断。中国规则、贴目 7.5，双方停一手后结束（本版本不包含死子确认和最终数目界面）。

## 当前云环境启动

```bash
cd /workspace/KataGo
./run.sh
```

在本机浏览器访问 `http://127.0.0.1:8000`。默认使用源码构建的 CPU 引擎和随本项目附带的小型官方预训练测试模型，适合功能演示；模型较旧，棋力不代表最新 KataGo。服务仅监听本机，云环境外访问需部署端口转发。

「停一手」表示这回合不落子，将回合交给对手；双方连续停一手会结束对局。「让 AI 落子」在 AI 回合继续其思考和落子，主要用于悔棋后恢复对弈。人落子后 AI 自动落子。点击一次「撤回一步」只撤回最后一手（例如白棋），再点一次撤回前一手（黑棋）。悔棋后 AI 暂停重下，可继续悔棋，或点击「让 AI 落子」。AI 思考期间按钮暂时禁用。每个浏览器页面独立对局，最多 8 个活动对局；刷新页面会失去当前对局标识，可重启服务清理。

## 在其他机器连接自己的 KataGo

模型已随代码附带，无需设置 `KATAGO_MODEL`；直接 `python app.py` 即可读取它。仍需安装适合机器的 KataGo 引擎（https://github.com/lightvector/KataGo），将可执行文件放到项目的 `bin/katago`（Windows 为 `bin/katago.exe`），或加入 PATH。当前云环境已编译好引擎，会自动识别。

若希望换用其他引擎或更强的官方模型：

```bash
KATAGO_BIN=/path/to/katago KATAGO_MODEL=/path/to/model.bin.gz python app.py
```

可用 `KATAGO_CONFIG` 指定 GTP 配置，`PORT` 指定端口。默认 `gtp.cfg` 使用两个搜索线程、100 visits；增大 maxVisits 可以提高棋力，但会延长思考时间。错误会显示在网页中，引擎日志为 `katago.log` 和 `katago-logs/`。

```bash
python -m unittest -v
```

这是本地开发应用，尚未加入账户、持久化、多用户资源管理或公网部署认证。
