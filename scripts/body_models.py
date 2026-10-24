"""Run in the GVHMR environment: fetch missing body models with the saved SMPL-X / SMPL logins."""
import sys

from gvhmr.utils import assets, mpi_download

FILES = {'smplx': 'smplx/SMPLX_NEUTRAL.npz', 'smpl': 'smpl/SMPL_NEUTRAL.pkl'}
SITES = {'smplx': 'https://smpl-x.is.tue.mpg.de/', 'smpl': 'https://smpl.is.tue.mpg.de/'}
failed = []
for name, file in FILES.items():
    if (assets.BODY_MODEL_ROOT / file).exists() or not mpi_download.credentials(name):
        continue
    print(f'Downloading the {name.upper()} body model with the saved login', flush=True)
    try:
        mpi_download.fetch_body_models(assets.BODY_MODEL_ROOT, smplx=name == 'smplx', smpl=name == 'smpl')
    except PermissionError as error:
        reason = ('wrong email or password' if 'HTTP 401' in str(error) else
                  'download refused (HTTP 403): often the license is not accepted on the site, '
                  'or there were too many downloads recently (try again later)')
        failed.append(f'  {name.upper()}: {reason}. Check by logging in at {SITES[name]}')
if failed:
    sys.exit('Body model download failed:\n' + '\n'.join(failed) + '\n'
             'Then run: ./workshop auth   ·   Or copy the files you already have to\n'
             + '\n'.join(f'  {assets.BODY_MODEL_ROOT / file}' for file in FILES.values()))
