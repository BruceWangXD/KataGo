import io
import json
import socket
import urllib.request
import unittest
from unittest.mock import patch
import app
import share

class FakeEngine:
    instances = []
    def __init__(self, size):
        self.closed = False
        self.instances.append(self)
    def command(self, text): return ''
    def close(self): self.closed = True

class ShareTests(unittest.TestCase):
    def test_occupied_old_port_and_repeated_restarts_and_ends(self):
        occupied = socket.socket()
        try:
            try: occupied.bind(('127.0.0.1', 8765)); occupied.listen()
            except OSError: occupied.close()  # Already occupied is the same regression.
            FakeEngine.instances = []
            def tunnel(args):
                url = args[args.index('--url') + 1]
                self.assertNotEqual(url, 'http://127.0.0.1:8765')
                self.assertEqual(urllib.request.urlopen(url, timeout=3).status, 200)
                def post(action, body):
                    return json.load(urllib.request.urlopen(urllib.request.Request(url+'/api/'+action, json.dumps(body).encode(), {'Content-Type':'application/json'}),timeout=3))
                key = None
                for _ in range(12):
                    game = post('new', {'id':key, 'size':9, 'human':'B'})
                    key = game['id']
                    self.assertEqual(len(app.GAMES), 1)
                self.assertTrue(all(e.closed for e in FakeEngine.instances[:-1]))
                self.assertTrue(post('end', {'id':key})['ended'])
                self.assertFalse(app.GAMES)
                self.assertTrue(FakeEngine.instances[-1].closed)
                self.assertTrue(post('end', {'id':key})['ended'])
                post('new', {'size':9, 'human':'W'})
                class Process:
                    def wait(self): return 0
                    def poll(self): return 0
                return Process()
            # Stub authentication here; real authentication is tested independently.
            with patch('share.shutil.which', return_value='/fake/cloudflared'), patch('app.find_katago', return_value='/fake/katago'), patch('share.getpass.getpass', return_value='test-password'), patch('app.Handler.authorized', return_value=True), patch('app.GTP', FakeEngine), patch('share.subprocess.Popen', side_effect=tunnel), patch('sys.stdout', new=io.StringIO()), patch.dict('os.environ', {}, clear=True):
                # Game's default argument retains GTP, so inject the stub explicitly.
                original = app.Game
                with patch('app.Game', side_effect=lambda size,human:original(size,human,FakeEngine)):
                    self.assertEqual(share.main(),0)
            self.assertFalse(app.GAMES)
            self.assertTrue(all(e.closed for e in FakeEngine.instances))
        finally:
            occupied.close()

if __name__=='__main__':unittest.main()
