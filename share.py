"""Start a password protected local app and a free Cloudflare Quick Tunnel."""
import getpass
import os
import shutil
import subprocess
import sys
import threading

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
    from app import Handler, ThreadingHTTPServer, GAMES, GAMES_LOCK, idle_cleanup
    # Bind once to a port chosen by the OS, then share exactly that server.
    os.environ['GO_PASSWORD'] = password
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    url = 'http://127.0.0.1:' + str(server.server_address[1])
    stop = threading.Event()
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    cleaner = threading.Thread(target=idle_cleanup, args=(stop,), daemon=True)
    worker.start()
    cleaner.start()
    proxy = None
    try:
        print('本地服务：' + url, flush=True)
        print('访客用户名：go；密码为你刚设置的密码。将下面日志中的 https://…trycloudflare.com 地址发给朋友。', flush=True)
        print('保持此终端和 Mac 运行；Control+C 停止分享。', flush=True)
        proxy = subprocess.Popen([tunnel, 'tunnel', '--url', url, '--protocol', 'http2'])
        return proxy.wait()
    except KeyboardInterrupt: return 0
    finally:
        if proxy is not None and proxy.poll() is None:
            proxy.terminate()
            try: proxy.wait(timeout=5)
            except subprocess.TimeoutExpired: proxy.kill(); proxy.wait()
        stop.set()
        server.shutdown()
        server.server_close()
        worker.join()
        with GAMES_LOCK:
            for game in GAMES.values(): game.engine.close()
            GAMES.clear()

if __name__ == '__main__': sys.exit(main())
