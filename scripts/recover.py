"""Run in the GVHMR environment; export the upstream-compatible prediction."""
import sys
from pathlib import Path
import gvhmr
video, target = map(Path, sys.argv[1:])
result = gvhmr.recover(str(video), static_camera=True, output_dir=str(target.parent))
result.save(target)
