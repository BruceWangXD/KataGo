"""Start a password protected local app and a free Cloudflare Quick Tunnel."""
import base64
import getpass
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

def main():
    tunnel = shutil.which('cloudflared')
    if not tunnel:
        for candidate in ('/opt/homebrew/bin/cloudflared', '/usr/local/bin/cloudflared'):
            if os.access(candidate, os.X_OK): tunnel = candidate; break
    if not tunnel:
        print('请先执行 brew install cloudflared，再运行 python3 share.py。')
        return 1
    from app import find_katago
    try: find_katago()
    except ValueError as error:
        print(error); return 1
    password = getpass.getpass('设置访客密码（至少 8 个字符，输入不显示）：')
    if len(password) < 8:
        print('密码太短，请重新运行。'); return 1
    env = os.environ.copy()
    env.update(GO_PASSWORD=password, PORT='8765')
    root = Path(__file__).resolve().parent
    app = subprocess.Popen([sys.executable, '-u', str(root / 'app.py')], env=env, cwd=str(root))
    proxy = None
    try:
        ready = False
        for _ in range(50):
            if app.poll() is not None: return 1
            try:
                request = urllib.request.Request('http://127.0.0.1:8765/', headers={'Authorization': 'Basic ' + base64.b64encode(('go:' + password).encode()).decode()})
                with urllib.request.urlopen(request, timeout=1) as response:
                    ready = response.status == 200
                if ready: break
            except OSError: time.sleep(0.1)
        if not ready:
            print('本地服务未就绪，未开启隧道。'); return 1
        print('访客用户名：go；密码为你刚设置的密码。将下面日志中的 https://…trycloudflare.com 地址发给朋友。', flush=True)
        print('保持此终端和 Mac 运行；Control+C 停止分享。', flush=True)
        proxy = subprocess.Popen([tunnel, 'tunnel', '--url', 'http://127.0.0.1:8765', '--protocol', 'http2'])
        while proxy.poll() is None and app.poll() is None: time.sleep(0.5)
        return 1
    except KeyboardInterrupt: return 0
    finally:
        for process in (proxy, app):
            if process is not None and process.poll() is None:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill(); process.wait()

if __name__ == '__main__': sys.exit(main())
