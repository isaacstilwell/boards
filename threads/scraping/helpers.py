from datetime import date, datetime
import re
from typing import Literal, Tuple
from .expressions import months_re, dates_re


def extract_dates(
    text: str, *, single_date_start: bool = False, fallback_date: date | None = None
) -> Tuple[date | None, date | None]:
    """
    Extracts start and end dates from a block of text

    Parameters
        text: str
            block of text to extract dates from
        single_date_start: bool
            whether to mark date as start date if only one date is found
        fallback_date: date
            fallback date to use as a start date and year if only one date is
            found and/or if no years are found

    Returns
        Tuple[date | None, date | None]
            tuple of (start_date, end_date) found in the text. None if not found
            or invalid dates
    """

    fallback_date_provided = True if fallback_date else False
    if not fallback_date:
        fallback_date = datetime.now().date()

    if (number_dates := dates_re.findall(text)) and len(number_dates) <= 2:
        split_dates = [
            [int(num) for num in re.split(r"[/.\-]", date)] for date in number_dates
        ]

        # force years to YYYY format
        # this will break if this app is still alive in years 3000 and onward,
        # but that's a problem for later...
        year = None
        for date in split_dates:
            if len(date) == 3:
                if date[-1] < 1000:
                    date[-1] += 2000
                year = date[-1]

        # complete all years
        for date in split_dates:
            if len(date) < 3:
                date.append(year if year else fallback_date.year)

        first_date = _safe_strptime(
            split_dates[0][0], split_dates[0][1], split_dates[0][2]
        )
        if len(split_dates) == 1:
            return (first_date, None) if single_date_start else (None, first_date)
        else:
            second_date = _safe_strptime(
                split_dates[1][0], split_dates[1][1], split_dates[1][2]
            )
            return (first_date, second_date)

    elif (selected_months := months_re.findall(text)) and len(selected_months) <= 2:
        numbers = [int(n) for n in re.findall(r"\d+", text)]
        days = [n for n in numbers if n <= 31]
        years = [n for n in numbers if n > 31]

        # try to add fallback date if provided and valid
        if not years:
            years = [fallback_date.year]
        if fallback_date_provided and len(days) == 1 and fallback_date.day < days[0]:
            days = [fallback_date.day] + days

        # overloaded dates; can't make accurate parse, so just exit. better to
        # have no info than wrong info, and this is likely to be wrong
        if not days or len(days) > 2 or len(years) > 2:
            return (None, None)

        first_date = _safe_strptime(selected_months[0][:3].lower(), days[0], years[0])

        if len(days) == 1:
            return (first_date, None) if single_date_start else (None, first_date)
        else:
            second_date = _safe_strptime(
                selected_months[-1][:3].lower(), days[1], years[-1]
            )
            return (first_date, second_date)
    else:
        return (None, None)


def _safe_strptime(month: str | int, day: int, year: int) -> date | None:
    """
    Wraps datetime.strptime to return None for invalid dates

    Parameters
        month: str | int
            3 letter abbreviation for, or number of month
        day: int
            date number
        year: int
            year number

    Returns
        date | None
            parsed date if valid, None otherwise
    """

    month_type = "word" if isinstance(month, str) else "number"
    try:
        return datetime.strptime(
            f"{month} {day} {year}", "%b %d %Y" if month_type == "word" else "%m %d %Y"
        ).date()
    except ValueError:
        return None
