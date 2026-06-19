from django.urls import path

from .views import HLSPlaylistView, HLSSegmentView, VideoListView

urlpatterns = [
    path('video/', VideoListView.as_view(), name='video-list'),
    path(
        'video/<int:movie_id>/<str:resolution>/index.m3u8',
        HLSPlaylistView.as_view(), name='hls-playlist',
    ),
    path(
        'video/<int:movie_id>/<str:resolution>/<str:segment>/',
        HLSSegmentView.as_view(), name='hls-segment',
    ),
    # Same view without trailing slash: HLS playlists reference bare '000.ts',
    # so this lets players fetch segments without an extra redirect.
    path(
        'video/<int:movie_id>/<str:resolution>/<str:segment>',
        HLSSegmentView.as_view(),
    ),
]
