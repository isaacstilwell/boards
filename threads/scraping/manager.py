import asyncio
import logging
from typing import List
from .base import BaseScraper
from .ckscraper import CKScraper
from .nkscraper import NKScraper
from .dkscraper import DKScraper
from .ghscraper import GHScraper


class ScraperManager():
    def __init__(self):
        self.scrapers: List[BaseScraper] = [
            CKScraper("https://cannonkeys.com"),
            NKScraper("https://novelkeys.com"),
            DKScraper("https://divinikey.com"),
            GHScraper("https://geekhack.org"),
        ]

    async def scrape(self):
        tasks = [scraper.run() for scraper in self.scrapers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        exceptions = [r for r in results if isinstance(r, Exception)]
        for e in exceptions:
            logging.error(str(e))

