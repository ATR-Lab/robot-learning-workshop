"""Verify self-contained ONNX preparation without network or private policies."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location('prepare_policy', Path(__file__).parents[1] / 'scripts/prepare_policy.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
AVAILABLE = all(importlib.util.find_spec(name) for name in ('onnx', 'numpy', 'mujoco'))

JOINTS = ['Head_Yaw', 'Head_Pitch'] + [
    side + '_' + joint for side in ('Left', 'Right')
    for joint in ('Shoulder_Pitch', 'Shoulder_Roll', 'Elbow_Pitch', 'Elbow_Yaw')
] + [
    side + '_' + joint for side in ('Left', 'Right')
    for joint in ('Hip_Pitch', 'Hip_Roll', 'Hip_Yaw', 'Knee_Pitch', 'Ankle_Pitch', 'Ankle_Roll')
]


def export_fixture(path):
    import numpy as np
    import onnx
    from onnx import helper, numpy_helper, TensorProto

    nodes, tensors = [], [numpy_helper.from_array(np.array([0], dtype=np.int64), 'index')]
    outputs = [helper.make_tensor_value_info('actions', TensorProto.FLOAT, [1, 22])]
    tensors.append(numpy_helper.from_array(np.zeros((1, 22), dtype=np.float32), 'actions'))
    for key in p.MOTION_KEYS:
        shape = (3, 22) if key.startswith('joint_') else (3, 1, 4 if key == 'body_quat_w' else 3)
        values = np.zeros(shape, dtype=np.float32)
        if key == 'body_quat_w':
            values[:, :, 0] = 1
        tensors.append(numpy_helper.from_array(values, key + '.1'))
        nodes.append(helper.make_node('Gather', [key + '.1', 'index'], [key]))
        outputs.append(helper.make_tensor_value_info(key, TensorProto.FLOAT, [1, *shape[1:]]))
    graph = helper.make_graph(nodes, 'tracking', [
        helper.make_tensor_value_info('obs', TensorProto.FLOAT, [1, 128]),
        helper.make_tensor_value_info('time_step', TensorProto.FLOAT, [1, 1]),
    ], outputs, tensors)
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 18)])
    metadata = dict(joint_names=','.join(JOINTS), body_names='Trunk', anchor_body_name='Trunk',
                    joint_stiffness=','.join(['4'] * 22), joint_damping=','.join(['0.25'] * 22),
                    default_joint_pos=','.join(['0'] * 22), action_scale=','.join(['0.3'] * 22),
                    observation_names=','.join(p.OBS_WIDTHS))
    helper.set_model_props(model, metadata)
    onnx.save(model, path)
    return model


def robot_fixture(folder):
    folder.mkdir()
    root = ET.Element('mujoco')
    world = ET.SubElement(root, 'worldbody')
    body = ET.SubElement(world, 'body', name='Trunk')
    ET.SubElement(body, 'freejoint')
    ET.SubElement(body, 'geom', type='sphere', size='0.02', mass='1')
    for index, name in enumerate(JOINTS):
        body = ET.SubElement(body, 'body', name='body_' + str(index), pos='0 0 0.03')
        ET.SubElement(body, 'joint', name=name, axis='0 1 0')
        ET.SubElement(body, 'geom', type='sphere', size='0.01', mass='0.1')
    ET.ElementTree(root).write(folder / 'k1.xml')


@unittest.skipUnless(AVAILABLE, 'Simulation dependencies are installed in the simulation CI job.')
class PrepareTests(unittest.TestCase):
    def test_embedded_motion_and_gains_prepare_a_compilable_scene(self):
        import mujoco
        import numpy as np

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'policy.onnx'
            export_fixture(source)
            robot_fixture(root / 'assets')
            with patch.object(p, 'ensure_assets', return_value=root / 'assets') as fetch:
                ready = p.prepare_onnx(source, root / 'policies')
                cached = p.prepare_onnx(source, root / 'policies')
            self.assertEqual(ready, cached)
            self.assertEqual(fetch.call_count, 1)
            cfg = json.loads((ready / 'config.json').read_text())
            self.assertEqual(cfg['joint_names'], JOINTS)
            self.assertEqual(cfg['obs_dim'], 128)
            self.assertEqual(cfg['kp'], [4.0] * 22)
            self.assertEqual((ready / 'policy.onnx').read_bytes(), source.read_bytes())
            model = mujoco.MjModel.from_xml_path(str(ready / cfg['robot_xml']))
            self.assertEqual(model.nu, 22)
            self.assertEqual(model.nq, 29)
            with np.load(ready / 'motion.npz') as motion:
                self.assertEqual(motion['joint_pos'].shape, (3, 22))
                self.assertEqual(list(motion['joint_names']), JOINTS)

    def test_metadata_free_and_external_tensor_exports_are_rejected(self):
        import onnx

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'policy.onnx'
            model = export_fixture(path)
            del model.metadata_props[:]
            onnx.save(model, path)
            with self.assertRaisesRegex(ValueError, 'metadata'):
                p.read_export(path)
            model = export_fixture(path)
            model.graph.initializer[0].data_location = onnx.TensorProto.EXTERNAL
            path.write_bytes(model.SerializeToString())
            with self.assertRaisesRegex(ValueError, 'external'):
                p.read_export(path)

    def test_observation_history_is_not_silently_ignored(self):
        import onnx

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'policy.onnx'
            model = export_fixture(path)
            entry = model.metadata_props.add()
            entry.key, entry.value = 'observation_terms_history_length', ','.join(['4'] * 9)
            onnx.save(model, path)
            with self.assertRaisesRegex(ValueError, 'history'):
                p.read_export(path)


if __name__ == '__main__':
    unittest.main()
