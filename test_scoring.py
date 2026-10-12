import copy
import unittest
from scoring import score_board

class ScoringTests(unittest.TestCase):
    def test_empty_board_neutral(self):
        s=score_board([[0]*9 for _ in range(9)])
        self.assertEqual(len(s['regions']),1)
        self.assertEqual(s['territory'],{'B':0,'W':0,'N':81})
        self.assertEqual((s['winner'],s['margin']),('W',7.5))
    def test_separate_eyes_and_neutral_region(self):
        board=[[1,1,1,0,2,2,2],[1,0,1,0,2,0,2],[1,1,1,0,2,2,2]]
        # Square board with separate enclosed eyes, outside touches both colors.
        board += [[0]*7 for _ in range(4)]
        original=copy.deepcopy(board)
        s=score_board(board)
        self.assertEqual(s['territory']['B'],1)
        self.assertEqual(s['territory']['W'],1)
        self.assertEqual(s['stones'],{'B':8,'W':8})
        self.assertEqual(s['white'],16.5)
        self.assertEqual(board,original)
    def test_edge_region_and_override_changes_winner(self):
        board=[[1,1,1],[1,0,0],[1,0,0]]
        s=score_board(board)
        self.assertEqual(s['territory']['B'],4)
        self.assertEqual(s['winner'],'B')
        region=s['regions'][0]['id']
        white=score_board(board,{region:'W'})
        self.assertEqual(white['territory'],{'B':0,'W':4,'N':0})
        self.assertEqual((white['winner'],white['margin']),('W',6.5))
        neutral=score_board(board,{region:'N'})
        self.assertEqual(neutral['territory']['N'],4)
    def test_all_stones_no_regions(self):
        s=score_board([[1,2],[2,1]])
        self.assertEqual(s['regions'],[])
        self.assertEqual(s['black'],2)
        self.assertEqual(s['white'],9.5)
    def test_mixed_boundary_is_neutral(self):
        s=score_board([[1,0],[0,2]])
        self.assertEqual(s['territory']['N'],2)
    def test_invalid_owner(self):
        with self.assertRaises(ValueError):score_board([[0]],{'0,0':'invalid'})

if __name__=='__main__':unittest.main()
