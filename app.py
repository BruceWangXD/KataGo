"""Local Go web app. Run: python app.py. Requires KataGo + a neural model."""
import json, os, subprocess, threading, uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent
COLS = 'ABCDEFGHJKLMNOPQRST'

class GTP:
    def __init__(self, size):
        local_binary = ROOT / 'bin' / ('katago.exe' if os.name == 'nt' else 'katago')
        cloud_binary = Path('/workspace/katago-build/katago')
        default_binary = str(local_binary) if local_binary.is_file() else str(cloud_binary) if cloud_binary.is_file() else 'katago'
        binary = os.environ.get('KATAGO_BIN') or default_binary
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
class Handler(BaseHTTPRequestHandler):
    def reply(self, status, obj):
        data=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        files={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
        if self.path not in files: return self.reply(404,{'error':'Not found'})
        name,mime=files[self.path]; data=(ROOT/'static'/name).read_bytes(); self.send_response(200); self.send_header('Content-Type',mime); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        try:
            length=int(self.headers.get('Content-Length',0))
            if length>4096: raise ValueError('请求过大')
            body=json.loads(self.rfile.read(length))
            if self.path=='/api/new':
                size=body.get('size',19); human=body.get('human','B')
                if size not in (9,13,19) or human not in ('B','W'): raise ValueError('无效的棋盘或颜色')
                old=GAMES.pop(body.get('id',''),None)
                if old:
                    with old.lock: old.engine.close()
                if len(GAMES)>=8: raise ValueError('对局数量已达上限，请重启服务清理。')
                game=Game(size,human); key=uuid.uuid4().hex; GAMES[key]=game
            else:
                key=body.get('id'); game=GAMES.get(key)
                if not game: raise ValueError('请先开始新对局。')
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

if __name__=='__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f'围棋网页：http://127.0.0.1:{port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
