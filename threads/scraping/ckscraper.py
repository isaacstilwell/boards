import asyncio
from datetime import date, datetime
from enum import Enum
import logging
import re
from typing import List, Tuple

from bs4 import BeautifulSoup, Tag
import httpx

from .base import BaseScraper, ScrapedThread, ItemType
from .helpers import extract_dates
from .expressions import designed_by_re


class CKScraper(BaseScraper):
    """
    Scraper for CannonKeys.

    Basic flow:
    - access first page of keyboard/keycap listings
    - extract all links from inside the grid of listings
    - access each listing at each link and extract thread info
    """

    async def fetch(self) -> List[ScrapedThread]:
        """
        Asynchronously extracts threads for keycap and keyboard pages on the
        site. Does not process in parallel to prevent rate limiting.

        Returns
            threads: list[ScrapedThread]
                list of ScrapedThread objects to be written to the DB as Threads
        """

        keyboard_threads = await self._get_threads(ItemType.KEYBOARD)
        keycap_threads = await self._get_threads(ItemType.KEYCAPS)
        return keyboard_threads + keycap_threads

    async def _get_threads(self, item_type: ItemType) -> List[ScrapedThread]:
        """
        Given an item type, extracts a list of ScrapedThread objects associated
        with items of that type on the first page of the site, sorted by newest.

        Parameters:
            item_type: ItemType
                type of item to scrape

        Returns:
            List[ScrapedThread]
                list of ScrapedThread objects to be written to the DB as Threads
        """

        links = await self._extract_thread_links(item_type)

        # partial because it returns the relative string
        # (full link == self.forum_url/{partial})
        threads = []
        for partial in links:
            try:
                thread = await self._extract_thread(partial, item_type)
                # CK gives an abnormal amount of bad responses, but i dont think
                # it has to do with blocking connections... just skip the thread
                # if it goes wrong, and it'll probably get scraped in the next
                # rotation
                if thread.title != "Something went wrong":
                    threads.append(thread)
            except Exception as e:
                BaseScraper.log(f"{self.forum_url}{partial}", e)

            await BaseScraper.sleep()
        return threads

    async def _extract_thread_links(self, item_type: ItemType) -> List[str]:
        """
        Given an item type, extracts a list of links to each item listing from
        the first page of the site, sorted by newest.

        Parameters:
            item_type: ItemType
                type of item to extract listings for

        Returns:
            List[str]
                a list of item links for all listings on the first page
        """

        async with httpx.AsyncClient() as client:
            collection = "keycaps" if item_type == ItemType.KEYCAPS else "keyboards"
            resp = await client.get(
                f"{self.forum_url}/collections/{collection}?sort_by=created-descending"
            )
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("product-block")
            return [card.find("a")["href"] for card in cards]

    async def _extract_thread(self, url: str, item_type: ItemType) -> ScrapedThread:
        """
        Given a url and an item type, extracts ScrapedThread object containing
        info about the listing found at the given URL

        Parameters:
            url: str
                link to the listing to be extracted
            item_type: ItemType
                type of the listing

        Returns:
            ScrapedThread
                the ScrapedThread object representing this listing
        """

        async with httpx.AsyncClient() as client:
            link = f"{self.forum_url}{url}"

            resp = await client.get(link)
            soup = BeautifulSoup(resp.text, "html.parser")

            # title always "<name> - CannonKeys"
            title_attr = soup.find("title")
            # if there's no title tag at all, something is deeply wrong
            assert isinstance(title_attr, Tag)
            title = (
                title_attr.text.replace("\n", " ")
                .replace("\u2013", "-")
                .split(" - ")[0]
            )

            # CK sometimes includes authors in text like "Designed by <Name>".
            # they are always in rich-text blocks
            designer = None
            rt_sections = soup.find_all("div", class_="section-rich-text")

            for section in rt_sections:
                if isinstance(text_element := section.find(string=designed_by_re), Tag):
                    match = designed_by_re.search(text_element.text)
                    designer = match.groups()[0] if match else None
                    break

            # extract all images from the thumbnail grid
            thumbnails = soup.find("carousel-slider", class_="thumbnails")

            # replace leading "//" to make them proper links
            image_links = (
                [
                    f"https://{anchor['href'].replace('//', '')}"
                    for anchor in thumbnails.find_all("a", class_="thumbnail")
                ]
                if isinstance(thumbnails, Tag)
                else []
            )

            # vendors are in one of the accordions, but the specific accordion
            # has no more detail, so just read all accordions (there are only
            # 2-3) and check links against vendor_map also start with cannonkeys
            # becuase we're scraping the site
            vendors = ["CannonKeys"]
            accordions = soup.find_all("div", class_="product-info-accordion")
            for accordion in accordions:
                accordion_links = [anchor["href"] for anchor in accordion.find_all("a")]
                vendors.extend(
                    [
                        self.vendor_map[link]
                        for link in accordion_links
                        if link in self.vendor_map
                    ]
                )

            # CK is american
            currency = "USD"

            price_container = soup.find("div", class_="price-container")
            if isinstance(price_container, Tag) and (
                isinstance(
                    price_element := price_container.find(
                        "span", class_="price__current"
                    ),
                    Tag,
                )
            ):
                price_text = price_element.text.replace(",", "").replace("$", "")
                price = float(price_text)
            else:
                price = None

            thread_type = None
            product_label = soup.find("span", class_="product-label")
            if isinstance(product_label, Tag) and (
                isinstance(thread_type_span := product_label.find("span"), Tag)
            ):
                thread_type_text = thread_type_span.text.lower()
                # check for out of stock first, because all other forms of stock
                # are instock
                if (
                    "out of stock" in thread_type_text
                    or "completed" in thread_type_text
                ):
                    thread_type = "completed"
                # check for other types of stock
                elif "stock" in thread_type_text or "clearence" in thread_type_text:
                    thread_type = "instock"
                # check for coming soon and date flags (dates are only in future)
                elif "coming soon" in thread_type_text or "/" in thread_type_text:
                    thread_type = "upcoming"
                # check for open pre-orers and groupbuys
                elif "pre-order" in thread_type_text or "group buy" in thread_type_text:
                    thread_type = "active"

            # use today's date because it will only be added
            # on thread creation, and it's likely that the first time
            # a thread is scraped is near when it was created
            post_date = datetime.now().date()

            start_date = None
            end_date = None
            if isinstance(
                info_block := soup.find("div", class_="product-info-block"), Tag
            ):
                date_p = info_block.find("p")
                date_label = date_p.text if isinstance(date_p, Tag) else ""
                # CK dates are inconsistent and sometimes we'll have a 2 date
                # string, other times 1 date. a single date is usually an end
                # date unless the gb hasn't started yet, in which case it's the
                # start date
                start_date, end_date = extract_dates(
                    date_label, single_date_start=(thread_type == "upcoming")
                )

            return ScrapedThread(
                title=title,
                designer=designer,
                external_url=link,
                image_urls=image_links,
                vendors=vendors,
                currency=currency,
                price=price,
                item_type=item_type.value,
                thread_type=thread_type,
                post_date=post_date,
                start_date=start_date,
                end_date=end_date,
            )
