from calendar import monthrange
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

    if mode == constants.ALIGN_DAY:
        new_date = value.date()
    elif mode == constants.ALIGN_WEEK:
        start_date = value.date()

        if edge == constants.LEFT_EDGE:
            new_date = start_date - timedelta(days=start_date.isoweekday() - 1)
        else:
            new_date = start_date + timedelta(days=7 - start_date.isoweekday())
    elif mode == constants.ALIGN_MONTH:
        if edge == constants.LEFT_EDGE:
            new_date = value.date().replace(day=1)
        else:
            new_date = value.date().replace(day=monthrange(value.year, value.month)[1])
    else:
        if edge == constants.LEFT_EDGE:
            new_date = value.date().replace(month=1, day=1)
        else:
            new_date = value.date().replace(month=12, day=31)

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

    if value.tzinfo is None:
        return result
    else:
        return value.tzinfo.localize(result)


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
