from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField

class Thread(models.Model):
    ITEM_TYPES = [('keyboard', 'Keyboard'), ('keycaps', 'Keycaps'), ('other', 'Other'), ('unknown', 'Unknown')]
    THREAD_TYPES = [('instock', 'In Stock'), ('upcoming', 'Upcoming'), ('active', 'Active'), ('completed', 'Completed')]
    STATUS = [('approved', 'Approved'), ('pending', 'Pending'), ('rejected', 'Rejected')]
    CURRENCY = [("USD", "$"), ("EUR", "€"), ("GBP", "£")]

    title = models.CharField(max_length=255)
    designer = models.CharField(max_length=255, null=True, blank=True)
    external_url = models.URLField(null=True, blank=True, unique=True)
    primary_image_url = models.URLField(blank=True)
    image_urls = ArrayField(models.URLField(), blank=True, default=list)
    vendors = ArrayField(models.CharField(max_length=255), blank=True, default=list)
    currency = models.CharField(max_length=3, choices=CURRENCY, null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES)
    thread_type = models.CharField(max_length=20, choices=THREAD_TYPES, null=True, blank=True)
    post_date = models.DateField()
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    poster = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_threads'
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
        ordering = ['-post_date']
        indexes = [
            models.Index(fields=['status'], name="status_idx"),
            models.Index(fields=['item_type'], name="item_type_idx"),
            models.Index(fields=["thread_type"], name="thread_type_idx"),
            models.Index(fields=["post_date"], name="post_date_idx"),
            models.Index(fields=["start_date"], name="start_date_idx"),
            models.Index(fields=["end_date"], name="end_date_idx")
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
        return f'{self.user.username} — {self.thread.title}'