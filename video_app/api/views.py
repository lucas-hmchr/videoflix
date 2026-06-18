from rest_framework import permissions
from rest_framework.generics import ListAPIView

from ..models import Video
from .serializers import VideoListSerializer


class VideoListView(ListAPIView):
    """Return all videos ordered by creation date (newest first)."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VideoListSerializer
    queryset = Video.objects.all()
