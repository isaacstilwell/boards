from django.core.management.base import BaseCommand, CommandError
from threads.scraping.manager import ScraperManager

class Command(BaseCommand):
    manager = ScraperManager()
    manager.scrape()