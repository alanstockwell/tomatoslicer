from datetime import (
    datetime,
    timedelta,
)
from calendar import monthrange

from dateutil.relativedelta import relativedelta


ALIGN_MODE_DAY = 0
ALIGN_MODE_WEEK = 1
ALIGN_MODE_MONTH = 2
ALIGN_MODE_YEAR = 3


class TimeSlice(object):
    _start = None
    _end = None

    tz = None

    def __init__(self, start, end=None, duration=None):
        self._start = start

        if end is not None and duration is None:
            self._end = end
        elif end is None and duration is not None:
            self._end = self._start + duration
        elif end is None and duration is None:
            self._end = start
        else:
            raise ValueError('end and duration cannot both be set')

        if self._start > self._end:
            raise ValueError('Start cannot come after the end of a TimeSlice')

    def __add__(self, other):
        return TimeSlice(min(self._start, other._start), end=max(self._end, other._end))

    @property
    def naive(self):
        return self._start.tzinfo is None or self._start.tzinfo.utcoffset(self._start) is None

    @property
    def tzinfo(self):
        return self._start.tzinfo

    @property
    def zero_length(self):
        return self._start == self._end

    @property
    def duration(self):
        return self._end - self._start

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, value):
        self._start = value

        if self._start > self._end:
            raise ValueError('Start cannot be set to a time after the end of a TimeSlice')

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, value):
        self._end = value

        if self._start > self._end:
            raise ValueError('End cannot be set to a time before the start of a TimeSlice')

    @property
    def range(self):
        return self._start, self._end

    def overlaps(self, other, completely=False):
        if type(other) == datetime:
            return self._start <= other <= self._end
        else:
            if completely:
                return (other._start >= self._start <= other._end) and (other._end <= self._end >= other._start)
            else:
                return (other._end >= self._start >= other._start) or (other._start <= self._end <= other._end)

    def before(self, other):
        if type(other) == datetime:
            return self._end <= other
        else:
            return self._end <= other._start

    def after(self, other):
        if type(other) == datetime:
            return self._start >= other
        else:
            return self._start >= other._end

    def iter(self, interval):
        interval_left_cursor = self._start

        # fix flapping on month math
        if type(interval) == relativedelta and interval.months is not None:
            correct_day = self._start.day
        else:
            correct_day = None

        while interval_left_cursor < self._end:
            interval_right_cursor = interval_left_cursor + interval

            if correct_day is not None:
                month_length = monthrange(interval_right_cursor.year, interval_right_cursor.month)[1]

                interval_right_cursor = interval_right_cursor.replace(day=min(
                    month_length,
                    correct_day,
                ))

            yield TimeSlice(interval_left_cursor, min(interval_right_cursor, self._end))

            interval_left_cursor = interval_right_cursor

    def iter_days(self, count=1):
        return self.iter(timedelta(days=count))

    def iter_weeks(self, count=1):
        return self.iter(timedelta(days=7 * count))

    def iter_months(self, count=1):
        return self.iter(relativedelta(months=count))
