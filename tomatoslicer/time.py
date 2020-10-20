from datetime import (
    datetime,
    timedelta,
    date,
)
from calendar import monthrange

from dateutil.relativedelta import relativedelta
from . import constants
from .shortcuts import (
    align_to_day,
    align_to_week,
    align_to_month,
    align_to_year,
)


class TimeSlice(object):
    LEFT_EDGE = constants.LEFT_EDGE
    RIGHT_EDGE = constants.RIGHT_EDGE

    _start = None
    _end = None

    tz = None

    def __init__(self, start, end=None, duration=None):
        """
        A TimeSlice requires a start and either an explicit end or a duration from which the end can be derived.
        All time slices are inclusive of their start and end for the purposes of comparison.
        :param start: the
        :type start: datetime
        :param end:
        :type end: datetime
        :param duration:
        :type duration: timedelta
        """
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

    def __eq__(self, other):
        return self._start == other._start and self._end == other._end

    def __str__(self):
        return 'Time Slice: {} - {}'.format(
            self.start.isoformat(),
            self.end.isoformat(),
        )

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

        correct_start_day = None
        correct_end_day = None

        # fix flapping on month math
        if type(interval) == relativedelta and (interval.months is not None or interval.years is not None):
            if self._start.day > 28:
                correct_start_day = self._start.day

            if self.end.day > 28:
                correct_end_day = self._end.day

        one_microsecond = timedelta(microseconds=1)

        while interval_left_cursor < self._end:
            next_interval_left_cursor = interval_left_cursor + interval
            interval_right_cursor = next_interval_left_cursor - one_microsecond

            if correct_start_day is not None:
                month_length = monthrange(interval_left_cursor.year, interval_left_cursor.month)[1]

                interval_left_cursor = interval_left_cursor.replace(day=min(
                    month_length,
                    correct_start_day,
                ))

            if correct_end_day is not None:
                month_length = monthrange(interval_right_cursor.year, interval_right_cursor.month)[1]

                interval_right_cursor = interval_right_cursor.replace(day=min(
                    month_length,
                    correct_end_day,
                ))

            yield TimeSlice(interval_left_cursor, min(interval_right_cursor, self._end))

            interval_left_cursor = next_interval_left_cursor

    def iter_days(self, step=1):
        return self.iter(timedelta(days=step))

    def iter_weeks(self, step=1):
        return self.iter(timedelta(days=7 * step))

    def iter_months(self, step=1):
        return self.iter(relativedelta(months=step))

    def iter_years(self, step=1):
        return self.iter(relativedelta(years=step))

    def align_start_to_day(self, edge=LEFT_EDGE):
        self.start = align_to_day(self._start, edge=edge)

    def align_end_to_day(self, edge=RIGHT_EDGE):
        self.end = align_to_day(self._end, edge=edge)

    def align_start_to_week(self, edge=LEFT_EDGE):
        self.start = align_to_week(self._start, edge=edge)

    def align_end_to_week(self, edge=RIGHT_EDGE):
        self.end = align_to_week(self._end, edge=edge)

    def align_start_to_month(self, edge=LEFT_EDGE):
        self.start = align_to_month(self._start, edge=edge)

    def align_end_to_month(self, edge=RIGHT_EDGE):
        self.end = align_to_month(self._end, edge=edge)

    def align_start_to_year(self, edge=LEFT_EDGE):
        self.start = align_to_year(self._start, edge=edge)

    def align_end_to_year(self, edge=RIGHT_EDGE):
        self.end = align_to_year(self._end, edge=edge)

    def shift_back(self, duration):
        self._start = self._start - duration
        self._end = self._end - duration

    def shift_forward(self, duration):
        self._end = self._end + duration
        self._start = self._start + duration


class NthWeekdayCalculator(object):

    def __init__(self, year, month, nth, iso_weekday):
        """
        Finds the nth instance of a certain weekday in a specific month, e.g. 3rd Wednesday of the month
        Allows iterating over months via next and previous
        :param year: Year for the month in question
        :param month: Month in question
        :param nth: Sequence of day in question
        :param iso_weekday: iso_weekday of day in question, e.g. 1 = Mon and 7 = Sun
        """

        self.year = year
        self.month = month
        self.nth = nth
        self.iso_weekday = iso_weekday

        weekday_offset = iso_weekday - date(year=self.year, month=self.month, day=1).isoweekday()

        sequence_baseline = (7 * (nth - 1)) + 1

        if weekday_offset >= 0:
            self.day = sequence_baseline + weekday_offset
        else:
            self.day = sequence_baseline + weekday_offset + 7

    @staticmethod
    def new_by_date(from_date, nth, iso_weekday):
        return NthWeekdayCalculator(
            year=from_date.year,
            month=from_date.month,
            nth=nth,
            iso_weekday=iso_weekday,
        )

    @property
    def date(self):
        return date(year=self.year, month=self.month, day=self.day)

    @property
    def previous(self):
        if self.month == 1:
            return NthWeekdayCalculator(
                year=self.year - 1,
                month=12,
                nth=self.nth,
                iso_weekday=self.iso_weekday,
            )
        else:
            return NthWeekdayCalculator(
                year=self.year,
                month=self.month - 1,
                nth=self.nth,
                iso_weekday=self.iso_weekday,
            )

    @property
    def next(self):
        if self.month == 12:
            return NthWeekdayCalculator(
                self.year + 1,
                1,
                nth=self.nth,
                iso_weekday=self.iso_weekday,
            )
        else:
            return NthWeekdayCalculator(
                year=self.year,
                month=self.month + 1,
                nth=self.nth,
                iso_weekday=self.iso_weekday,
            )
