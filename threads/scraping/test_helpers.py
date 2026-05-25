import pytest

from .helpers import extract_dates
from datetime import datetime, date

CURRENT_YEAR = datetime.now().year


@pytest.mark.parametrize(
    "text, single_date_start, fallback_date, expected",
    [
        ### with month names...
        # two dates, one year
        (
            "August 15 - December 16, 2028",
            False,
            None,
            (date(2028, 8, 15), date(2028, 12, 16)),
        ),
        # two years
        (
            "August 15, 2027 - December 16, 2028",
            False,
            None,
            (date(2027, 8, 15), date(2028, 12, 16)),
        ),
        # fallback date with no years
        (
            "August 15 - December 16",
            False,
            datetime.now().date(),
            (date(CURRENT_YEAR, 8, 15), date(CURRENT_YEAR, 12, 16)),
        ),
        # no fallback date with no years defaults to now
        (
            "August 15 - December 16",
            False,
            None,
            (date(CURRENT_YEAR, 8, 15), date(CURRENT_YEAR, 12, 16)),
        ),
        # single_date_start w/ 2 dates doesn't change anything
        (
            "August 15 - December 16",
            True,
            datetime.now().date(),
            (date(CURRENT_YEAR, 8, 15), date(CURRENT_YEAR, 12, 16)),
        ),
        (
            "August 15, 2027 - December 16, 2028",
            True,
            None,
            (date(2027, 8, 15), date(2028, 12, 16)),
        ),
        # 2 dates with abbr
        (
            "Aug 15 - Dec 16",
            False,
            datetime.now().date(),
            (date(CURRENT_YEAR, 8, 15), date(CURRENT_YEAR, 12, 16)),
        ),
        # 1 date
        (
            "December 16",
            False,
            datetime.now().date(),
            (None, date(CURRENT_YEAR, 12, 16)),
        ),
        # single_date_start
        (
            "December 16",
            True,
            datetime.now().date(),
            (date(CURRENT_YEAR, 12, 16), None),
        ),
        # poorly formatted dates
        (
            "Aug 15-Dec 16",
            False,
            datetime.now().date(),
            (date(CURRENT_YEAR, 8, 15), date(CURRENT_YEAR, 12, 16)),
        ),
        (
            "from Aug   15 through December 16 ",
            False,
            datetime.now().date(),
            (date(CURRENT_YEAR, 8, 15), date(CURRENT_YEAR, 12, 16)),
        ),
        (
            "Aug 15\nDec 16",
            False,
            datetime.now().date(),
            (date(CURRENT_YEAR, 8, 15), date(CURRENT_YEAR, 12, 16)),
        ),
        ### with compacted numeric format
        # two dates, one year
        ("8/15 - 12/16/2028", False, None, (date(2028, 8, 15), date(2028, 12, 16))),
        # two years
        (
            "8/15/2027 - 12/16/2028",
            False,
            None,
            (date(2027, 8, 15), date(2028, 12, 16)),
        ),
        # fallback date with no years
        (
            "8/15 - 12/16",
            False,
            datetime.now().date(),
            (date(CURRENT_YEAR, 8, 15), date(CURRENT_YEAR, 12, 16)),
        ),
        # no fallback date with no years defaults to now
        (
            "8/15 - 12/16",
            False,
            None,
            (date(CURRENT_YEAR, 8, 15), date(CURRENT_YEAR, 12, 16)),
        ),
        # single_date_start w/ 2 dates doesn't change anything
        (
            "8/15 - 12/16",
            True,
            datetime.now().date(),
            (date(CURRENT_YEAR, 8, 15), date(CURRENT_YEAR, 12, 16)),
        ),
        ("8/15/2027 - 12/16/2028", True, None, (date(2027, 8, 15), date(2028, 12, 16))),
        # 1 date
        ("12/16", False, datetime.now().date(), (None, date(CURRENT_YEAR, 12, 16))),
        # single_date_start
        ("12/16", True, datetime.now().date(), (date(CURRENT_YEAR, 12, 16), None)),
        # different formats
        (
            "8.15 - 12.16",
            False,
            datetime.now().date(),
            (date(CURRENT_YEAR, 8, 15), date(CURRENT_YEAR, 12, 16)),
        ),
        (
            "8-15 - 12-16",
            False,
            datetime.now().date(),
            (date(CURRENT_YEAR, 8, 15), date(CURRENT_YEAR, 12, 16)),
        ),
        (
            "08/15 - 12/16",
            False,
            datetime.now().date(),
            (date(CURRENT_YEAR, 8, 15), date(CURRENT_YEAR, 12, 16)),
        ),
        ("8/15/28 - 12/16/29", False, None, (date(2028, 8, 15), date(2029, 12, 16))),
    ],
)
def test_extract_dates(text, single_date_start, fallback_date, expected):
    assert (
        extract_dates(
            text, single_date_start=single_date_start, fallback_date=fallback_date
        )
        == expected
    )


@pytest.mark.parametrize(
    "text, single_date_start, fallback_date, expected",
    [
        ### with month names...
        # (from a real thread: https://geekhack.org/index.php?PHPSESSID=ste6gd3m9i75sa3s2j6idlqf9o5mei4n&topic=126412.0)
        ("25th Feb - 30th Feb 2026", False, None, (date(2026, 2, 25), None)),
        # no month but numbers
        (
            "John is 25 years old and he is born in 2003 and has 06 children",
            False,
            None,
            (None, None),
        ),
        # month but no numbers
        ("Januray February", False, None, (None, None)),
        ### with compacted numeric format
        # invalid separators
        ("8//2 9///25", False, None, (None, None)),
        # invalid dates
        ("8/50 - 12/75", False, None, (None, None)),
    ],
)
def test_invalid_dates(text, single_date_start, fallback_date, expected):
    assert (
        extract_dates(
            text, single_date_start=single_date_start, fallback_date=fallback_date
        )
        == expected
    )
