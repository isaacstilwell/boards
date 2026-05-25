from datetime import datetime
from typing import List

from bs4 import BeautifulSoup, Tag
import httpx

from .base import BaseScraper, ScrapedThread, ItemType
from .helpers import extract_dates
from .expressions import designed_by_re


class DKScraper(BaseScraper):
    """
    Scraper for Divinikey.

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
            collection = (
                "keycap-sets" if item_type == ItemType.KEYCAPS else "keyboard-kits"
            )
            resp = await client.get(
                f"{self.forum_url}/collections/{collection}?sort_by=created-descending"
            )
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("li", class_="js-pagination-result")
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

            # title always "<name> - Divinikey"
            title_attr = soup.find("title")
            # if there's no title tag at all, something is deeply wrong
            assert isinstance(title_attr, Tag)
            title = (
                title_attr.text.replace("\n", " ")
                .replace("\u2013", "-")
                .split(" - ")[0]
            )

            # DK sometimes includes authors in text like "Designed by <Name>".
            # they are always in product-description blocks, which there is only
            # one of
            designer = None
            if isinstance(
                product_description := soup.find("div", class_="product-description"),
                Tag,
            ):
                if isinstance(
                    text_element := product_description.find(string=designed_by_re), Tag
                ):
                    match = designed_by_re.search(text_element.text)
                    designer = match.groups()[0] if match else None

            # extract all images from the thumbnail grid
            thumbnails = soup.find("div", class_="media-gallery__thumbs")
            # replace leading "//" to make them proper links, and remove &width
            # to get full size images
            image_links = (
                [
                    f"https://{img['src'].replace('//', '').split('&width')[0]}"
                    for img in thumbnails.find_all("img")
                ]
                if isinstance(thumbnails, Tag)
                else []
            )

            # DK rarely puts sister vendors, and it avoids using their links
            # when it does. too much work to manually parse vendors in their
            # format, so just put DK as the sole vendor
            vendors = ["Divinikey"]

            # DK is american
            currency = "USD"

            price_container = soup.find("div", class_="product-price")
            if isinstance(price_container, Tag) and (
                isinstance(
                    price_element := price_container.find("span", class_="js-value"),
                    Tag,
                )
            ):
                price_text = price_element.text.replace(",", "").replace("$", "")
                price = float(price_text)
            else:
                price = None

            # threads that don't have labels are always in stock on DK
            thread_type = "instock"
            product_label_container = soup.find("div", class_="product-label-container")
            if isinstance(product_label_container, Tag) and (
                product_labels := product_label_container.find_all("span")
            ):
                # there are only multiple labels if sold out, and sold out is
                # always the last label
                thread_type_text = product_labels[-1].text.lower()

                # check for out of stock first, because all other forms of stock
                # are instock
                if "sold out" in thread_type_text:
                    thread_type = "completed"
                # check for open pre-orders and groupbuys
                elif "pre-order" in thread_type_text or "groupbuy" in thread_type_text:
                    thread_type = "active"

            # use today's date because it will only be added on thread creation,
            # and it's likely that the first time a thread is scraped is near
            # when it was created
            post_date = datetime.now().date()

            start_date = None
            end_date = None
            if info_block := soup.find(
                "span", class_="metafield-multi_line_text_field"
            ):
                date_label = info_block.text.split("\n")[0]
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
