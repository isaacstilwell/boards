import asyncio
import logging
from typing import List
from .base import BaseScraper
from .ckscraper import CKScraper
from .nkscraper import NKScraper
from .dkscraper import DKScraper
from .ghscraper import GHScraper


class ScraperManager:
    """
    Manager for all scrapers
    """

    def __init__(self):
        """
        Instantiates all of the scrapers and provides them with links
        """
        self.scrapers: List[BaseScraper] = [
            CKScraper("https://cannonkeys.com"),
            NKScraper("https://novelkeys.com"),
            DKScraper("https://divinikey.com"),
            GHScraper("https://geekhack.org"),
        ]

    async def scrape(self):
        """
        Called .run() on each scraper and awaits all runs together asynchronously

        Returns
            None
        """
        tasks = [scraper.run() for scraper in self.scrapers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        exceptions = [r for r in results if isinstance(r, Exception)]
        for e in exceptions:
            logging.error(str(e))
