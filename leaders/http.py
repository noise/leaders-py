#!/usr/bin/python
'''
HTTP REST API for Leaderboard Service
'''
import json
from flask import Flask
from flask import request
from leaders import Leaderboard

app = Flask(__name__)

@app.route('/')
def index():
    return "boo"

@app.route('/<game>/<metric>/<user>', methods=['POST'])
def add_value(game, metric, user):
    try:
        value = request.values['value']
    except(KeyError):
        return ('Must provide "value" parameter', 400)
    
    # TODO: figure out how we should deal with spec'ing time ranges for the board?
    # TODO: just punt for now and use all ranges?
    b = Leaderboard(game, metric, Leaderboard.RANGES_ALL)
    b.set_metric(user, value)
    return "OK"

@app.route('/<game>/<metric>/<user>/friends')
def leaders_friends(game, metric, user):
    return ('Not implemented', 500)

@app.route('/<game>/<metric>/<range_code>', methods=['GET'])
def leaders(game, metric, range_code):
    for r in Leaderboard.RANGES_ALL:
        if r.range_code == range_code:
            range = r
            break

    b = Leaderboard(game, metric, r)
    l = b.leaders(r)
    return json.dumps(l)


if __name__ == '__main__':
    #app.debug = True
    app.run(host='0.0.0.0')
