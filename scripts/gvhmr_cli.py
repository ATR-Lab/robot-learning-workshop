"""Upstream CLI with the workshop's missing-frame-count workaround."""
import sys

if sys.argv[1:2] == ['demo']:
    from gvhmr.utils import video_io_utils
    from video_metadata import install_frame_count_fallback
    install_frame_count_fallback(video_io_utils)

from gvhmr.cli import app
app()
