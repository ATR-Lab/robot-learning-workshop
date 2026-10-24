"""Run in the GVHMR environment; export the upstream-compatible prediction."""
import sys
from pathlib import Path
from video_metadata import decoded_video_lwh, install_frame_count_fallback
video, target, *pose_video = map(Path, sys.argv[1:])
# Validate before loading/downloading the multi-GB models.
print(f'Video verified: {decoded_video_lwh(video)} (frames, width, height)', flush=True)
import gvhmr
from gvhmr.utils import video_io_utils
install_frame_count_fallback(video_io_utils)
result = gvhmr.recover(str(video), static_camera=True, output_dir=str(target.parent))
result.save(target)
if pose_video:  # in-camera body mesh beside the world-frame view
    import moderngl
    create = moderngl.create_standalone_context

    def any_egl_device(*args, **kwargs):
        """GVHMR asks for the default EGL device; on WSL or with CPU-only Mesa another one may be the working one."""
        try:
            return create(*args, **kwargs)
        except Exception:
            if kwargs.get('backend') != 'egl' or 'device_index' in kwargs:
                raise
            for index in range(8):
                try:
                    return create(*args, device_index=index, **kwargs)
                except Exception:
                    pass
            raise

    moderngl.create_standalone_context = any_egl_device
    print(f'Body pose video: {result.render(pose_video[0], view="both")}', flush=True)
