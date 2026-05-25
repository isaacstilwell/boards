import pytest

from .ghscraper import GHScraper
from datetime import date


@pytest.fixture
def scraper():
    return GHScraper("https://geekhack.org")


@pytest.mark.parametrize(
    "title, expected",
    [
        ("[GB] GMK Gregory 2", "GMK Gregory 2"),
        ("[GB] Osidian TKL V2 | Sept 15 - Oct 15", "Osidian TKL V2"),
        ("[GB]GMK CYL Thunder God - May 22 - Jun 15 2026", "GMK CYL Thunder God"),
        ("[GB] DCS 9009 Fix Kit (December 10th 25-Jan 11th 26)", "DCS 9009 Fix Kit"),
        ("[GB] S46 R3 — 40% Wireless Keyboard Kit | Refined Tri-Mode, Clean", "S46 R3"),
        (
            "[GB] DIVERSITY—A multi-layout keyboard inspired by original Cherry style",
            "DIVERSITY",
        ),
        ("[GB]篆Seal TKL - The GB will be launched on March 23rd!", "篆Seal TKL"),
    ],
)
def test_extract_thread_title(scraper, title, expected):
    assert scraper._extract_thread_title(title) == expected


@pytest.mark.parametrize(
    "title, expected",
    [
        ("[GB] GMK Gregory 2", "keycaps"),
        ("[GB] Osidian TKL V2 | Sept 15 - Oct 15", "keyboard"),
        ("[GB]GMK CYL Thunder God - May 22 - Jun 15 2026", "keycaps"),
        ("[GB] DCS 9009 Fix Kit (December 10th 25-Jan 11th 26)", "keycaps"),
        (
            "[GB] S46 R3 — 40% Wireless Keyboard Kit | Refined Tri-Mode, Clean",
            "keyboard",
        ),
        (
            "[GB] DIVERSITY—A multi-layout keyboard inspired by original Cherry style",
            "keyboard",
        ),
        ("[GB]篆Seal TKL - The GB will be launched on March 23rd!", "keyboard"),
        (
            "[GB] Sho66, SRX, SR1 by Sho (2026 Rerun) - Cases for FC660C, Realforce R1 & R2",
            "unknown",
        ),
    ],
)
def test_extract_thread_item_type(scraper, title, expected):
    assert scraper._extract_thread_item_type(title) == expected


@pytest.mark.parametrize(
    "title, start, end, expected",
    [
        (
            "[In-stock] GMK CYL Quaderno - An Olivetti-Inspired Set",
            None,
            None,
            "instock",
        ),
        (
            "[GB] Osidian TKL V2 | Sept 15 - Oct 15",
            date(2025, 9, 15),
            date(2025, 10, 15),
            "completed",
        ),
        (
            "[GB]GMK CYL Thunder God - May 22 - Jun 15 2026",
            date(2026, 5, 22),
            date(2026, 6, 15),
            "active",
        ),
        (
            "[GB] DCS 9009 Fix Kit (December 10th 25-Jan 11th 26)",
            date(2025, 12, 10),
            date(2026, 1, 11),
            "completed",
        ),
        (
            "[GB] S46 R3 — 40% Wireless Keyboard Kit | Refined Tri-Mode, Clean",
            date(2026, 4, 27),
            date(2026, 5, 17),
            "completed",
        ),
        (
            "[GB] DIVERSITY—A multi-layout keyboard inspired by original Cherry style",
            None,
            None,
            None,
        ),
        (
            "[GB]篆Seal TKL - The GB will be launched on March 23rd!",
            date(2026, 7, 24),
            date(2025, 8, 24),
            "upcoming",
        ),
    ],
)
def test_extract_thread_type(scraper, title, start, end, expected):
    assert scraper._extract_thread_type(title, start, end) == expected
