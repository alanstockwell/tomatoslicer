import pytz

from datetime import (
    datetime,
    timedelta,
    date,
    time,
)
from calendar import monthrange

from dateutil.relativedelta import relativedelta
from . import constants
from .shortcuts import (
    align_to_day,
    align_to_week,
    align_to_month,
    align_to_year,
    duration_to_unit_hours,
    duration_to_rounded_unit_hours,
)


class TimeSlice(object):
    LEFT_EDGE = constants.LEFT_EDGE
    RIGHT_EDGE = constants.RIGHT_EDGE

    _start = None
    _end = None

    def __init__(self, start, end=None, duration=None, tz=None,
                 decimal_places=2, rounding_step=None, rounding_mode=None):
        """
        A TimeSlice requires a start and either an explicit end or a duration from which the end can be derived.
        All time slices are inclusive of their start and end for the purposes of comparison.
        :param start:
        :type start: datetime
        :param end:
        :type end: datetime
        :param duration:
        :type duration: timedelta
        :param decimal_places: Used when calculating rounded unit hours
        :type decimal_places: int
        :param rounding_step: Used when calculating rounded unit hours
        :type rounding_step: float
        :param rounding_mode: Used when calculating rounded unit hours
        :type rounding_mode: str
        """

        if tz is None:
            if start.tzinfo is None:
                self.tz = pytz.utc
            else:
                self.tz = pytz.timezone(start.tzinfo.zone)
        else:
            self.tz = tz

        self._start = start.astimezone(pytz.utc)

        if end is not None and duration is None:
            self.end = end
        elif end is None and duration is not None:
            self.end = self.start + duration
        elif end is None and duration is None:
            self.end = self.start
        else:
            raise ValueError('End and duration cannot both be set')

        if self.start > self.end:
            raise ValueError('Start cannot come after the end of a TimeSlice')

        self.decimal_places = decimal_places
        self.rounding_step = rounding_step
        self.rounding_mode = rounding_mode

    def __add__(self, other):
        return TimeSlice(
            self.start + other,
            end=self.end + other,
            decimal_places=self.decimal_places,
            rounding_step=self.rounding_step,
            rounding_mode=self.rounding_mode,
        )

    def __sub__(self, other):
        return TimeSlice(
            self.start - other,
            end=self.end - other,
            decimal_places=self.decimal_places,
            rounding_step=self.rounding_step,
            rounding_mode=self.rounding_mode,
        )

    def __eq__(self, other):
        return self._start == other._start and self._end == other._end

    def __str__(self):
        return 'Time Slice: {} - {}'.format(
            self.start.isoformat(),
            self.end.isoformat(),
        )

    @staticmethod
    def from_dates(start_date, end_date=None, tz=None):
        if end_date is None:
            end_date = start_date

        return TimeSlice(
            datetime.combine(start_date, time.min),
            datetime.combine(end_date, time.max),
            tz=tz,
        )

    @property
    def zero_length(self):
        return self._start == self._end

    @property
    def duration(self):
        return self._end - self._start

    @property
    def unit_hours(self):
        return duration_to_unit_hours(
            self.duration,
            decimal_places=self.decimal_places,
        )

    @property
    def rounded_unit_hours(self):
        return duration_to_rounded_unit_hours(
            self.duration,
            decimal_places=self.decimal_places,
            rounding_step=self.rounding_step,
            rounding_mode=self.rounding_mode,
        )

    @property
    def start(self):
        return self._start.astimezone(self.tz)

    @start.setter
    def start(self, value):
        self._start = value.astimezone(pytz.utc)

        if self._start > self._end:
            raise ValueError('Start cannot be set to a time after the end of a TimeSlice')

    @property
    def end(self):
        return self._end.astimezone(self.tz)

    @end.setter
    def end(self, value):
        self._end = value.astimezone(pytz.utc)

        if self._start > self._end:
            raise ValueError('End cannot be set to a time before the start of a TimeSlice')

    @property
    def range(self):
        return self.start, self.end

    def overlaps(self, other, completely=False):
        if type(other) == datetime:
            try:
                comparison = pytz.utc.localize(other)
            except ValueError:
                comparison = other

            return self._start <= comparison <= self._end
        else:
            if completely:
                return (other._start >= self._start <= other._end) and (other._end <= self._end >= other._start)
            else:
                return (other._end >= self._start >= other._start) or (other._start <= self._end <= other._end)

    def before(self, other):
        if type(other) == datetime:
            return self._end <= pytz.utc.localize(other)
        else:
            return self._end <= other._start

    def after(self, other):
        if type(other) == datetime:
            return self._start >= other
        else:
            return self._start >= other._end

    def iter(self, interval, iterating_months=False):
        interval_left_cursor = self.start

        correct_start_day = None
        correct_end_day = None

        # fix flapping on month math
        if isinstance(interval, relativedelta) and (interval.months > 0 or interval.years > 0):
            if self.start.day > 28:
                correct_start_day = self.start.day

            if self.end.day > 28:
                correct_end_day = self.end.day

        one_microsecond = timedelta(microseconds=1)

        counter = 0

        while interval_left_cursor < self.end:
            next_interval_left_cursor = self.tz.normalize(interval_left_cursor + interval)
            interval_right_cursor = self.tz.normalize(next_interval_left_cursor - one_microsecond)

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

            next_time_slice = TimeSlice(interval_left_cursor, min(interval_right_cursor, self._end))

            if all((
                    iterating_months,
                    counter > 0,
                    next_interval_left_cursor < self.end,
            )):
                # align inner months
                next_time_slice.align_to_month()

            yield next_time_slice

            interval_left_cursor = next_interval_left_cursor

            counter += 1

    def iter_days(self, step=1):
        return self.iter(relativedelta(days=step))

    def iter_weeks(self, step=1):
        return self.iter(relativedelta(days=7 * step))

    def iter_months(self, step=1):
        return self.iter(relativedelta(months=step), iterating_months=True)

    def iter_years(self, step=1):
        return self.iter(relativedelta(years=step))

    def align_start_to_day(self, edge=LEFT_EDGE):
        self.start = align_to_day(self.start, edge=edge)

    def align_end_to_day(self, edge=RIGHT_EDGE):
        self.end = align_to_day(self.end, edge=edge)

    def align_to_day(self, start_edge=LEFT_EDGE, end_edge=RIGHT_EDGE):
        self.align_start_to_day(edge=start_edge)
        self.align_end_to_day(edge=end_edge)

    def align_start_to_week(self, edge=LEFT_EDGE):
        self.start = align_to_week(self.start, edge=edge)

    def align_end_to_week(self, edge=RIGHT_EDGE):
        self.end = align_to_week(self.end, edge=edge)

    def align_to_week(self, start_edge=LEFT_EDGE, end_edge=RIGHT_EDGE):
        self.align_start_to_week(edge=start_edge)
        self.align_end_to_week(edge=end_edge)

    def align_start_to_month(self, edge=LEFT_EDGE):
        self.start = align_to_month(self.start, edge=edge)

    def align_end_to_month(self, edge=RIGHT_EDGE):
        self.end = align_to_month(self.end, edge=edge)

    def align_to_month(self, start_edge=LEFT_EDGE, end_edge=RIGHT_EDGE):
        self.align_start_to_month(edge=start_edge)
        self.align_end_to_month(edge=end_edge)

    def align_start_to_year(self, edge=LEFT_EDGE):
        self.start = align_to_year(self.start, edge=edge)

    def align_end_to_year(self, edge=RIGHT_EDGE):
        self.end = align_to_year(self.end, edge=edge)

    def align_to_year(self, start_edge=LEFT_EDGE, end_edge=RIGHT_EDGE):
        self.align_start_to_year(edge=start_edge)
        self.align_end_to_year(edge=end_edge)

    def shift_left(self, duration):
        self._start = self._start - duration
        self._end = self._end - duration

    def shift_right(self, duration):
        self._end = self._end + duration
        self._start = self._start + duration

    def format_duration(self, day_label='day', hour_label='hr', minute_label='min',
                        day_label_plural=None, hour_label_plural=None, minute_label_plural=None):

        return FormattedDuration(
            self.duration,
            day_label=day_label,
            hour_label=hour_label,
            minute_label=minute_label,
            day_label_plural=day_label_plural,
            hour_label_plural=hour_label_plural,
            minute_label_plural=minute_label_plural,
        ).text


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


