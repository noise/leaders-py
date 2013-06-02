#!/usr/bin/env python

"""
Leaderboard system core logic

See README.md for further documentation, and tests/ directory for examples.
"""

import datetime as dt
import time
import hashlib

from redis import Redis

_KEY_DELIMITER = '/'


class TimeRange(object):
    def __init__(self, code, format, expiration):
        self.range_code = code
        self.slot_format = format
        self.expiration = expiration

    def format(self, date):
        return _KEY_DELIMITER.join([self.range_code,
                                   date.strftime(self.slot_format)])


class Leaderboard(object):
    """
    Main class for leaderboards.
    """

    # Constants for specifying range(s) to Leaderboard constructor
    _1_DAY_SECONDS = 60 * 60 * 24
    _1_WEEK_SECONDS = _1_DAY_SECONDS * 7
    _1_MONTH_SECONDS = _1_DAY_SECONDS * 31  # yes 30.5 on average, but extra is OK.
    # TODO: make expiration configurable
    RANGE_DAILY = TimeRange('d', '%Y%m%d', 3 * _1_DAY_SECONDS)
    RANGE_WEEKLY = TimeRange('w', '%Y%w', 2 * _1_WEEK_SECONDS + 2 * _1_DAY_SECONDS)
    RANGE_MONTHLY = TimeRange('m', '%Y%m', 2 * _1_MONTH_SECONDS + 2 * _1_DAY_SECONDS)
    RANGE_ALLTIME = TimeRange('a', 'a', -1)
    RANGES_ALL = [RANGE_DAILY, RANGE_WEEKLY, RANGE_MONTHLY, RANGE_ALLTIME]

    def __init__(self, game, metric, ranges=RANGES_ALL, redis=None):
        self.game = game
        self.metric = metric
        self.ranges = ranges
        if not redis:
            self.store = Redis()
        else:
            self.store = redis

    def _board_key(self, range, slots_ago=0):
        """
        Board keys are of the format:
        /leaders/{game}/{metric}/{range_code}/{range_slot}
        e.g. /combat/highscore/d/20130207
        """
        # todo: implement "slots_ago" for yesterday, last week, etc.
        d = dt.date.fromtimestamp(time.time())

        return _KEY_DELIMITER.join(["leaders", self.game, self.metric,
                                    range.format(d)])

    def _hashlist(self, l):
        """
        hash from a list for creating unique temp zset keys
        """
        h = hashlib.sha1()
        for i in l:
            h.update(i)
        return h.hexdigest()

    def _add_ranks(self, leaders, offset=0):
        """
        Our zrange calls give back user id and score/value but not rank.
        We could call zrank but that's inefficient and currently does not deal
        with ties.

        Ranks start at 1, not 0.
        """
        # todo: option to decide how to handle ties
        i = offset + 1
        leaders2 = []
        for l in leaders:
            name, score = l
            leaders2.append((name, score, i))
            i = i + 1
        return leaders2

    def set_metric(self, user, value):
        """
        Set a new peak value for this user, e.g. high score
        """
        for r in self.ranges:
            key = self._board_key(r)
            self.store.zadd(key, user, value)
            if r != self.RANGE_ALLTIME:
                self.store.expire(key, r.expiration)

    def inc_metric(self, user, value):
        """
        Increment the current value for this user, e.g. total earned
        """
        for r in self.ranges:
            key = self._board_key(r)
            self.store.zincrby(key, user, value)
            if r != self.RANGE_ALLTIME:
                self.store.expire(key, r.expiration)

    def leaders(self, range, limit=-1, offset=0, slots_ago=0):
        '''
        retrieve a list of global leaders
        '''
        key = self._board_key(range, slots_ago)
        end = offset + limit - 1 if limit > 0 else -1
        l = self.store.zrange(key, offset, end, withscores=True)
        return self._add_ranks(l, offset)

    def leaders_near(self, range, user, limit, slots_ago=0):
        '''
        retrieve a list of global leaders surrounding the given user
        '''
        key = self._board_key(range, slots_ago)
        rank = self.store.zrank(key, user)
        print rank

        l = self.store.zrange(key, max(0, rank - limit / 2 + 1),
                              rank + limit / 2,
                              withscores=True)
        return self._add_ranks(l)

    def leaders_friends_list(self, friends, range, limit=-1, offset=0, slots_ago=0):
        '''
        retrieve a list of leaders from the given friends list
        '''
        # create a temp zset of friends to intersect w/global list
        # todo: allow for caching the friend list via config
        tmpid = self._hashlist(friends)
        friends_key = 'friends_' + tmpid
        # todo: pipeline
        for f in friends:
            self.store.zadd(friends_key, f, 0)

        l = self.leaders_friends_key(friends_key, range, limit, offset, slots_ago)
        self.store.delete(friends_key)
        return l

    def leaders_friends_key(self, friends_key, range, limit=-1, offset=0, slots_ago=0):
        '''
        retrieve a list of leaders from the given friends list
        '''
        key = self._board_key(range, slots_ago)
        inter_key = 'inter_' + friends_key + "_" + key

        self.store.zinterstore(inter_key, [key, friends_key])
        end = offset + limit if limit > 0 else -1
        l = self.store.zrange(inter_key, offset, end, withscores=True)

        self.store.delete(inter_key)
        return self._add_ranks(l)
