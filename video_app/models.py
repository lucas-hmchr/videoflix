from django.db import models


class Video(models.Model):
    """A streamable video with metadata shown on the dashboard."""

    class Category(models.TextChoices):
        DRAMA = 'Drama', 'Drama'
        ROMANCE = 'Romance', 'Romance'
        ACTION = 'Action', 'Action'
        COMEDY = 'Comedy', 'Comedy'
        DOCUMENTARY = 'Documentary', 'Documentary'

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=Category.choices)
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True)
    video_file = models.FileField(upload_to='videos/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
