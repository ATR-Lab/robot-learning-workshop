"""Run in the GVHMR environment: fetch missing body models with the saved SMPL-X / SMPL logins."""
import sys

from gvhmr.utils import assets, mpi_download

need = {name: not (assets.BODY_MODEL_ROOT / name / file).exists()
        for name, file in (('smplx', 'SMPLX_NEUTRAL.npz'), ('smpl', 'SMPL_NEUTRAL.pkl'))}
need = {name: True for name, missing in need.items() if missing and mpi_download.credentials(name)}
if need:
    print(f"Downloading body models with the saved logins: {', '.join(need)}", flush=True)
    try:
        mpi_download.fetch_body_models(assets.BODY_MODEL_ROOT, smplx='smplx' in need, smpl='smpl' in need)
    except PermissionError:
        sys.exit(f"Login refused for {' / '.join(need).upper()}: wrong email/password, or the license on "
                 'that site is not accepted. Check by logging in on the website, then run: ./workshop auth')
