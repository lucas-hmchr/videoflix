import os

from django.http import FileResponse, Http404
from rest_framework import permissions
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView

from ..models import Video
from ..utils import hls_file_path, is_safe_segment, is_valid_resolution
from .serializers import VideoListSerializer


class VideoListView(ListAPIView):
    """Return all videos ordered by creation date (newest first)."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VideoListSerializer
    queryset = Video.objects.all()


class HLSPlaylistView(APIView):
    """Serve the HLS manifest (index.m3u8) for a video and resolution."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, movie_id, resolution):
        if not is_valid_resolution(resolution):
            raise Http404
        path = hls_file_path(movie_id, resolution, 'index.m3u8')
        if not os.path.exists(path):
            raise Http404
        return FileResponse(open(path, 'rb'),
                            content_type='application/vnd.apple.mpegurl')


class HLSSegmentView(APIView):
    """Serve a single HLS video segment (.ts) for a video and resolution."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, movie_id, resolution, segment):
        if not (is_valid_resolution(resolution) and is_safe_segment(segment)):
            raise Http404
        path = hls_file_path(movie_id, resolution, segment)
        if not os.path.exists(path):
            raise Http404
        return FileResponse(open(path, 'rb'), content_type='video/MP2T')
