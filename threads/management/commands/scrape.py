from django.core.management.base import BaseCommand, CommandError
from threads.scraping.manager import ScraperManager
import asyncio


class Command(BaseCommand):
    """
    Support for the scrape django command.

    Instantiates ScraperManager and runs the .scrape() method, populating the DB
    with new Threads and updating existing Thread objects if applicable.
    """

    help = "Runs a round of scraping across all sites"

    def handle(self, *args, **options):
        manager = ScraperManager()
        asyncio.run(manager.scrape())
