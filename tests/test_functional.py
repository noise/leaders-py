import unittest

from leaders.leaders import Leaderboard
from redis import Redis


class Functional(unittest.TestCase):
    b = Leaderboard('combat', 'hs', [Leaderboard.RANGE_DAILY])
    b2 = Leaderboard('combat', 'earned', [Leaderboard.RANGE_DAILY, Leaderboard.RANGE_WEEKLY])
    r = Redis(host='localhost', port=6379, db=0)  # todo db 9
    size = 20

    @classmethod
    def setUpClass(cls):
        for i in range(0, cls.size):
            cls.b.set_metric('dude' + str(i), i)
            # todo: split to a separate test case for inc vs set uses
            cls.b2.inc_metric('dude' + str(i), i)
            cls.b2.inc_metric('dude' + str(i), i)

    @classmethod
    def tearDownClass(cls):
        cls.r.flushdb()

    def test_size(self):
        key = self.b._board_key(Leaderboard.RANGE_DAILY)
        self.assertEquals(self.size, self.r.zcard(key))
        key = self.b2._board_key(Leaderboard.RANGE_DAILY)
        self.assertEquals(self.size, self.r.zcard(key))
        key = self.b2._board_key(Leaderboard.RANGE_WEEKLY)
        self.assertEquals(self.size, self.r.zcard(key))

    def test_leaders(self):
        l = self.b.leaders(Leaderboard.RANGE_DAILY)
        self.assertEquals(self.size, len(l))
        self.assertEquals(('dude0', 0, 1), l[0])

    def test_leaders_inc(self):
        l = self.b2.leaders(Leaderboard.RANGE_DAILY)
        self.assertEquals(self.size, len(l))
        self.assertEquals(('dude1', 2, 2), l[1])

    def test_leaders_offset(self):
        limit = 5
        l = self.b.leaders(Leaderboard.RANGE_DAILY, limit, 10)
        self.assertEquals(limit, len(l))
        self.assertEquals(('dude10', 10, 11), l[0])

    def test_friends_list(self):
        friends = ['dude3', 'dude12', 'dude13', 'dudenothere', 'dude18']
        l = self.b.leaders_friends_list(friends, Leaderboard.RANGE_DAILY)
        print l
        self.assertEquals(4, len(l))
        self.assertEquals(('dude3', 3, 1), l[0])
        self.assertEquals(('dude18', 18, 4), l[3])

    def test_friends_key(self):
        friends = ['dude3', 'dude12', 'dude13', 'dudenothere', 'dude18']
        for f in friends:
            self.r.zadd("tmp_myfriends", f, 0)
        l = self.b.leaders_friends_key("tmp_myfriends", Leaderboard.RANGE_DAILY)
        print l
        self.assertEquals(4, len(l))
        self.assertEquals(('dude3', 3, 1), l[0])
        self.assertEquals(('dude18', 18, 4), l[3])

    def test_leaders_near(self):
        l = self.b.leaders_near(Leaderboard.RANGE_DAILY, 'dude10', 10)
        print l
        self.assertEquals(10, len(l))


if __name__ == '__main__':
    unittest.main()
