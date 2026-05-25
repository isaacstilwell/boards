from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField


class Thread(models.Model):
    ITEM_TYPES = [
        ("keyboard", "Keyboard"),
        ("keycaps", "Keycaps"),
        ("other", "Other"),
        ("unknown", "Unknown"),
    ]
    THREAD_TYPES = [
        ("instock", "In Stock"),
        ("upcoming", "Upcoming"),
        ("active", "Active"),
        ("completed", "Completed"),
    ]
    STATUS = [
        ("approved", "Approved"),
        ("pending", "Pending"),
        ("rejected", "Rejected"),
    ]
    CURRENCY = [("USD", "$"), ("EUR", "€"), ("GBP", "£")]

    # name of the project in this thread
    title = models.CharField(max_length=255)
    # person who designed it (if available)
    designer = models.CharField(max_length=255, null=True, blank=True)
    # link to GH or vendor
    external_url = models.URLField(null=True, blank=True, unique=True)
    # image that displays in the list of threads
    primary_image_url = models.URLField(blank=True)
    # images that display in the detail area
    image_urls = ArrayField(models.URLField(), blank=True, default=list)
    # list of vendors that sell the keyboard
    vendors = ArrayField(models.CharField(max_length=255), blank=True, default=list)
    # currency that the price is in ($, €, £)
    currency = models.CharField(
        max_length=3, choices=CURRENCY, null=True, blank=True, default="USD"
    )
    # price of the item
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    # type (keyboard, keycaps, other, unknown) - defaults to keyboard for
    # compose section
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, default="keyboard")
    # timeline type (in-stock, upcoming GB, active GB, completed GB) - defaults
    # to upcoming for compose section
    thread_type = models.CharField(
        max_length=20, choices=THREAD_TYPES, null=True, blank=True, default="upcoming"
    )
    # date the thread was posted (since the scraper runs daily, this should be
    # pretty accurate)
    post_date = models.DateField()
    # date the GB starts (if available)
    start_date = models.DateField(null=True, blank=True)
    # date the GB ends (if available)
    end_date = models.DateField(null=True, blank=True)
    # thread status - admins need to approve user-created threads
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    # poster if any
    poster = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_threads",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def author(self) -> str | None:
        if self.designer:
            return self.designer
        elif self.poster:
            return self.poster.username
        else:
            return None

    class Meta:
        ordering = ["-post_date"]
        indexes = [
            models.Index(fields=["status"], name="status_idx"),
            models.Index(fields=["item_type"], name="item_type_idx"),
            models.Index(fields=["thread_type"], name="thread_type_idx"),
            models.Index(fields=["post_date"], name="post_date_idx"),
            models.Index(fields=["start_date"], name="start_date_idx"),
            models.Index(fields=["end_date"], name="end_date_idx"),
        ]

    def __str__(self):
        return self.title


class SavedThread(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="saved")
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "thread"]
        order_with_respect_to = "thread"

    def __str__(self):
        return f"{self.user.username} — {self.thread.title}"


class UploadedImage(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="uploaded_images"
    )
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, null=True, blank=True)
    image = models.ImageField(upload_to="images/")

    def __str__(self):
        return f"Image uploaded by {self.user} on {self.thread}"