class FormattedDuration(object):

    hours = None
    days = None
    minutes = None

    def __init__(self, duration, day_label='day', hour_label='hr', minute_label='min',
                 day_label_plural=None, hour_label_plural=None, minute_label_plural=None):

        self.duration = duration

        self.hours = int(self.duration.total_seconds() // 3600)
        self.days = int(self.hours / 24)
        self.minutes = int((self.duration.total_seconds() % 3600) // 60)

        self._day_label = day_label
        self._hour_label = hour_label
        self._minute_label = minute_label

        if day_label_plural is None:
            self._day_label_plural = '{}s'.format(self._day_label)
        else:
            self._day_label_plural = day_label_plural

        if hour_label_plural is None:
            self._hour_label_plural = '{}s'.format(self._hour_label)
        else:
            self._hour_label_plural = hour_label_plural

        if minute_label_plural is None:
            self._minute_label_plural = '{}s'.format(self._minute_label)
        else:
            self._minute_label_plural = minute_label_plural

        if self.days > 0:
            self.hours = self.hours % (self.days * 24)

    def __str__(self):
        return self.text

    @property
    def text(self):
        if self.days + self.hours == 0:
            return '{} {}'.format(
                self.minutes,
                self._minute_label if self.minutes == 1 else self._minute_label_plural,
            )
        elif self.days == 0:
            return '{} {} {} {}'.format(
                self.hours,
                self._hour_label if self.hours == 1 else self._hour_label_plural,
                self.minutes,
                self._minute_label if self.minutes == 1 else self._minute_label_plural,
            )
        else:
            return '{} {} {} {} {} {}'.format(
                self.days,
                self._day_label if self.days == 1 else self._day_label_plural,
                self.hours,
                self._hour_label if self.hours == 1 else self._hour_label_plural,
                self.minutes,
                self._minute_label if self.minutes == 1 else self._minute_label_plural,
            )
