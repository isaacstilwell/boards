import asyncio
from datetime import date, datetime
from enum import Enum
import logging
import random
import re
from typing import Dict, Literal, Tuple

import httpx
from bs4 import BeautifulSoup, Tag
from urllib.parse import ParseResult, urlparse, parse_qs

from .base import BaseScraper, ScrapedThread
from .helpers import extract_dates
from .expressions import (
    keyboard_keywords_re,
    keycap_keywords_re,
    instock_keywords_re,
    currency_tokens_re,
    price_re,
    months_re,
)


class SubBoard(Enum):
    """
    Enum mapping meaningful names to subboard ids in GH
    """

    GROUP_BUYS = 70
    INTEREST_CHECKS = 132  # to be implemented later, not necessary for MVP


class GHScraper(BaseScraper):
    """
    Scraper for GeekHack.

    Basic flow:
    - access first page of groupbuy threads
    - extract all links from inside the table of listings that have [<type>] in
    the title
    - access each thread at each link and extract thread info

    NOTE: many methods use assert isinstance(var, Tag). This is primarily to
    avoid typing errors, but I only use assert in areas where there would be no
    point scraping anything if the assert fails
    """

    async def fetch(self) -> list[ScrapedThread]:
        """
        Asynchronously extracts threads for from the groupbuy section of GH

        Returns
            threads: list[ScrapedThread]
                list of ScrapedThread objects to be written to the DB as Threads
        """

        thread_urls = await self._extract_thread_urls()
        threads: list[ScrapedThread] = []
        for url in thread_urls:
            try:
                thread = await self._extract_thread(url)
                threads.append(thread)
            except Exception as e:
                BaseScraper.log(url, e)
            await BaseScraper.sleep()

        return threads

    async def _extract_thread_urls(self) -> list[str]:
        """
        Extracts a list of links to each item listing from the first page of the
        groupbuys board

        Returns
            thread_urls (list[str]):
                list of urls to individual GB threads on GH
        """

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.forum_url}/index.php?board={SubBoard.GROUP_BUYS.value}.0"
            )
            soup = BeautifulSoup(resp.text, "html.parser")
            thread_urls = []
            main_content = soup.find("div", class_="topic_table")
            assert isinstance(main_content, Tag)

            thread_items = main_content.find_all("tr")
            for ti in thread_items:
                subj = ti.find("td", class_="subject")
                # relevant listings always start with [GB], [Pre-Order], or
                # another [<status>] tag otherwise we skip them
                if subj and (thread_link := subj.find("a")).text[0] == "[":
                    thread_urls.append(thread_link["href"])
            return thread_urls

    def _extract_thread_title(self, title: str) -> str:
        """
        Extracts a clean title from the full string in the HTML <title>
        attribute of a GH thread

        Parameters
            title: str
                the full string in the <title> element

        Returns
            clipped_title: str
                the cleaned title of the thread to be used as the thread title
        """

        # the thread should have a "] " in the title, which we want to avoid
        if len(title_split := re.split(r"] ?", title)) > 1:
            # some titles include non-title names after (e.g., "- An
            # Olivetti-inspired set"). we want to clip this
            clipped_title = re.split(r" ?[|\-–—(]", title_split[1])[0]
        else:
            # if the thread somehow doesn't have "] ", just fallback to the
            # whole title
            clipped_title = title

        return clipped_title

    def _extract_thread_item_type(
        self, title: str
    ) -> Literal["keyboard", "keycaps", "unknown"]:
        """
        Tries to match a number of keywords in the title and picks the type that
        had the higher number of keywords.

        The title is the most efficient way to find the type without matching
        the full body of a post, which is much more expensive.

        Parameters
            title: str
                the full string in the <title> element

        Returns
            item_type (Literal["keyboard", "keycaps", "unknown"]):
                type of item this title is for
        """

        keycap_score = len(keycap_keywords_re.findall(title))
        keyboard_score = len(keyboard_keywords_re.findall(title))

        if keycap_score >= 1 and keycap_score - keyboard_score >= 1:
            item_type = "keycaps"
        elif keyboard_score >= 1 and keyboard_score - keycap_score >= 1:
            item_type = "keyboard"
        else:
            item_type = "unknown"
        return item_type

    def _extract_thread_type(
        self, title: str, start_date: date | None, end_date: date | None
    ) -> Literal["instock", "upcoming", "active", "completed"] | None:
        """
        Uses the thread title and the dates to determine if the thread is
        for an in-stock item, upcoming GB, active GB, or completed GB.

        Parameters
            title: str
                the full string in the <title> element
            start_date: date | None
                the date determined as the strating date from the scrape, or
                None if no date was determined
            end_date: date | None
                the date determined as the ending date from the scrape, or
                None if no date was determined

        Returns
            (Literal["instock", "upcoming", "active", "completed"] | None):
                stock type of this thread. None if indeterminate.
        """

        if instock_keywords_re.search(title):
            return "instock"

        if start_date and end_date:
            if start_date <= (now := datetime.now().date()) and end_date > now:
                return "active"
            elif start_date > now:
                return "upcoming"
            else:
                return "completed"

        return None

    def _extract_price_info(self, post: Tag) -> Tuple[str | None, float | None]:
        """
        Extracts the price of an item from the HTML body of a GH thread.

        Parameters
            post: (bs4) Tag
                the full bs4 tag associated with the body of the thread

        Returns
            (currency, price): Tuple(str | None, float | None)
                the 3-char currency abbreviation and the decimal cost of the item
        """

        currency_elements = post.find_all(string=currency_tokens_re)
        currency = None
        price = None

        for currency_element in currency_elements:
            # extract the number + symbol from the whole text (sometimes in a
            # huge block)
            match = price_re.search(currency_element.text)
            if match:
                currency_string = match.group()
                # match first index with $/€/£ and convert to a currency string
                match currency_string[0]:
                    case "$":
                        currency = "USD"
                    case "€":
                        currency = "EUR"
                    case "£":
                        currency = "GBP"

                # extract price from the remaining string after removing "," if
                # necessary
                price = float(currency_string[1:].replace(",", ""))
                break
        return (currency, price)

    def _extract_dates(
        self, post: Tag, post_date: date
    ) -> Tuple[date | None, date | None]:
        """
        Extracts the dates of a GB from the HTML body of a GH thread.

        Parameters
            post: (bs4) Tag
                the full bs4 tag associated with the body of the thread

        Returns
            (start_date, end_date): Tuple(date | None, date | None)
                the dates associated with the starting and ending dates of a GB.
                None if invalid.
        """

        # search for elements that have month strings
        selected_month_text = ""
        selected_months = []

        # goal is to find a string that contains exactly two months, since this
        # is almost always a date range in GH (i.e., sept 20, 2026 - oct 20, 2026)
        for month_element in post.find_all(string=months_re):
            match len(month_strings := months_re.findall(month_element.text)):
                case 1 if len(selected_months) < 1:
                    # update the final text block to search, but continue
                    # searching for 2 month combo
                    selected_months = month_strings
                    selected_month_text = month_element.text
                case 2:
                    # break if 2 months found
                    selected_months = month_strings
                    selected_month_text = month_element.text
                    break
                case _:
                    # >2 months found is impossible to get any info from. no
                    # need to update for 1 month if selected_months already has
                    # 1 month
                    continue
        return extract_dates(selected_month_text, fallback_date=post_date)

    async def _extract_thread(self, url: str) -> ScrapedThread:
        """
        Given a url, extracts ScrapedThread object containing info about the GH
        thread found at the given URL

        Parameters:
            url: str
                tracked link to the GH thread to be extracted

        Returns:
            ScrapedThread
                the ScrapedThread object representing this GB post
        """

        async with httpx.AsyncClient() as client:
            # GH assigns the asyncclient a session id, which causes messy
            # lookups in the DB, so remove it for the url we pass to the db
            queries = parse_qs(urlparse(url).query)
            topic = queries["topic"][0]
            untracked_link = f"{self.forum_url}/index.php?topic={topic}"

            # get url with tracked link, otherwise it doesn't work
            resp = await client.get(url)
            soup = BeautifulSoup(resp.text, "html.parser")

            title_attr = soup.find("title")
            assert isinstance(title_attr, Tag)
            title = title_attr.text
            clipped_title = self._extract_thread_title(title)
            item_type = self._extract_thread_item_type(title)

            # the first postarea always contains the date the thread was posted
            postarea = soup.find("div", class_="postarea")

            # post date is always in the same pattern:
            # "« on: DAYNAME, DAY MONTH YEAR, 05:31:58 »"
            post_date_tag = (
                postarea.find("div", class_="smalltext")
                if isinstance(postarea, Tag)
                else None
            )
            post_date_string = (
                post_date_tag.text.split(", ")[1]
                if isinstance(post_date_tag, Tag)
                else None
            )
            post_date = (
                datetime.strptime(post_date_string, "%d %B %Y").date()
                if post_date_string
                else date.today()
            )

            post_wrapper = soup.find("div", class_="post_wrapper")
            assert isinstance(post_wrapper, Tag)

            # the first post_wrapper > poster class always contains the thread
            # author
            poster_info = post_wrapper.find("div", class_="poster")
            author_header = (
                poster_info.find("h4") if isinstance(poster_info, Tag) else None
            )
            author_anchor = (
                author_header.find("a") if isinstance(author_header, Tag) else None
            )
            author = author_anchor.text if isinstance(author_anchor, Tag) else None

            # we always want the first post class in a thread
            post = post_wrapper.find("div", class_="post")
            assert isinstance(post, Tag)

            # getting image links by searching for all img tags
            # cannot fail because we have a find_all. if no images, we just
            # get an empty array
            image_links = []
            images = post.find_all("img", class_="bbc_img")
            for image in images:
                image_links.append(image["src"])

            # get the vendors by comparing the home url of bbc links in the
            # thread cannot fail because we're using find_all
            vendors = []
            bbc_links = post.find_all("a", class_="bbc_link")
            for bbc in bbc_links:
                # extract home url and check against vendor_map
                parsed_url: ParseResult = urlparse(bbc["href"])
                if (
                    vendor_link := f"{parsed_url.scheme}://{parsed_url.netloc}/"
                ) in self.vendor_map:
                    vendors.append(self.vendor_map[vendor_link])

            currency, price = self._extract_price_info(post)

            start_date, end_date = self._extract_dates(post, post_date)
            thread_type = self._extract_thread_type(title, start_date, end_date)

            return ScrapedThread(
                title=clipped_title,
                designer=author,
                external_url=untracked_link,
                image_urls=image_links,
                vendors=vendors,
                currency=currency,
                price=price,
                item_type=item_type,
                thread_type=thread_type,
                post_date=post_date,
                start_date=start_date,
                end_date=end_date,
            )
