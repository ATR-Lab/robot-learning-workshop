# K1 cartwheel example

After `./setup.sh`, run from the repository folder:

```bash
./sim play examples/cartwheel
```

Docker: `./sim --docker play examples/cartwheel`, then http://localhost:8080 → **Play**.
Mac: **Enter** restarts; **Space** pauses. No venv activation needed.

The checkpoint-29999 policy starts standing, performs a cartwheel and returns to standing.
[Watch the recorded result](../../docs/examples/cartwheel_final_29999.mp4).

Included files:

- `policy.onnx`: trained policy with observation normalization inside.
- `config.json`, `motion.npz`, `robot/`: matching settings, reference and K1 MuJoCo model/meshes. Keep these together.
- `cartwheel_reference.csv`: reference trajectory at 50 Hz.
- `cartwheel_29999_mujoco.csv`: recorded policy rollout at 50 Hz.

CSV columns: time in seconds, root position in metres, quaternion (`w,x,y,z`), 22 joint angles and 22 joint velocities in the joint order from `config.json`.

This is a MuJoCo policy example; the robot video is not a human-video input for GVHMR. No training checkpoint or original human video is required to run it.

Headless check: `./sim play examples/cartwheel --check`.
The supplied policy completes the 10.24-second Mac check without falling on MuJoCo 3.16.0. Docker runtime verification is pending.

Robot model and meshes originate from the Booster K1 assets supplied with the training setup. Policy: readiness_v5 warm119, checkpoint 29999.
