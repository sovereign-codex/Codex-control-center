import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('restore_preflight', Path(__file__).resolve().parents[1] / 'restore-preflight.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RestoreIdentityTests(unittest.TestCase):
    def setUp(self):
        self.config = {'services': {'hall-core': {'build': {'args': {'HALL_RUNTIME_UID': '997', 'HALL_RUNTIME_GID': '996'}}, 'volumes': [{'type': 'bind', 'source': '/tmp/hall-restore-test', 'target': '/var/lib/hall-core'}]}}}
        self.container = {'Config': {'User': '997:996'}, 'Mounts': [{'Type': 'bind', 'Source': '/tmp/hall-restore-test', 'Destination': '/var/lib/hall-core', 'RW': True}]}

    def test_actual_service_identity_not_10001(self):
        self.assertEqual(module.validate(self.config, self.container), ('997', '996', '/tmp/hall-restore-test'))

    def test_legacy_identity_supported_when_matched(self):
        args = self.config['services']['hall-core']['build']['args']
        args.update(HALL_RUNTIME_UID='10001', HALL_RUNTIME_GID='10001')
        self.container['Config']['User'] = '10001:10001'
        self.assertEqual(module.validate(self.config, self.container)[:2], ('10001', '10001'))

    def test_identity_mismatch_rejected(self):
        self.container['Config']['User'] = '10001:10001'
        with self.assertRaises(ValueError):
            module.validate(self.config, self.container)

    def test_bad_or_root_identity_rejected(self):
        for uid in ('0', '-1', 'tyme', '997\n0', ''):
            config = copy.deepcopy(self.config)
            config['services']['hall-core']['build']['args']['HALL_RUNTIME_UID'] = uid
            with self.assertRaises(ValueError):
                module.validate(config, self.container)

    def test_wrong_mount_and_readonly_rejected(self):
        for change in ({'Source': '/tmp/other'}, {'RW': False}, {'Type': 'volume'}):
            container = copy.deepcopy(self.container)
            container['Mounts'][0].update(change)
            with self.assertRaises(ValueError):
                module.validate(self.config, container)


if __name__ == '__main__':
    unittest.main()
