import unittest
from app import Game
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
if __name__=='__main__':unittest.main()
