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
    KEYBOARD = "keyboard"
    KEYCAPS = "keycaps"

class BaseScraper(ABC):
    with open("threads/scraping/vendors.json", "r") as f:
        vendors = json.load(f)
    vendor_map = {v["url"] : v["name"] for v in vendors}

    def __init__(self, forum_url: str):
        super().__init__()
        self.results: List[ScrapedThread] = []
        self.forum_url = forum_url

    @abstractmethod
    async def fetch(self) -> List[ScrapedThread]:
        ...

    @staticmethod
    def write(threads: List[ScrapedThread]):
        for thread in threads:
            Thread.objects.update_or_create(
                external_url=thread.external_url,
                defaults={
                    "title": thread.title,
                    "designer": thread.designer,
                    "external_url": thread.external_url,
                    "primary_image_url": thread.image_urls[0] if thread.image_urls else "",
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
                    "primary_image_url": thread.image_urls[0] if thread.image_urls else "",
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
                }
            )

    @staticmethod
    async def sleep():
        await asyncio.sleep(random.uniform(8,15))

    @staticmethod
    def log(url: str, error: Exception):
        logging.error(f"{url}: {str(error)}")

    async def run(self) -> bool:
        self.results = await self.fetch()
        await sync_to_async(self.write)(self.results)
        return True