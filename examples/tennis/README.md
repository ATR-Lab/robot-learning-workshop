# Tennis example · video → K1 motion

Reference result of the sample run. After `./setup.sh` (it downloads the input to `data/inputs/tennis.mp4`):

```bash
./workshop process data/inputs/tennis.mp4
```

Your `data/outputs/tennis/` should match these files:

- `tennis_compare.mp4`: input video beside the K1. [Watch it](tennis_compare.mp4).
- `tennis_k1.mp4`: the K1 alone.
- `tennis.csv`: K1 motion, 312 rows at 30 fps. Columns: root position x, y, z in metres, root quaternion (`x,y,z,w`), 22 joint angles in radians.

Small numeric differences between runs are normal. Input: [GVHMR's tennis sample](https://github.com/zju3dv/GVHMR/tree/ee960bb6e2ea2d381aa97f08e9b71ef320b624b1/docs/example_video), research use under its license.
