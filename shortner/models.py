from django.db import models
from django.utils import timezone

class Url(models.Model):
    link = models.URLField(max_length=2048) # Increased max_length for longer URLs
    uuid = models.CharField(max_length=10, unique=True, db_index=True) # Added db_index for faster lookups
    click_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    last_clicked = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.uuid} -> {self.link[:70]}{'...' if len(self.link) > 70 else ''}" # Truncate long links

    class Meta:
        ordering = ['-created_at']
        verbose_name = "URL Entry"
        verbose_name_plural = "URL Entries"