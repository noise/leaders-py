#!/usr/bin/env python

"""
Leaderboard core logic

See README.md for further documentation, and tests/ directory for examples.

Note currently weeks start at midnight on Monday, and are not configurable.
"""

from collections import namedtuple
from datetime import datetime
import hashlib
import itertools
import logging
import time

from redis import StrictRedis
from time_range import TimeRange

log = logging.getLogger(__name__)

_KEY_DELIMITER = '/'

Leader = namedtuple('Leader', 'id score rank ts')
Leaders = namedtuple('Leaders', 'total start end leaders')


class Leaderboard(object):
    """
    Main class for leaderboards.
    """
    _1_DAY_SECONDS = 60 * 60 * 24
    _1_WEEK_SECONDS = _1_DAY_SECONDS * 7
    _1_MONTH_SECONDS = _1_DAY_SECONDS * 31

    # Constants for specifying range(s) to Leaderboard constructor
    # TODO: make expiration configurable and setup a pruner task
    RANGE_DAILY = TimeRange('d', '%Y%m%d', 3 * _1_DAY_SECONDS, _KEY_DELIMITER)
    RANGE_WEEKLY = TimeRange('w', '%Y%W', 2 * _1_WEEK_SECONDS + 2 * _1_DAY_SECONDS, _KEY_DELIMITER)
    RANGE_MONTHLY = TimeRange('m', '%Y%m', 2 * _1_MONTH_SECONDS + 2 * _1_DAY_SECONDS, _KEY_DELIMITER)
    RANGE_ALLTIME = TimeRange('a', 'a', -1, _KEY_DELIMITER)
    RANGES_ALL = [RANGE_DAILY, RANGE_WEEKLY, RANGE_MONTHLY, RANGE_ALLTIME]

    def __init__(self, game, metric, ranges=RANGES_ALL, reverse=True,
                 timed_ties=False, tie_oldest_wins=True,
                 redis=None):
        """
        :param reverse: True for sorting by high to low scores
        :param timed_ties: True to use a given timestamp to resolve tie scores, assumes score values are ints
        :param tie_oldest_wins: True if the earlier time wins
        """
        self.game = game
        self.metric = metric
        self.ranges = ranges
        self.reverse = reverse
        self.timed_ties = timed_ties
        self.tie_oldest_wins = tie_oldest_wins

        if not redis:
            self.r = StrictRedis()
        else:
            self.r = redis

    def _board_key(self, range, slots_ago=0):
        """
        Board keys are of the format:
        /leaders/{game}/{metric}/{range_code}/{range_slot}
        e.g. /combat/highscore/d/20130207
        """
        if slots_ago != 0:
            d = range.date_range(slots_ago)[0]
        else:
            d = datetime.utcnow()
        return _KEY_DELIMITER.join(["leaders", self.game, self.metric,
                                    range.format(d)])

    def _hashlist(self, l):
        """
        hash from a list for creating unique temp zset keys
        """
        h = hashlib.sha1()
        for i in l:
            h.update(i)
        h.update(str(time.time()))
        return h.hexdigest()

    def _range(self, key, start, end):
        if self.reverse:
            return self.r.zrevrange(key, start, end, withscores=True, score_cast_func=float)
        else:
            return self.r.zrange(key, start, end, withscores=True, score_cast_func=float)

    def _add_ranks(self, leaders, offset=0):
        """
        Calculate ranks and update the given leader list to include them.
        Ranks start at 1.
        """
        with_ranks = [Leader(m, s, rank, t) for (m, s, t), rank in zip(leaders, itertools.count(offset + 1))]
        return with_ranks

    def _dt_to_ts(self, ts):
        """
        Ensure we are using a UNIX timestamp
        """
        if isinstance(ts, datetime):
            return (ts - datetime(1970, 1, 1)).total_seconds()
        else:
            return ts

    def _encode_value_with_time(self, value, ts):
        """
        Redis will rank members with identical scores lexigraphically. Often this is not
        what we want for a leaderboard. Using the timed_ties option, we will r the
        timestamp in the decimal part of the float score and thereby use it for tie-breaking.
        tie_oldest_wins controls whether older or newer timestamps get ranked higher.
        """
        if not ts:
            ts = time.time()
        else:
            ts = self._dt_to_ts(ts)
        if self.reverse == self.tie_oldest_wins:
            # invert the timestamp for proper ordering
            ts = 3000000000 - ts
        to_dec = 0.0000000001
        return float(value) + (ts * to_dec)

    def _decode_value_with_time(self, combo):
        from_dec = 10000000000
        value = int(combo)
        ts = (combo - value) * from_dec
        if self.reverse == self.tie_oldest_wins:
            ts = datetime.utcfromtimestamp(3000000000 - ts)
        return value, ts

    def _leaders_with_ranks(self, key, offset, end):
        total = self.r.zcard(key)
        l = self._range(key, offset, end)
        if self.timed_ties:
            l = [((m,) + self._decode_value_with_time(s)) for (m, s) in l]
        else:
            l = [(m, s, 0) for (m, s) in l]
        log.info(l)
        with_ranks = self._add_ranks(l, offset)
        return total, with_ranks

    def set_metric(self, user, value, ts=None):
        """
        Set a new peak value for this user, e.g. high score
        """
        if self.timed_ties:
            value = self._encode_value_with_time(value, ts)

        for r in self.ranges:
            key = self._board_key(r)
            self.r.zadd(key, value, user)
            if r != self.RANGE_ALLTIME:
                self.r.expire(key, r.expiration)

    def inc_metric(self, user, value, ts=None):
        """
        Increment the current value for this user, e.g. total earned
        """
        if ts:
            log.warn('inc_metric: timestamps not supported yet')

        for r in self.ranges:
            key = self._board_key(r)
            self.r.zincrby(key, user, value)
            if r != self.RANGE_ALLTIME:
                self.r.expire(key, r.expiration)

    def leaders(self, range, limit=-1, offset=0, id=None, slots_ago=0):
        """
        Retrieve a list of global leaders.

        :param range: The TimeRange to query
        :param limit: Maximum number of entries to return
        :param offset: Rank to start at, ignored if id is provided
        :param id: Member to center the range of entries around, i.e. "leaders near me"
        :param slots_ago: number of time slots prior, e.g. 1 for yesterday, last week, etc.
        """
        key = self._board_key(range, slots_ago)

        if id:
            if self.reverse:
                rank = self.r.zrevrank(key, id)
            else:
                rank = self.r.zrank(key, id)
            log.debug('uid: %r, rank: %r', id, rank)
            if rank is None:
                log.warn('specified id %r not found in board %r', id, key)
                rank = 0
            offset = max(0, rank - int(round(limit / 2.0)) + 1)
            end = rank + limit / 2 if limit > 0 else -1
        else:
            end = offset + limit - 1 if limit > 0 else -1

        total, with_ranks = self._leaders_with_ranks(key, offset, end)
        start, end = range.date_range(slots_ago)
        return Leaders(total, start, end, with_ranks)

    def leaders_friends_list(self, friends, range, limit=-1, offset=0, slots_ago=0):
        """
        retrieve a list of leaders from the given friends list
        """
        # create a temp zset of friends to intersect w/global list
        # todo: allow for caching the friend list via config
        tmpid = self._hashlist(friends)
        friends_key = 'friends_' + tmpid
        pipe = self.r.pipeline()
        for f in friends:
            pipe.zadd(friends_key, 0, f)
        pipe.execute()

        l = self.leaders_friends_key(friends_key, range, limit, offset, slots_ago)
        self.r.delete(friends_key)
        return l

    def leaders_friends_key(self, friends_key, range, limit=-1, offset=0, slots_ago=0):
        """
        Retrieve a list of leaders from the given friends list
        """
        key = self._board_key(range, slots_ago)
        inter_key = 'inter_' + friends_key + "_" + key

        self.r.zinterstore(inter_key, [key, friends_key])
        end = offset + limit if limit > 0 else -1

        total, with_ranks = self._leaders_with_ranks(inter_key, offset, end)

        self.r.delete(inter_key)
        start, end = range.date_range(slots_ago)
        return Leaders(total, start, end, with_ranks)

    def clear(self, range, slots_ago=0):
        """
        """
        key = self._board_key(range, slots_ago)
        self.r.delete(key)

    def clear_all(self):
        # TODO: track and clear all prior slots
        for range in self.ranges:
            self.clear(range)
