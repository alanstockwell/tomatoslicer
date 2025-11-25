from datetime import timezone

from copy import deepcopy
from datetime import (
    datetime,
    timedelta,
    date,
    time,
)

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
from .shortcuts import localize


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
                self.tz = timezone.utc
            else:
                self.tz = start.tzinfo
        else:
            self.tz = tz

        self._start = start.astimezone(timezone.utc)

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
        start_time = self.start + other
        end_time = self.end + other

        return TimeSlice(
            start_time,
            end=end_time,
            decimal_places=self.decimal_places,
            rounding_step=self.rounding_step,
            rounding_mode=self.rounding_mode,
        )

    def __sub__(self, other):
        start_time = self.start - other
        end_time = self.end - other

        return TimeSlice(
            start_time,
            end=end_time,
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

    def __repr__(self):
        return '<{}>'.format(str(self))

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
    def spans_dst_start(self):
        start_dst = self.start.dst()
        end_dst = self.end.dst()

        if None in (start_dst, end_dst):
            return False

        return self.start.dst() < self.end.dst()

    @property
    def spans_dst_end(self):
        start_dst = self.start.dst()
        end_dst = self.end.dst()

        if None in (start_dst, end_dst):
            return False

        return self.start.dst() > self.end.dst()

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
        self._start = value.astimezone(timezone.utc)

        if self._start > self._end:
            raise ValueError('Start cannot be set to a time after the end of a TimeSlice')

    @property
    def end(self):
        return self._end.astimezone(self.tz)

    @end.setter
    def end(self, value):
        self._end = value.astimezone(timezone.utc)

        if self._start > self._end:
            raise ValueError('End cannot be set to a time before the start of a TimeSlice')

    @property
    def range(self):
        return self.start, self.end

    @property
    def date_range(self):
        return self.start.date(), self.end.date()

    def copy(self):
        return deepcopy(self)

    def occludes(self, other):
        return self._start <= other._start <= self._end and self._start <= other._end <= self._end

    def occluded_by(self, other):
        return other._start <= self._start <= other._end and other._start <= self._end <= other._end

    def overlaps(self, other):
        if type(other) == datetime:
            try:
                comparison = localize(other, timezone.utc)
            except ValueError:
                comparison = other

            return self._start <= comparison <= self._end
        else:
            return any((
                other._start <= self._start <= other._end,
                other._start <= self._end <= other._end,
                self._start <= other._start <= self._end,
                self._start <= other._end <= self._end,
            ))

    def before(self, other):
        if type(other) == datetime:
            return self._end <= localize(self._end, timezone.utc)
        else:
            return self._end <= other._start

    def after(self, other):
        if type(other) == datetime:
            return self._start >= other
        else:
            return self._start >= other._end

    def iter(self, interval):
        one_microsecond = timedelta(microseconds=1)

        current_time_slice = TimeSlice(self.start, end=self.start + interval)

        while current_time_slice.end - one_microsecond <= self.end:
            yield TimeSlice(current_time_slice.start, end=current_time_slice.end - one_microsecond)

            current_time_slice += interval

            if current_time_slice.spans_dst_start:
                current_time_slice.end -= current_time_slice.end.dst()
            elif current_time_slice.spans_dst_end:
                current_time_slice.end += current_time_slice.end.dst()

    def iter_days(self, step=1):
        return self.iter(relativedelta(days=step))

    def iter_weeks(self, step=1):
        return self.iter(relativedelta(days=7 * step))

    def iter_months(self, step=1):
        return self.iter(relativedelta(months=step))

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

    def split(self, split_time):
        if not self.overlaps(split_time):
            raise ValueError('Split time not in range')

        try:
            start = TimeSlice(
                start=self.start,
                end=split_time - timedelta(microseconds=1),
            )
        except ValueError:
            start = None

        return (
            start,
            TimeSlice(
                start=split_time,
                end=self.end,
            )
        )

    def punch_hole(self, other):
        if self.occluded_by(other):
            return []
        elif not self.overlaps(other):
            return [self.copy()]

        parts = []

        try:
            left_part, right_part = self.split(other.start)

            if left_part is not None:
                parts.append(left_part)
        except ValueError:
            pass

        try:
            left_part, right_part = self.split(other.end)

            parts.append(right_part)
        except ValueError:
            pass

        return parts

    def merge(self, other):
        if self.overlaps(other):
            return TimeSlice(start=min(self.start, other.start), end=max(self.end, other.end))

        raise ValueError('Cannot merge; Time slices do not overlap')

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

    @property
    def total_hours(self):
        return self.hours + (self.days * 24)

    @property
    def total_hours_text(self):
        return '{}:{:02d}'.format(self.total_hours, self.minutes)


class TimeLine(object):

    def __init__(self, time_slices=None, reverse=False):
        self.time_slices = [] if time_slices is None \
            else [time_slices] if isinstance(time_slices, TimeSlice) else \
            list(time_slices)

        self._reverse = reverse

        self.sort()

    def __add__(self, other):
        new_time_line = self.copy()

        new_time_line.time_slices += other.time_slices

        new_time_line.flatten()

        return new_time_line

    def __sub__(self, other):
        new_time_line = self.copy()

        new_time_line.punch_holes(other)

        return new_time_line

    @property
    def reverse(self):
        return self._reverse

    @property
    def start(self):
        try:
            return min((_.start for _ in self.time_slices))
        except ValueError:
            return None

    @property
    def end(self):
        try:
            return max((_.end for _ in self.time_slices))
        except ValueError:
            return None

    @property
    def outer_time_slice(self):
        start = self.start

        if start is None:
            return None

        return TimeSlice(start, end=self.end)

    @property
    def outer_duration(self):
        outer_time_slice = self.outer_time_slice

        if outer_time_slice is None:
            return None

        return outer_time_slice.duration

    @property
    def cumulative_duration(self):
        duration = timedelta()

        for time_slice in self.time_slices:
            duration += time_slice.duration

        return duration

    def copy(self):
        return deepcopy(self)

    def append(self, time_slice):
        self.time_slices.append(time_slice)

    def sort(self, reverse=None):
        if reverse is not None:
            self._reverse = reverse

        self.time_slices.sort(key=lambda x: x.range, reverse=self._reverse)

    def merge_overlap(self):
        if len(self.time_slices) > 0:
            reverse = self.reverse

            self.sort(reverse=True)

            merged_time_slices = []

            current_slice = self.time_slices.pop()

            while len(self.time_slices) > 0:
                next_time_slice = self.time_slices.pop()

                try:
                    current_slice = current_slice.merge(next_time_slice)
                except ValueError:
                    merged_time_slices.append(current_slice)

                    current_slice = next_time_slice

            merged_time_slices.append(current_slice)

            self.time_slices = merged_time_slices

            self.sort(reverse=reverse)

    def flatten(self, reverse=None):
        self.sort(reverse=reverse)
        self.merge_overlap()

    def overlaps(self, other):
        for time_slice in self.time_slices:
            if time_slice.overlaps(other):
                return True

        return False

    def punch_hole(self, hole):
        reverse = self.reverse

        self.sort(reverse=False)

        punched_time_slices = []

        for time_slice in self.time_slices:
            if hole.overlaps(time_slice):
                for punched_time_slice in time_slice.punch_hole(hole):
                    punched_time_slices.append(punched_time_slice)
            else:
                punched_time_slices.append(time_slice)

        self.time_slices = punched_time_slices

        self.sort(reverse=reverse)

    def punch_holes(self, holes):
        if isinstance(holes, TimeLine):
            holes = holes.time_slices

        for hole in holes:
            self.punch_hole(hole)

    def split(self, split_time):
        if self.outer_time_slice.overlaps(split_time):
            reverse = self.reverse

            self.sort(reverse=False)

            left_time_line = TimeLine(reverse=reverse)
            right_time_line = TimeLine(reverse=reverse)

            for time_slice in self.time_slices:
                if time_slice.end < split_time:
                    left_time_line.append(time_slice.copy())
                elif time_slice.overlaps(split_time):
                    left_time_slice, right_time_slice = time_slice.split(split_time)

                    if left_time_slice is not None:
                        left_time_line.append(left_time_slice)

                    right_time_line.append(right_time_slice)
                else:
                    right_time_line.append(time_slice.copy())

            self.sort(reverse=reverse)

            left_time_line.sort()
            right_time_line.sort()

            return [left_time_line, right_time_line]
        else:
            return [self.copy()]

    def crop(self, time_slice):
        if isinstance(time_slice, TimeLine):
            time_slice = time_slice.outer_time_slice

        if time_slice is None or len(self.time_slices) == 0 or not self.outer_time_slice.overlaps(time_slice):
            raise ValueError('Time slice does not overlap timeline')

        kept_part = None

        for part in self.split(time_slice.start):
            if part is not None and part.overlaps(time_slice):
                kept_part = part

        for part in kept_part.split(time_slice.end):
            if part is not None and part.overlaps(time_slice):
                kept_part = part

                break

        return kept_part
