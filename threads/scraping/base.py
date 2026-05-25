from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass
from datetime import date
from enum import Enum
import logging
import random
from typing import List, Literal
import json

from asgiref.sync import sync_to_async

from threads.models import Thread


@dataclass
class ScrapedThread:
    """
    The ScrapedThread dataclass represents a thread extracted from a site by a
    subclass of BaseScraper. It is designed to map cleanly to a Thread from
    threads/models.py.
    """

    title: str
    designer: str | None
    external_url: str
    image_urls: List[str]
    vendors: List[str]
    currency: str | None
    price: float | None
    item_type: Literal["keyboard", "keycaps", "unknown"]
    thread_type: Literal["instock", "upcoming", "active", "completed"] | None
    post_date: date
    start_date: date | None
    end_date: date | None


class ItemType(Enum):
    """
    Enum representing the different item types being scraped. Used to avoid
    hardcoding values into the shopify scrapers that all have the same rough
    url construction.
    """

    KEYBOARD = "keyboard"
    KEYCAPS = "keycaps"


class BaseScraper(ABC):
    """
    ABC representing a scraper. All scrapers are capable of writing their own
    results to the Thread model, sleeping for a random time within a range,
    logging their errors, and running their full scrape -> write pipeline.

    Each scraper must implement the write() method individually.
    """

    # the vendor map maps vendor urls to vendor names. vendors.json is scraped
    # from https://www.alexotos.com/keyboard-vendor-list/
    with open("threads/scraping/vendors.json", "r") as f:
        vendors = json.load(f)
    vendor_map = {v["url"]: v["name"] for v in vendors}

    def __init__(self, forum_url: str):
        """
        Constructs an empty results object and adds the forum_url as an attribute

        Parameters
            forum_url: str
                the base url of the website that will be scraped
        """

        super().__init__()
        self.results: List[ScrapedThread] = []
        self.forum_url = forum_url

    @abstractmethod
    async def fetch(self) -> List[ScrapedThread]: ...

    @staticmethod
    def write(threads: List[ScrapedThread]):
        """
        Writes a list of ScrapedThread objects to the Thread model

        Parameters
            threads: List[ScrapedThread]
                a list of scraped threads to write to the model

        Returns
            None
        """

        for thread in threads:
            Thread.objects.update_or_create(
                external_url=thread.external_url,
                defaults={
                    "title": thread.title,
                    "designer": thread.designer,
                    "external_url": thread.external_url,
                    "primary_image_url": thread.image_urls[0]
                    if thread.image_urls
                    else "",
                    "image_urls": thread.image_urls,
                    "vendors": thread.vendors,
                    "currency": thread.currency,
                    "price": thread.price,
                    "item_type": thread.item_type,
                    "thread_type": thread.thread_type,
                    "start_date": thread.start_date,
                    "end_date": thread.end_date,
                    "status": "approved",
                },
                create_defaults={
                    "title": thread.title,
                    "designer": thread.designer,
                    "external_url": thread.external_url,
                    "primary_image_url": thread.image_urls[0]
                    if thread.image_urls
                    else "",
                    "image_urls": thread.image_urls,
                    "vendors": thread.vendors,
                    "currency": thread.currency,
                    "price": thread.price,
                    "item_type": thread.item_type,
                    "thread_type": thread.thread_type,
                    "post_date": thread.post_date,
                    "start_date": thread.start_date,
                    "end_date": thread.end_date,
                    "status": "approved",
                },
            )

    @staticmethod
    async def sleep():
        """
        Sleeps for between 8 and 15 seconds

        Returns
            None
        """

        await asyncio.sleep(random.uniform(8, 15))

    @staticmethod
    def log(url: str, error: Exception):
        """
        Logs the url of a listing that produced an error and the error itself.

        Parameters
            url: str
                the url of the listing with an error
            error: Exception
                the error that the scrape resulted in

        Returns
            None
        """

        logging.error(f"{url}: {str(error)}")

    async def run(self) -> bool:
        """
        Fetches all ScrapedThreads and writes them to the DB

        Returns
            None
        """

        self.results = await self.fetch()
        await sync_to_async(self.write)(self.results)
        return True
