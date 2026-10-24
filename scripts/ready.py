"""Run in the GVHMR environment: short checklist of what video conversion needs."""
import sys

from gvhmr.utils import assets

missing = set(assets.missing('demo'))
checks = [(f'body model {name}', (assets.BODY_MODEL_ROOT / name / file).exists())
          for name, file in (('smplx', 'SMPLX_NEUTRAL.npz'), ('smpl', 'SMPL_NEUTRAL.pkl'))]
checks += [(f'checkpoint {name}', name not in missing)
           for name, asset in assets.ASSETS.items() if asset.group == 'demo']
for name, ok in checks:
    print(f"  {'✓' if ok else '✗'} {name}")
if not all(ok for _, ok in checks):
    print('Missing models. Body models: ./workshop auth  ·  checkpoints: ./workshop download')
    sys.exit(1)
