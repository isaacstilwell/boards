import asyncio
from datetime import date, datetime
from enum import Enum
import logging
import random
import re
from typing import Dict, Literal, Tuple

import httpx
from bs4 import BeautifulSoup, Tag
from .base import BaseScraper, ScrapedThread
from urllib.parse import ParseResult, urlparse, parse_qs
from .helpers import extract_dates

# GH uses PHP which uses meaningless numbers for the different subboards
class SubBoard(Enum):
    GROUP_BUYS = 70
    INTEREST_CHECKS = 132

class GHScraper(BaseScraper):
    async def fetch(self) -> list[ScrapedThread]:
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
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.forum_url}/index.php?board={SubBoard.GROUP_BUYS.value}.0")
            soup = BeautifulSoup(resp.text, "html.parser")
            thread_urls = []
            main_content = soup.find("div", class_="topic_table")
            thread_items = main_content.find_all("tr")
            for ti in thread_items:
                subj = ti.find("td", class_="subject")
                # relevant listings always start with [GB], [Pre-Order], or another [<status>] tag
                # otherwise we skip them
                if subj and (thread_link := subj.find("a")).text[0] == "[":
                    thread_urls.append(thread_link["href"])
            return thread_urls

    def _extract_thread_title(self, title) -> str:
        # the thread should have a "] " in the title, which we want to avoid
        if len(title_split := title.split("] ")) > 1:
            # some titles include non-title names after (e.g., "- An Olivetti-inspired set")
            # we want to clip this
            clipped_title = re.split(r" ?[|\-(]", title_split[1])[0]
        else:
            # if the thread somehow doesn't have "] ", just fallback to the whole title
            clipped_title = title

        return clipped_title

    def _extract_thread_item_type(self, title) -> Literal["keyboard", "keycaps", "unknown"]:
        # TODO: compile RE outside of func to improve performance since they're static
        keycap_keywords = re.compile(
            r"\b(?:"
            r"GMK|DSA|DSS|DCS|SA|G20|SP|JTK|DMK|EPBT|NicePBT|CYL|"
            r"MT3|KAT|KAM|KAS|DCX|PBT(?:fans)?|MW|CRP|SWG|SW|KKB|"
            r"set|keycaps?|keyset"
            r")\b",
            re.IGNORECASE
        )

        # TODO: compile outside
        keyboard_keywords = re.compile(
            r"\b(?:"
            r"(?:key)?board|TKL|full ?size|"
            r"40%?|60%?|65%?|70%?|75%?|80%?|98%?|"
            r"numpad|ergo"
            r")\b",
            re.IGNORECASE
        )
        # the title is the most efficient way to find the type. otherwise, we'd need to
        # pass the text of the entire post through the re, which is very inefficient
        keycap_score = len(keycap_keywords.findall(title))
        keyboard_score = len(keyboard_keywords.findall(title))

        # TODO use an enum
        if keycap_score >= 1 and keycap_score - keyboard_score >= 1:
            item_type = "keycaps"
        elif keyboard_score >= 1 and keyboard_score - keycap_score >= 1:
            item_type = "keyboard"
        else:
            item_type = "unknown"
        return item_type

    def _extract_thread_type(self, title: str, start_date: date | None, end_date: date | None) -> Literal["instock", "upcoming", "active", "completed"] | None:
        instock_keywords = re.compile(r"in(\-| )?stock",re.IGNORECASE)
        if instock_keywords.search(title):
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
        currency_elements = post.find_all(string=re.compile(r"(\$|€|£)"))
        currency = None
        price = None

        for currency_element in currency_elements:
            # extract the number + symbol from the whole text (sometimes in a huge block)
            currency_re = re.compile(r"(\$|€|£)((\d{1,3}(,\d{3})?|\d{1,6})(\.\d{2})?)")
            match = currency_re.search(currency_element.text)
            if match:
                currency_string = match.group()
                # match first index with $/€/£ and convert to a currency string
                match(currency_string[0]):
                    case "$":
                        currency = "USD"
                    case "€":
                        currency = "EUR"
                    case "£":
                        currency = "GBP"

                # extract price from the remaining string after removing "," if necessary
                price = float(currency_string[1:].replace(",", ""))
                break
        return (currency, price)

    def _extract_dates(self, post: Tag, post_date: date) -> Tuple[date | None, date | None]:
        # TODO: compile outside
        months = re.compile(
            r"\b(?:"
            r"Jan(?:uary)?|"
            r"Feb(?:ruary)?|"
            r"Mar(?:ch)?|"
            r"Apr(?:il)?|"
            r"May|"
            r"Jun(?:e)?|"
            r"Jul(?:y)?|"
            r"Aug(?:ust)?|"
            r"Sep(?:t(?:ember)?)?|"
            r"Oct(?:ober)?|"
            r"Nov(?:ember)?|"
            r"Dec(?:ember)?"
            r")\b\.?",
            re.IGNORECASE
        )

        # start_date = None
        # end_date = None

        # search for elements that have month strings
        selected_month_text = ""
        selected_months = []
        for month_element in post.find_all(string=months):
            match (len(month_strings := months.findall(month_element.text))):
                case 1 if len(selected_months) < 1:
                    # update the final text block to search, but continue searching for 2 month combo
                    selected_months = month_strings
                    selected_month_text = month_element.text
                case 2:
                    # break if 2 months found
                    selected_months = month_strings
                    selected_month_text = month_element.text
                    break
                case _:
                    # >2 months found is impossible to get any info from
                    # no need to update for 1 month if selected_months already has 1 month
                    continue
        return extract_dates(selected_month_text, fallback_date=post_date)


        # if len(month_elements) > 0:
        #     # if we find a match, we try to get something with 2 month strings
        #     # since this should always be something like "GB runs Mar 14 - Apr 14"
        #     selected_month_text = month_elements[0].text
        #     selected_months = months.findall(selected_month_text)
        #     if len(selected_months) == 1:
        #         # only check for better matches if we dont already have 2 months
        #         for me in month_elements[1:]:
        #             if len(ms := months.findall(me.text)) == 2:
        #                 # we only search for == 2, not > 2 beacuse if we have more than 2
        #                 # months, there's no way to glean the start and end dates
        #                 selected_month_text = me.text
        #                 selected_months = ms
        #                 # stop searching if we find this pattern
        #                 break

        #     # find all digit instances, and sort into days and years
        #     numbers = [int(n) for n in re.findall(r"\d+", selected_month_text)]
        #     days = [n for n in numbers if n <= 31]
        #     years = [n for n in numbers if n > 31]

        #     # lots of strings won't have the year, meaning they are very likely in the same
        #     # year as the post was made
        #     if not years:
        #         years = [post_date.year]

        #     # this case should be fairly rare, but there is a chance the GB thread is posted on the day it started
        #     # and only includes the end date
        #     if len(days) == 1 and post_date.day < days[0]:
        #         days = [post_date.day] + days

        #     # if we have exactly 2 days, we can reasonably predict the start and end dates
        #     if len(days) == 2:
        #         start_date = datetime.strptime(f"{selected_months[0][:3].lower()} {days[0]} {years[0]}", "%b %d %Y").date()
        #         end_date = datetime.strptime(f"{selected_months[-1][:3].lower()} {days[1]} {years[-1]}", "%b %d %Y").date()

        # return (start_date, end_date)

    async def _extract_thread(self, url: str) -> ScrapedThread:
        async with httpx.AsyncClient() as client:
            # GH assigns the asyncclient a session id, which causes messy lookups
            # in the DB, so remove it for the url we pass to the db
            queries = parse_qs(urlparse(url).query)
            topic = queries["topic"][0]
            untracked_link = f"{self.forum_url}/index.php?topic={topic}"

            # get url with tracking link, otherwise it doesn't work...
            resp = await client.get(url)
            soup = BeautifulSoup(resp.text, "html.parser")

            # a thread will always have a title
            title = soup.find("title").text
            # print(title)
            clipped_title = self._extract_thread_title(title)
            item_type = self._extract_thread_item_type(title)

            # the first postarea always contains the date the thread was posted
            postarea = soup.find("div", class_="postarea")
            # print(postarea)
            # post date is always in the same pattern:
            #   « on: DAYNAME, DAY MONTH YEAR, 05:31:58 »
            post_date_string = postarea.find("div", class_="smalltext").text.split(", ")[1]
            # print(post_date_string)
            post_date = datetime.strptime(post_date_string, "%d %B %Y").date()

            post_wrapper = soup.find("div", class_="post_wrapper")
            # print(post_wrapper)
            # the first post_wrapper > poster class always contains the thread author
            poster_info = post_wrapper.find("div", class_="poster")
            # print(poster_info)
            author = poster_info.find("h4").find("a").text
            # print(author)

            # we always want the first post class in a thread
            post = post_wrapper.find("div", class_="post")

            # getting image links by searching for all img tags
            # cannot fail because we have a find_all. if no images, we just
            # get an empty array
            image_links = []
            images = post.find_all("img", class_="bbc_img")
            for image in images:
                image_links.append(image["src"])

            # get the vendors by comparing the home url of bbc links in the thread
            # cannot fail because we're using find_all
            vendors = []
            bbc_links = post.find_all("a", class_="bbc_link")
            for bbc in bbc_links:
                # extract home url and check against vendor_map
                parsed_url: ParseResult = urlparse(bbc["href"])
                if (vendor_link := f"{parsed_url.scheme}://{parsed_url.netloc}/") in self.vendor_map:
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
                end_date=end_date
            )
