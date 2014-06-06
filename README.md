# Leaders Overview

A leaderboard service/server for online/mobile games, backed by
Redis. Redis offers the unique ability to do sorted set intersections
in the storage server. This allows for "friends leaderboards" to be
computed very efficiently.

# Dependencies

Python 2.7.x, Redis 2.4.x+, Flask, Redis-py, RedisMock

Linux:

```sh
sudo apt-get install redis-server
virtualenv venv --distribute
source venv/bin/activate
pip install -r requirements.txt
```

OS X:

```sh
brew install redis
virtualenv venv --distribute
source venv/bin/activate
pip install -r requirements.txt
```

# Running

Tests:

```sh
./bin/runtests
```

Server:

```sh
./bin/runserver
```

# Design


## Leaderboards

Leaderboards are defined by the Game ID and Board ID. There can be any
number of boards per game. Game ID and Board ID are both free-form
strings, though it's best practice to keep them in the set of
characters: "[A-Z][a-z][0-9]-_.".

Leaderboards can be set to expire after N periods, see Configuration

## Entries

An entry on a given leaderboard consists of a User ID, and
Value. Timestamps are added automatically. 

## Values

Values can either be an absoulte value, e.g. a high-score, where
the maximum during the given period is desired, or a cumulative value,
e.g. total coins earned in the period, number of games wons, etc.  

## Time Ranges

Leaderboards can be set to maintain daily, weekly, or monthly
sets. Currently there is no support for sliding windows such as "last
7 days".


## Storage Design

Boards keys: /leaders/{game_id}/{board_id}/{range_code}/{slot}
* board_id can be any unique string, for example: "highscore", "earned_coins", etc.
* range_code is one of: "d" (daily), "w" (weekly), "m" (monthly), "a" (all time)
* slot is a range dependent format of the current date:
  - daily: yyyymmdd
  - weekly: yyyyww
  - monthly: yyyymm
  - alltime: a

Board data
* the "member" (Redis parlance) for each entry is the user_id and the "score" is the Data Point

Friend lists
* We create temp zsets for each passed in friends list, with the key based off a hash of the list.
* You can also specify the key to an existing zset of friends (TODO)

## Data Integrity

The leaders system makes no attempt to verify that data passed in by
the game is correct, aside from some basic well-formedness
checks. Games are responsible for screening data before pushing it
into Leaders. 

Likewise, there is nothing stopping a caller from doing "set" and "inc" to the same board.

# REST API

The REST API is structured to match the storage design in a nearly 1:1
manner.

GETs:
* /leaders/games
* /leaders/{game_id}/boards
* /leaders/{game_id}/{board_id}/{range_code}
* /leaders/{game_id}/{board_id}/{range_code}/last

POSTs:
* URL: /leaders/{game_id}/{board_id}/{range_code}/{user_id}
* POST vars: 
  * "value"
  * "type", one of: "set"(default), "inc"


# Configuration

(TODO)

