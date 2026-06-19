import logging

import django_rq
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from redis.exceptions import RedisError

from .models import Video
from .tasks import process_video
from .utils import remove_hls_output

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Video)
def enqueue_video_processing(sender, instance, created, **kwargs):
    """Queue HLS conversion when a new video with a source file is created."""
    if not (created and instance.video_file):
        return
    try:
        django_rq.get_queue('default').enqueue(process_video, instance.pk)
    except RedisError:
        logger.warning('Redis unavailable: video %s not queued.', instance.pk)


@receiver(post_delete, sender=Video)
def cleanup_video_files(sender, instance, **kwargs):
    """Remove the source file, thumbnail and HLS output of a deleted video."""
    instance.video_file.delete(save=False)
    instance.thumbnail.delete(save=False)
    remove_hls_output(instance.pk)
