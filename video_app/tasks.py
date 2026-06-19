from .models import Video
from .utils import RESOLUTIONS, convert_to_hls, generate_thumbnail


def process_video(video_id):
    """Background job: build the thumbnail and all HLS renditions for a video."""
    video = Video.objects.filter(pk=video_id).first()
    if video is None or not video.video_file:
        return
    source = video.video_file.path
    _store_thumbnail(video, source)
    _build_renditions(video_id, source)


def _store_thumbnail(video, source):
    """Generate the thumbnail and save its path on the video record."""
    video.thumbnail.name = generate_thumbnail(source, video.pk)
    video.save(update_fields=['thumbnail'])


def _build_renditions(video_id, source):
    """Transcode the source into every configured HLS resolution."""
    for resolution, height in RESOLUTIONS.items():
        convert_to_hls(source, video_id, resolution, height)
