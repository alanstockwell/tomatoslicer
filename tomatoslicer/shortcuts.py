from calendar import monthrange
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from datetime import (
    timedelta,
    datetime,
    date,
    time,
)

from . import constants


def align_to(value, edge, mode=constants.ALIGN_DAY):
    if edge not in (constants.LEFT_EDGE, constants.RIGHT_EDGE):
        raise ValueError('Invalid edge: {}'.format(str(edge)))

    if mode not in (constants.ALIGN_DAY, constants.ALIGN_WEEK, constants.ALIGN_MONTH, constants.ALIGN_YEAR):
        raise ValueError('Invalid alignment mode: {}'.format(str(mode)))

    if isinstance(value, datetime):
        tzinfo = value.tzinfo
        value = value.date()
    else:
        tzinfo = None

    if mode == constants.ALIGN_DAY:
        new_date = value
    elif mode == constants.ALIGN_WEEK:
        start_date = value

        if edge == constants.LEFT_EDGE:
            new_date = start_date - timedelta(days=start_date.isoweekday() - 1)
        else:
            new_date = start_date + timedelta(days=7 - start_date.isoweekday())
    elif mode == constants.ALIGN_MONTH:
        if edge == constants.LEFT_EDGE:
            new_date = value.replace(day=1)
        else:
            new_date = value.replace(day=monthrange(value.year, value.month)[1])
    else:
        if edge == constants.LEFT_EDGE:
            new_date = value.replace(month=1, day=1)
        else:
            new_date = value.replace(month=12, day=31)

    if edge == constants.LEFT_EDGE:
        result = datetime.combine(
            new_date,
            time.min,
        )
    else:
        result = datetime.combine(
            new_date,
            time.max,
        )

    return result if tzinfo is None else tzinfo.localize(result)


def align_to_day(value, edge=constants.LEFT_EDGE):
    return align_to(value, edge=edge, mode=constants.ALIGN_DAY)


def align_to_week(value, edge=constants.LEFT_EDGE):
    return align_to(value, edge=edge, mode=constants.ALIGN_WEEK)


def align_to_month(value, edge=constants.LEFT_EDGE):
    return align_to(value, edge=edge, mode=constants.ALIGN_MONTH)


def align_to_year(value, edge=constants.LEFT_EDGE):
    return align_to(value, edge=edge, mode=constants.ALIGN_YEAR)


def next_nth_of_month(nth, from_date):
    """
    Return the next instance of the nth day of the month relative to a specific date.
    Returns same month if before nth day and next month if after.
    Returns last day of next month if nth day exceeds next months length
    :param nth:
    :param from_date:
    :return:
    """

    if from_date.day < nth:
        return date(from_date.year, from_date.month, nth)
    else:
        next_month = from_date + relativedelta(months=1)
        return next_month.replace(day=min(nth, monthrange(next_month.year, next_month.month)[1]))


def date_edges(start_date, end_date=None):
    if end_date is None:
        end_date = start_date

    return align_to_day(start_date, constants.LEFT_EDGE), align_to_day(end_date, constants.RIGHT_EDGE)


def duration_to_unit_hours(duration, decimal_places=None):
    if duration is None:
        return Decimal(0)

    result = Decimal(duration.total_seconds()) / Decimal(3600)

    if decimal_places is None:
        return result
    else:
        return round(result, decimal_places)


def duration_to_rounded_unit_hours(duration, decimal_places=None, rounding_step=None, rounding_mode=None):
    if duration is None:
        return Decimal('0.0')

    unit_hours = duration_to_unit_hours(duration, decimal_places=decimal_places)

    if rounding_step is None or rounding_mode is None:
        return unit_hours
    elif rounding_mode == constants.ROUNDING_MODE_FLOOR:
        remainder = unit_hours % rounding_step

        if remainder == Decimal(0):
            return unit_hours
        else:
            return unit_hours - remainder
    elif rounding_mode == constants.ROUNDING_MODE_CEILING:
        remainder = unit_hours % rounding_step

        if remainder == Decimal(0):
            return unit_hours
        else:
            return unit_hours + (rounding_step - remainder)
    elif rounding_mode == constants.ROUNDING_MODE_STANDARD:
        fraction = Decimal('1.0') / rounding_step

        return round(unit_hours * fraction) / fraction

    raise ValueError('Invalid rounding mode: {}'.format(rounding_mode))
