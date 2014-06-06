import unittest

from leaders.leaders import Leaderboard
from mockredis import MockRedis


class TestLeaderboard(unittest.TestCase):
    r = MockRedis(strict=True)
    size = 20

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        cls.r.flushdb()

    def tearDown(self):
        self.r.flushdb()

    def _setup_board(self):
        b = Leaderboard('combat', 'rank', [Leaderboard.RANGE_DAILY], reverse=False, redis=self.r)
        for i in range(1, self.size + 1):
            b.set_metric('player' + str(i), i)
        return b

    def test_size(self):
        b = self._setup_board()
        key = b._board_key(Leaderboard.RANGE_DAILY)
        self.assertEquals(self.size, self.r.zcard(key))

    def test_size2(self):
        b = Leaderboard('combat', 'rank', [Leaderboard.RANGE_DAILY, Leaderboard.RANGE_WEEKLY], reverse=False, redis=self.r)
        for i in range(1, self.size + 1):
            b.set_metric('player' + str(i), i)
        key = b._board_key(Leaderboard.RANGE_DAILY)
        self.assertEquals(self.size, self.r.zcard(key))
        key = b._board_key(Leaderboard.RANGE_WEEKLY)
        self.assertEquals(self.size, self.r.zcard(key))

    def test_leaders(self):
        b = self._setup_board()
        total, start, end, l = b.leaders(Leaderboard.RANGE_DAILY)
        self.assertEquals(self.size, len(l))
        self.assertEquals(('player1', 1.0, 1, 0), l[0])

    def test_leaders_reverse(self):
        b = Leaderboard('combat', 'rank', [Leaderboard.RANGE_DAILY], reverse=True, redis=self.r)
        for i in range(1, self.size + 1):
            b.set_metric('player' + str(i), i)
        total, start, end, l = b.leaders(Leaderboard.RANGE_DAILY)
        self.assertEquals(self.size, len(l))
        self.assertEquals(('player20', 20.0, 1, 0), l[0])

    def test_leaders_inc(self):
        #b = self._setup_board()
        #l = b.leaders(Leaderboard.RANGE_DAILY)
        #self.assertEquals(self.size, len(l.leaders))
        #self.assertEquals(('player20', 40.0, 1, 0), l[0])
        pass

    def test_leaders_offset(self):
        b = self._setup_board()
        limit = 5
        total, start, end, l = b.leaders(Leaderboard.RANGE_DAILY, limit, 10)
        print l
        self.assertEquals(limit, len(l))
        self.assertEquals(('player11', 11.0, 11, 0), l[0])

    def test_friends_list(self):
        b = self._setup_board()
        friends = ['player3', 'player12', 'player13', 'playernothere', 'player18']
        total, start, end, l = b.leaders_friends_list(friends, Leaderboard.RANGE_DAILY)
        print l
        self.assertEquals(4, len(l))
        self.assertEquals(('player3', 3.0, 1, 0), l[0])
        self.assertEquals(('player18', 18.0, 4, 0), l[3])

    def test_friends_key(self):
        b = self._setup_board()
        friends = ['player3', 'player12', 'player13', 'playernothere', 'player18']
        for f in friends:
            self.r.zadd("tmp_myfriends", 0, f)
        l = b.leaders_friends_key("tmp_myfriends", Leaderboard.RANGE_DAILY)
        print l
        self.assertEquals(4, len(l.leaders))
        self.assertEquals(('player3', 3, 1, 0), l.leaders[0])
        self.assertEquals(('player18', 18, 4, 0), l.leaders[3])

    def test_leaders_near(self):
        b = self._setup_board()
        total, start, end, l = b.leaders(Leaderboard.RANGE_DAILY, limit=11, id='player10')
        print l
        self.assertEquals(11, len(l))
        self.assertEquals(('player10', 10.0, 10, 0), l[5])

    def test_tie_rankings(self):
        # without further handling, ties get ranked lexigraphically
        bt = Leaderboard('ties', 'hs', [Leaderboard.RANGE_DAILY], reverse=True, redis=self.r)
        bt.set_metric('first', 100.0)
        bt.set_metric('second', 100.0)
        bt.set_metric('zzzzz', 100.0)
        total, start, end, l = bt.leaders(Leaderboard.RANGE_DAILY, 10)
        print l
        self.assertEquals(l[0][0], 'zzzzz')
        bt.clear_all()

        bt = Leaderboard('ties', 'hs', [Leaderboard.RANGE_DAILY], reverse=False, redis=self.r)
        bt.set_metric('first', 100.0)
        bt.set_metric('second', 100.0)
        bt.set_metric('aaaaa', 100.0)
        total, start, end, l = bt.leaders(Leaderboard.RANGE_DAILY, 10)
        print l
        self.assertEquals(l[0][0], 'aaaaa')
        bt.clear_all()

    def test_tie_rankings_with_ts(self):
        bt = Leaderboard('ties', 'hs', ranges=[Leaderboard.RANGE_DAILY],
                         reverse=False,
                         timed_ties=True,
                         tie_oldest_wins=True,
                         redis=self.r)

        bt.set_metric('first', 100, ts=1400000001)
        bt.set_metric('second', 100, ts=1400000002)
        bt.set_metric('third', 100, ts=1400000003)
        bt.set_metric('fourth', 101, ts=1400000000)
        total, start, end, l = bt.leaders(Leaderboard.RANGE_DAILY, 10)
        print l
        self.assertEquals(l[0][0], 'first')
        bt.clear_all()

    def test_tie_rankings_with_ts_reverse(self):
        bt = Leaderboard('ties', 'hs', ranges=[Leaderboard.RANGE_DAILY],
                         reverse=True,
                         timed_ties=True,
                         tie_oldest_wins=True,
                         redis=self.r)

        bt.set_metric('first', 100, ts=1400000001)
        bt.set_metric('second', 100, ts=1400000002)
        bt.set_metric('third', 100, ts=1400000003)
        bt.set_metric('fourth', 99, ts=1400000000)
        total, start, end, l = bt.leaders(Leaderboard.RANGE_DAILY, 10)
        print l
        self.assertEquals(l[0][0], 'first')
        bt.clear_all()

    def test_tie_rankings_with_ts_newest(self):
        bt = Leaderboard('ties', 'hs', ranges=[Leaderboard.RANGE_DAILY],
                         reverse=False,
                         timed_ties=True,
                         tie_oldest_wins=False,
                         redis=self.r)

        bt.set_metric('first', 100, ts=1400000003)
        bt.set_metric('second', 100, ts=1400000002)
        bt.set_metric('third', 100, ts=1400000001)
        bt.set_metric('fourth', 101, ts=1400000000)
        total, start, end, l = bt.leaders(Leaderboard.RANGE_DAILY, 10)
        print l
        self.assertEquals(l[0][0], 'first')
        bt.clear_all()

    def test_tie_rankings_with_ts_reverse_newest(self):
        bt = Leaderboard('ties', 'hs', ranges=[Leaderboard.RANGE_DAILY],
                         reverse=True,
                         timed_ties=True,
                         tie_oldest_wins=False,
                         redis=self.r)

        bt.set_metric('first', 100, ts=1400000003)
        bt.set_metric('second', 100, ts=1400000002)
        bt.set_metric('third', 100, ts=1400000001)
        bt.set_metric('fourth', 99, ts=1400000000)
        total, start, end, l = bt.leaders(Leaderboard.RANGE_DAILY, 10)
        print l
        self.assertEquals(l[0][0], 'first')
        bt.clear_all()


if __name__ == '__main__':
    unittest.main()
