"""Local Go web app. Run: python app.py. Requires KataGo + a neural model."""
import base64, errno, hmac, json, os, shutil, signal, subprocess, sys, threading, time, uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent
COLS = 'ABCDEFGHJKLMNOPQRST'

def find_katago():
    configured = os.environ.get('KATAGO_BIN')
    candidates = [configured] if configured else [
        str(ROOT / 'bin' / ('katago.exe' if os.name == 'nt' else 'katago')),
        '/workspace/katago-build/katago',
        'katago',
    ]
    if not configured and sys.platform == 'darwin':
        candidates.extend(['/opt/homebrew/bin/katago', '/usr/local/bin/katago'])
    for candidate in candidates:
        executable = shutil.which(candidate)
        if executable:
            return executable
    if configured:
        raise ValueError('KATAGO_BIN 指向的引擎不存在或不可执行，请检查路径：' + configured)
    if sys.platform == 'darwin':
        raise ValueError('尚未安装 KataGo 引擎。请在项目目录运行 bash setup_macos.sh，安装后重启 python3 app.py。模型已附带，无需另行下载。')
    raise ValueError('找不到 KataGo 引擎。请安装 KataGo 并加入 PATH，或设置 KATAGO_BIN 为可执行文件路径。')

class GTP:
    def __init__(self, size):
        binary = find_katago()
        model = os.environ.get('KATAGO_MODEL') or str(ROOT / 'models' / 'g170-b6c96-s175395328-d26788732.bin.gz')
        config = os.environ.get('KATAGO_CONFIG', str(ROOT / 'gtp.cfg'))
        if not model or not Path(model).is_file():
            raise ValueError('请设置 KATAGO_MODEL 为 KataGo 神经网络模型文件路径。')
        self.log = open(ROOT / 'katago.log', 'a')
        try:
            self.p = subprocess.Popen([binary, 'gtp', '-model', model, '-config', config], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log, text=True, bufsize=1)
        except Exception:
            self.log.close()
            raise
        try:
            self.command(f'boardsize {size}')
            self.command('clear_board')
            self.command('komi 7.5')
        except Exception:
            self.close()
            raise
    def command(self, text):
        timer = threading.Timer(120, self.p.kill)
        timer.start()
        try:
            return self._command(text)
        finally:
            timer.cancel()
    def _command(self, text):
        self.p.stdin.write(text + '\n'); self.p.stdin.flush()
        lines = []
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError('KataGo 已退出，请查看 katago.log。')
            if not line.strip() and lines: break
            if line.strip(): lines.append(line.strip())
        response = '\n'.join(lines)
        if not response.startswith('='): raise ValueError(response.lstrip('? '))
        return response[1:].strip()
    def close(self):
        self.log.close()
        if self.p.poll() is None:
            self.p.terminate()
            try: self.p.wait(timeout=3)
            except subprocess.TimeoutExpired: self.p.kill(); self.p.wait()

class Game:
    def __init__(self, size, human, engine_factory=GTP):
        self.size, self.human = size, human
        self.engine = engine_factory(size)
        self.moves, self.snapshots, self.board = [], [], [[0]*size for _ in range(size)]
        self.lock = threading.Lock()
        self.last_used = time.monotonic()
    def state(self):
        over = bool(self.moves and (self.moves[-1]['vertex']=='resign' or (len(self.moves)>1 and self.moves[-1]['vertex']==self.moves[-2]['vertex']=='pass')))
        return dict(board=self.board, size=self.size, human=self.human, turn='B' if len(self.moves)%2==0 else 'W', moves=self.moves, over=over)
    def apply(self, color, vertex):
        self.snapshots.append([row[:] for row in self.board])
        if vertex not in ('pass','resign'):
            x,y=COLS.index(vertex[0]), self.size-int(vertex[1:]); value=1 if color=='B' else 2
            self.board[y][x]=value
            def group(sx,sy):
                seen=set(); todo=[(sx,sy)]; liberties=set(); target=self.board[sy][sx]
                while todo:
                    a,b=todo.pop()
                    if (a,b) in seen: continue
                    seen.add((a,b))
                    for c,d in ((a-1,b),(a+1,b),(a,b-1),(a,b+1)):
                        if 0<=c<self.size and 0<=d<self.size:
                            if self.board[d][c]==0: liberties.add((c,d))
                            elif self.board[d][c]==target: todo.append((c,d))
                return seen, liberties
            for a,b in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0<=a<self.size and 0<=b<self.size and self.board[b][a] not in (0,value):
                    stones,liberties=group(a,b)
                    if not liberties:
                        for c,d in stones: self.board[d][c]=0
            stones,liberties=group(x,y)
            if not liberties:
                for c,d in stones: self.board[d][c]=0
        self.moves.append(dict(color=color,vertex=vertex))
    def play(self, vertex):
        s=self.state()
        if s['over'] or s['turn']!=self.human: raise ValueError('当前不能落子，请让 AI 落子或悔棋。')
        self.engine.command(f'play {self.human} {vertex}')
        self.apply(self.human,vertex)
    def ai(self):
        s=self.state()
        if s['over'] or s['turn']==self.human: raise ValueError('当前不是 AI 回合。')
        vertex=self.engine.command(f"genmove {s['turn']}").strip()
        self.apply(s['turn'],vertex.lower() if vertex.lower() in ('pass','resign') else vertex.upper())
    def undo(self):
        if not self.moves: raise ValueError('还没有可撤回的棋步。')
        if self.moves[-1]['vertex'] != 'resign': self.engine.command('undo')
        self.moves.pop(); self.board=self.snapshots.pop()

