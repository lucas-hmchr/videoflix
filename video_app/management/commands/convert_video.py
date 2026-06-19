from django.core.management.base import BaseCommand, CommandError

from video_app.models import Video
from video_app.tasks import process_video


class Command(BaseCommand):
    """Convert a video to HLS synchronously (local testing without a worker)."""

    help = 'Generate thumbnail + HLS renditions for a video by its id.'

    def add_arguments(self, parser):
        parser.add_argument('video_id', type=int, help='ID of the Video to convert.')

    def handle(self, *args, **options):
        video_id = options['video_id']
        if not Video.objects.filter(pk=video_id).exists():
            raise CommandError(f'Video {video_id} does not exist.')
        self.stdout.write(f'Converting video {video_id} (this runs FFmpeg)...')
        process_video(video_id)
        self.stdout.write(self.style.SUCCESS(
            f'Done. Thumbnail + 480p/720p/1080p HLS generated for video {video_id}.'
        ))
