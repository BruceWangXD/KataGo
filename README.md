# 弈 · Python + KataGo 围棋网页

原生 Canvas 棋盘，Python 标准库 HTTP 后端，通过官方 KataGo GTP 子进程对弈。无需 Python 第三方库。支持 9/13/19 路、选择黑白、提子、停一手、AI 认输、逐手悔棋。非法落子与劫由 KataGo 判断。中国规则、贴目 7.5，双方停一手后结束（点目支持 AI 预判死活及手动修正）。

## 当前云环境启动

```bash
cd /workspace/KataGo
./run.sh
```

启动成功后，打开终端输出的实际网址。默认使用 `http://127.0.0.1:8000`；如果端口被占用，会自动尝试 8001 到 8010。也可用 `PORT=8080 python3 app.py` 指定端口，指定端口被占用时会给出提示，不会自动改用其他端口。默认使用源码构建的 CPU 引擎和随本项目附带的小型官方预训练测试模型，适合功能演示；模型较旧，棋力不代表最新 KataGo。服务仅监听本机，云环境外访问需部署端口转发。

「停一手」表示这回合不落子，将回合交给对手；双方连续停一手会结束对局。「让 AI 落子」在 AI 回合继续其思考和落子，主要用于悔棋后恢复对弈。人落子后 AI 自动落子。点击一次「撤回一步」只撤回最后一手（例如白棋），再点一次撤回前一手（黑棋）。悔棋后 AI 暂停重下，可继续悔棋，或点击「让 AI 落子」。AI 思考期间按钮暂时禁用。每个浏览器页面独立对局，最多 1 个活动对局；闲置 15 分钟自动清理，刷新页面会失去当前对局标识，可重启服务清理。

## macOS 首次安装

模型已经包含在仓库中，但 KataGo 引擎需要针对你的电脑单独安装。Mac（Apple Silicon 和 Intel）执行：

```bash
git pull origin main
bash setup_macos.sh
python3 app.py
```

安装脚本通过 Homebrew 安装官方 KataGo；如果没有 Homebrew，请先按照 https://brew.sh 的说明安装，再重试。程序会自动查找 Apple Silicon 的 `/opt/homebrew/bin/katago` 和 Intel 的 `/usr/local/bin/katago`，无需手动设置 PATH。也可运行 `bash run.sh`，在 Mac 上缺少引擎时会先运行安装脚本。安装需要联网，只在首次安装时执行。

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

## 免费公网试用：Mac + Cloudflare 临时隧道

```bash
git pull origin main
bash setup_macos.sh
brew install cloudflared
python3 share.py
```

启动时设置至少 8 个字符的访客密码。找到隧道日志里的 `https://……trycloudflare.com` 地址，将地址、用户名 `go` 和密码发给朋友。浏览器会弹出登录框，无需访客安装软件。此模式由系统自动分配空闲端口，并将实际端口传给隧道，无需处理 8765 端口冲突。

不需要域名或 Cloudflare 账户，临时网址重启后会变化。Mac 必须保持开机、联网且不要休眠；按 Control+C 停止分享。中国内地访问可能慢或不可达，应先让朋友实测，不能保证线路可用。Cloudflare Quick Tunnel 有并发和使用限制，适用于试用，不适用于正式运营。若本机已有 Cloudflare tunnel 配置导致临时隧道失败，请参考官方文档：https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/

访客可不限次数点击「开始新对局」重开自己的棋局，或点击「结束对局」立即释放引擎。刷新同一标签页后仍可重开或结束旧局。试用版最多同时一局，连续 15 分钟没有操作会自动释放引擎。分享模式全站需要密码，本地 `python3 app.py` 模式默认不要求密码。密码仅在进程环境中传递，不保存到仓库。网页登录使用同一个访客账户，请只分享给可信的朋友。

## 点目结算

点击「点目结算」暂停落子并显示所有连通空地区域：只接触黑棋的空地标黑点，只接触白棋的空地标白点，同时接触双方或不接触棋子的空地标红点（中立）。点击任一空点会修改整块连通空地，按黑方 → 白方 → 中立循环，立即刷新分数、胜方与目差。

沿用中国规则：黑分 = 黑棋子数 + 黑方空地点数；白分 = 白棋子数 + 白方空地点数 + 7.5 贴目。中立空地不计分。界面同时显示双方空地点数、棋子数和最终总分。棋子死活由 KataGo 预判并支持人工修正；空地仍按移除死子后的边界判定，复杂双活或未完成的棋局可能需要修正。点目不改变棋盘或棋谱。点击「继续对弈」退出点目模式；落子或悔棋会清除此前归属修正。

### 棋子死活与归属

点目会调用 KataGo 的 `final_status_list dead` 预判死子，在所有棋子上显示黑点或白点。棋子标记归自己的颜色表示活子，归对方表示死子。点击任一棋子，整块同色连通棋子在黑方／白方之间切换。结算在副本中移除死子后重新划分空地，按中国规则重新计算子空总分、白方 7.5 贴目和目差，原棋盘与棋谱不变。修改棋块死活会重置空地修正。自动死活判定仍是 AI 估计，未收官局面和弱模型可能判断有误，可人工纠正。