GAMES={}
GAMES_LOCK = threading.RLock()

def cleanup_games(now=None):
    now = time.monotonic() if now is None else now
    with GAMES_LOCK:
        for key, game in list(GAMES.items()):
            if now - game.last_used >= 900:
                game.engine.close()
                del GAMES[key]

def idle_cleanup(stop):
    while not stop.wait(30):
        cleanup_games()

class Handler(BaseHTTPRequestHandler):
    def authorized(self):
        password = os.environ.get('GO_PASSWORD')
        if not password:
            return True
        expected = 'Basic ' + base64.b64encode(('go:' + password).encode()).decode()
        if hmac.compare_digest(self.headers.get('Authorization', '').encode(), expected.encode()):
            return True
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Go trial", charset="UTF-8"')
        self.send_header('Content-Length', '0')
        self.end_headers()
        return False
    def reply(self, status, obj):
        data=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        if not self.authorized(): return
        files={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
        if self.path not in files: return self.reply(404,{'error':'Not found'})
        name,mime=files[self.path]; data=(ROOT/'static'/name).read_bytes(); self.send_response(200); self.send_header('Content-Type',mime); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        if not self.authorized(): return
        with GAMES_LOCK:
            self.handle_post()
    def handle_post(self):
        try:
            cleanup_games()
            length=int(self.headers.get('Content-Length',0))
            if not 0 < length <= 4096: raise ValueError('请求大小无效')
            body=json.loads(self.rfile.read(length))
            if not isinstance(body, dict): raise ValueError('请求格式无效')
            if self.path=='/api/end':
                old = GAMES.pop(body.get('id', ''), None)
                if old: old.engine.close()
                return self.reply(200, {'ended': True})
            if self.path=='/api/new':
                size=body.get('size',19); human=body.get('human','B')
                if size not in (9,13,19) or human not in ('B','W'): raise ValueError('无效的棋盘或颜色')
                old=GAMES.pop(body.get('id',''),None)
                if old:
                    with old.lock: old.engine.close()
                if len(GAMES)>=1: raise ValueError('试用版同时只支持一局，请等待当前访客点击结束对局，或闲置 15 分钟后重试。')
                game=Game(size,human); key=uuid.uuid4().hex; GAMES[key]=game
            else:
                key=body.get('id'); game=GAMES.get(key)
                if not game: raise ValueError('请先开始新对局。')
                game.last_used = time.monotonic()
                with game.lock:
                    if self.path=='/api/play':
                        x,y=body.get('x'),body.get('y')
                        if not isinstance(x,int) or not isinstance(y,int) or not (0<=x<game.size and 0<=y<game.size): raise ValueError('无效坐标')
                        game.play(COLS[x]+str(game.size-y))
                    elif self.path=='/api/pass': game.play('pass')
                    elif self.path=='/api/ai': game.ai()
                    elif self.path=='/api/undo': game.undo()
                    else: return self.reply(404,{'error':'Not found'})
            self.reply(200,dict(id=key,**game.state()))
        except (ValueError, OSError, RuntimeError, KeyError, TypeError) as e: self.reply(400,{'error':str(e)})

def create_server(port=8000, fallback=True):
    if not 1 <= port <= 65535:
        raise ValueError('PORT 必须是 1 到 65535 之间的整数。')
    ports = range(port, min(port + 11, 65536)) if fallback else [port]
    for candidate in ports:
        try:
            return ThreadingHTTPServer(('127.0.0.1', candidate), Handler)
        except OSError as error:
            if error.errno != errno.EADDRINUSE:
                raise
    raise OSError(errno.EADDRINUSE, '端口已被占用，请使用 PORT=8080 python3 app.py 指定其他空闲端口。')

def main():
    def stop_service(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop_service)
    try:
        configured_port = os.environ.get('PORT')
        server = create_server(int(configured_port) if configured_port is not None else 8000,
                               fallback=configured_port is None)
    except (ValueError, OSError) as error:
        print(f'启动失败：{error}', file=sys.stderr)
        return 1
    with server:
        stop = threading.Event()
        cleaner = threading.Thread(target=idle_cleanup, args=(stop,), daemon=True)
        cleaner.start()
        port = server.server_address[1]
        if configured_port is None and port != 8000:
            print(f'8000 端口已被占用，已自动选择 {port}。', flush=True)
        print(f'围棋网页：http://127.0.0.1:{port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()
            with GAMES_LOCK:
                for game in GAMES.values(): game.engine.close()
                GAMES.clear()
    return 0

if __name__=='__main__':
    sys.exit(main())
