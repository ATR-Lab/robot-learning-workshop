# K1 dance motions

Eight reference motions already retargeted to the Booster K1, ready to watch in MuJoCo. These are kinematic references (what a policy should track), not trained policies.

```bash
./workshop motion examples/dances/gangnam_style                          # Mac window · Docker: browser link → Play
./workshop motion examples/dances/lerobot --record data/lerobot.mp4      # save a video
```

Mac viewer: **Enter** restarts, **Space** pauses; the motion loops. The same command plays your own results: `./workshop motion data/outputs/tennis/tennis.csv`.

| Clip | Length | Notes |
| :--- | :--- | :--- |
| `gangnam_style` | 14.8 s | from a dance video with this workshop's pipeline (GVHMR → GMR), ground-aligned |
| `be_ok_dance` | 15.0 s | from a dance video with this workshop's pipeline, ground-aligned |
| `hawaii_scuba_trip` | 8.9 s | in place, calm |
| `the_fighting_chicken` | 10.1 s | in place |
| `lerobot` | 6.5 s | in place, fast arms |
| `paniolo_playah` | 7.8 s | in place, small hops |
| `tangerine_accountability` | 10.0 s | deep squats |
| `nikki_break_bot` | 21.6 s | squats, travels a little |

The last six were retargeted to K1 from Unitree G1 dance clips with an IK retargeter (trunk, feet, arm directions; ground-aligned).

**Format** (same as `./workshop robot` output): one row per frame at 30 fps, no header, 29 columns: root position x, y, z (m), root quaternion `x,y,z,w`, 22 joint angles (rad) in the order of `examples/cartwheel/robot/K1_serial.xml` (head yaw/pitch, left arm ×4, right arm ×4, left leg ×6, right leg ×6).
