import unittest
import errno
import socket
from unittest.mock import patch
from app import Game, create_server, find_katago
class Engine:
    def __init__(self,size): self.commands=[]
    def command(self,text):
        self.commands.append(text)
        return 'D4' if text.startswith('genmove') else ''
class GameTests(unittest.TestCase):
    def test_two_single_undos(self):
        g=Game(9,'B',Engine);g.play('C3');g.ai()
        self.assertEqual(len(g.moves),2);g.undo()
        self.assertEqual(g.state()['turn'],'W');self.assertEqual(g.board[5][3],0)
        g.undo();self.assertEqual(g.board,[[0]*9 for _ in range(9)])
        self.assertEqual(g.engine.commands[-2:],['undo','undo'])
    def test_capture_restored_by_undo(self):
        g=Game(9,'B',Engine)
        for color,v in [('W','B2'),('B','A2'),('B','B1'),('B','C2'),('B','B3')]:g.apply(color,v)
        self.assertEqual(g.board[7][1],0);g.undo();self.assertEqual(g.board[7][1],2)
    def test_turn_and_two_passes(self):
        g=Game(9,'B',Engine);g.play('pass')
        with self.assertRaises(ValueError):g.play('A1')
        g.apply('W','pass');self.assertTrue(g.state()['over']);g.undo();self.assertFalse(g.state()['over'])
    def test_engine_reject_keeps_state(self):
        g=Game(9,'B',Engine)
        def reject(text): raise ValueError('illegal move')
        g.engine.command=reject
        with self.assertRaises(ValueError):g.play('A1')
        self.assertEqual(g.moves,[]);self.assertEqual(g.snapshots,[])
class EngineDiscoveryTests(unittest.TestCase):
    def test_homebrew_path_without_shell_path(self):
        for binary in ('/opt/homebrew/bin/katago', '/usr/local/bin/katago'):
            with patch.dict('os.environ', {}, clear=True), patch('app.sys.platform', 'darwin'), patch('app.shutil.which', side_effect=lambda candidate: binary if candidate == binary else None):
                self.assertEqual(find_katago(), binary)

    def test_missing_mac_engine_has_install_instructions(self):
        with patch.dict('os.environ', {}, clear=True), patch('app.sys.platform', 'darwin'), patch('app.shutil.which', return_value=None):
            with self.assertRaisesRegex(ValueError, 'bash setup_macos.sh'):
                find_katago()

    def test_invalid_override_is_not_silently_replaced(self):
        with patch.dict('os.environ', {'KATAGO_BIN': '/missing/katago'}, clear=True), patch('app.shutil.which', return_value=None) as lookup:
            with self.assertRaisesRegex(ValueError, 'KATAGO_BIN'):
                find_katago()
            lookup.assert_called_once_with('/missing/katago')

class StartupTests(unittest.TestCase):
    def test_occupied_port_falls_back(self):
        # Exercise a real occupied socket and a real HTTP server bind.
        with socket.socket() as occupied:
            occupied.bind(('127.0.0.1', 0))
            occupied.listen()
            port = occupied.getsockname()[1]
            if port == 65535: self.skipTest('No higher port available')
            with create_server(port) as server:
                self.assertGreater(server.server_address[1], port)

    def test_explicit_port_does_not_fall_back(self):
        with socket.socket() as occupied:
            occupied.bind(('127.0.0.1', 0))
            occupied.listen()
            with self.assertRaises(OSError) as caught:
                create_server(occupied.getsockname()[1], fallback=False)
            self.assertEqual(caught.exception.errno, errno.EADDRINUSE)

    def test_other_bind_errors_are_not_retried(self):
        with patch('app.ThreadingHTTPServer', side_effect=OSError(errno.EACCES, 'denied')) as constructor:
            with self.assertRaises(OSError): create_server()
            self.assertEqual(constructor.call_count, 1)

    def test_invalid_port(self):
        for port in (0, -1, 65536):
            with self.assertRaises(ValueError): create_server(port)

if __name__=='__main__':unittest.main()
