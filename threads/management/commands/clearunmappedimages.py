from django.core.management.base import BaseCommand, CommandError
from threads.models import UploadedImage


class Command(BaseCommand):
    """
    Support for the clearunmappedimages django command.

    Clears images that aren't associated with threads. Intended to be run on a
    crontab once a day.
    """

    help = "Deletes uploaded images that aren't associated with a thread"

    def handle(self, *args, **options):
        UploadedImage.objects.filter(thread__isnull=True).delete()
