import os
import re
import shutil
import subprocess
import time

from django.conf import settings

# Target HLS renditions: label -> output height in pixels.
RESOLUTIONS = {'480p': 480, '720p': 720, '1080p': 1080}

# A valid segment is a plain filename such as '000.ts' (no path separators).
SEGMENT_PATTERN = re.compile(r'^[\w-]+\.ts$')


def is_valid_resolution(resolution):
    """Return True if the resolution is one we actually generate."""
    return resolution in RESOLUTIONS


def is_safe_segment(segment):
    """Return True only for plain '.ts' segment names (blocks path traversal)."""
    return bool(SEGMENT_PATTERN.match(segment))


def hls_base_dir(video_id):
    """Return the root directory that holds all HLS output of a video."""
    return os.path.join(settings.MEDIA_ROOT, 'hls', str(video_id))


def hls_file_path(video_id, resolution, filename):
    """Return the on-disk path of one HLS file (playlist or segment)."""
    return os.path.join(hls_base_dir(video_id), resolution, filename)


def hls_dir(video_id, resolution):
    """Return (and create) the output directory for one HLS resolution."""
    path = os.path.join(hls_base_dir(video_id), resolution)
    os.makedirs(path, exist_ok=True)
    return path


FFMPEG_BASE = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error']


def run_ffmpeg(cmd, attempts=3):
    """Run an FFmpeg command, retrying transient failures; raise with stderr."""
    result = None
    for attempt in range(attempts):
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return
        time.sleep(attempt + 1)
    raise RuntimeError(f'FFmpeg failed ({result.returncode}): {result.stderr.strip()}')


def _hls_command(source, height, segment_pattern, playlist):
    """Build the FFmpeg argument list for a single HLS rendition."""
    return FFMPEG_BASE + [
        '-i', source,
        '-vf', f'scale=-2:{height}',
        '-c:v', 'libx264', '-c:a', 'aac',
        '-hls_time', '10', '-hls_playlist_type', 'vod',
        '-hls_segment_filename', segment_pattern, playlist,
    ]


def convert_to_hls(source, video_id, resolution, height):
    """Transcode the source into one HLS rendition; return the playlist path."""
    out_dir = hls_dir(video_id, resolution)
    playlist = os.path.join(out_dir, 'index.m3u8')
    segments = os.path.join(out_dir, '%03d.ts')
    run_ffmpeg(_hls_command(source, height, segments, playlist))
    return playlist


def generate_thumbnail(source, video_id):
    """Grab a single frame as the thumbnail; return its media-relative path."""
    relative = f'thumbnails/{video_id}.jpg'
    dest = os.path.join(settings.MEDIA_ROOT, relative)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    run_ffmpeg(FFMPEG_BASE + ['-ss', '00:00:01.000', '-i', source,
                              '-frames:v', '1', '-update', '1', dest])
    return relative


def remove_hls_output(video_id):
    """Delete the whole HLS output tree of a video, if present."""
    shutil.rmtree(hls_base_dir(video_id), ignore_errors=True)
