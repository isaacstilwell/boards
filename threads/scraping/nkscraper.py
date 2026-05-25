import asyncio
from datetime import datetime
from enum import Enum
import re
from typing import List, Tuple

from bs4 import BeautifulSoup, Tag
import httpx

from .base import BaseScraper, ScrapedThread, ItemType
from .helpers import extract_dates


class NKScraper(BaseScraper):
    """
    Scraper for NovelKeys.

    Basic flow:
    - access first page of keyboard/keycap listings
    - extract all prices and links from inside the grid of listings
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

        # these are awaited in order because we don't want to be making multiple
        # calls at once
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

        link_price_objects = await self._extract_thread_links_and_prices(item_type)

        # partial because it returns the relative string
        # (full link == self.forum_url/{partial}) we get the price at this stage
        # because the thread requires a selector to show the price
        threads = []
        for partial, price in link_price_objects:
            try:
                thread = await self._extract_thread(partial, price, item_type)
                threads.append(thread)
            except Exception as e:
                BaseScraper.log(f"{self.forum_url}{partial}", e)
            await BaseScraper.sleep()
        return threads

    async def _extract_thread_links_and_prices(
        self, item_type: ItemType
    ) -> List[Tuple[str, float | None]]:
        """
        Given an item type, extracts a list of price-link pairs for each item
        listing from the first page of the site, sorted by newest.

        Parameters:
            item_type: ItemType
                type of item to extract listings for

        Returns:
            List[Tuple[str, float | None]]
                a list of (price-link) pairs for all listings on the first page
        """

        async with httpx.AsyncClient() as client:
            collection = "keycaps" if item_type == ItemType.KEYCAPS else "keyboards"

            resp = await client.get(
                f"{self.forum_url}/collections/{collection}?sort_by=created-descending"
            )
            soup = BeautifulSoup(resp.text, "html.parser")

            cards = soup.find_all("div", class_="product-card__quick-add-wrapper")

            output = []
            for card in cards:
                anchor = card.find("a", recursive=False)
                if not anchor:
                    continue
                href = anchor["href"]
                price_div = anchor.find("div", class_="price")

                # when item on sale, there's a child span that contains the sale
                # price, otherwise it's just the parent div
                price_span = price_div.find("span", class_="price")
                price_element = price_span if price_span else price_div

                # remove spaces and newlines to get in $xxx,xxx form then remove
                # commas and "$" for float conversion
                if isinstance(price_element, Tag):
                    price_text = (
                        price_element.text.strip()
                        .replace("\n", "")
                        .replace(",", "")
                        .replace("$", "")
                    )
                    price = float(price_text)
                else:
                    price = None
                output.append((href, price))
            return output

    async def _extract_thread(
        self, url: str, price: float | None, item_type: ItemType
    ) -> ScrapedThread:
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

            configurator_element = soup.find("div", class_="product-configurator")
            configurator_state = True if configurator_element else False

            # title always "<name> - NovelKeys LLC" or "<name>\n- NovelKeys LLC"
            # they sometimes use the u2013 dash instead of the normal dash, so
            # just try to convert since it's a common pattern
            title_attr = soup.find("title")
            # if there's no title tag at all, something is deeply wrong
            assert isinstance(title_attr, Tag)
            title = (
                title_attr.text.replace("\n", " ")
                .replace("\u2013", "-")
                .split(" - ")[0]
            )

            # NK doesnt have authors
            author = None

            # extract all images from the thumbnail grid
            thumbnail_grid = soup.find(
                "div",
                class_="product-thumbnails" if configurator_state else "thumbnail-grid",
            )
            # replace leading "//" to make them proper links
            image_links = (
                [
                    f"https://{anchor['href'].replace('//', '')}"
                    for anchor in thumbnail_grid.find_all(
                        "a",
                        class_="product-thumbnail"
                        if configurator_state
                        else "product-single__thumbnail",
                    )
                ]
                if isinstance(thumbnail_grid, Tag)
                else []
            )

            # vendors are in unclassed panels, so get all the panels and extract
            # all the links and validate with vendor_map. also start with
            # novelkeys becuase we're scraping the site
            vendors = ["NovelKeys"]
            panels = soup.find_all("div", class_="panel")
            for panel in panels:
                panel_links = [anchor["href"] for anchor in panel.find_all("a")]
                vendors.extend(
                    [
                        self.vendor_map[link]
                        for link in panel_links
                        if link in self.vendor_map
                    ]
                )

            # NK is american
            currency = "USD"

            product_flag = soup.find(id="product-flag")
            if product_flag:
                abbr = product_flag.find("abbr")
                if isinstance(abbr, Tag) and (
                    "stock" in (thread_type_text := abbr.text.lower())
                    or "clearence" in thread_type_text
                ):
                    thread_type = "instock"
                elif "preorder" in thread_type_text:
                    thread_type = "active"
                else:
                    thread_type = "completed"
            else:
                thread_type = None

            # NK doesn't make post dates available. use today for the post date,
            # leveraging the fact that we only pass post_date when creating a
            # new thread, not updating an existing one
            post_date = datetime.now().date()

            # try to extract an end_date (only occurs sometimes)
            end_wrapper = soup.find("div", class_="product-product-flag-details")

            if end_wrapper:
                start_date, end_date = extract_dates(end_wrapper.text)
            else:
                start_date, end_date = (None, None)

            return ScrapedThread(
                title=title,
                designer=author,
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
