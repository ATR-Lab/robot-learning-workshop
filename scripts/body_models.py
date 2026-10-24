"""Run in the GVHMR environment: fetch missing body models with the saved SMPL-X / SMPL logins."""
from gvhmr.utils import assets, mpi_download

need = {name: not (assets.BODY_MODEL_ROOT / name / file).exists()
        for name, file in (('smplx', 'SMPLX_NEUTRAL.npz'), ('smpl', 'SMPL_NEUTRAL.pkl'))}
need = {name: True for name, missing in need.items() if missing and mpi_download.credentials(name)}
if need:
    print(f"Downloading body models with the saved logins: {', '.join(need)}", flush=True)
    mpi_download.fetch_body_models(assets.BODY_MODEL_ROOT, smplx='smplx' in need, smpl='smpl' in need)
