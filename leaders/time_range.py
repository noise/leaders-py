import calendar
from datetime import datetime, timedelta


class TimeRange(object):
    def __init__(self, code, format, expiration, key_delimiter):
        self.range_code = code
        self.slot_format = format
        self.expiration = expiration
        self.key_delimiter = key_delimiter

    def format(self, date):
        return self.key_delimiter.join([self.range_code, date.strftime(self.slot_format)])

    def __repr__(self):
        return self.range_code

    def date_range(self, slots_ago=0):
        d = datetime.utcnow()
        if self.range_code == 'd':
            d = d - timedelta(days=slots_ago)
            start = datetime(d.year, d.month, d.day)
            end = datetime(d.year, d.month, d.day, 23, 59, 59)
        elif self.range_code == 'w':
            d = d - timedelta(weeks=slots_ago)
            day_of_wk = d.weekday()
            day1 = d - timedelta(days=day_of_wk)
            day7 = d + timedelta(days=(6 - day_of_wk))
            start = datetime(day1.year, day1.month, day1.day)
            end = datetime(day7.year, day7.month, day7.day, 23, 59, 59)
        elif self.range_code == 'm':
            if slots_ago >= d.month:
                start = datetime(d.year - 1, d.month + 12 - slots_ago, 1)
            else:
                start = datetime(d.year, d.month - slots_ago, 1)
            end = datetime(start.year, start.month, calendar.monthrange(start.year, start.month)[1], 23, 59, 59)
        else:
            start, end = datetime.utcfromtimestamp(0), datetime.utcfromtimestamp(2147483647)

        return start, end
