import importlib.util,pathlib,tempfile,unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('runner',ROOT/'skills/rhino-modeling/scripts/rhino_run.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class DispatcherTest(unittest.TestCase):
    def test_missing_runtime(self):
        with self.assertRaises(FileNotFoundError):r.cli('/does/not/exist')
    def test_explicit_path_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix='Rhino path 测试 ') as d:
            p=pathlib.Path(d)/'custom runtime';p.touch()
            self.assertEqual(r.cli(str(p)),[str(p)])
    def test_nonexistent_instance_rejected_before_dispatch(self):
        with patch.object(r,'cli',return_value=['fake']),patch.object(r,'query',return_value='[]'):
            with self.assertRaisesRegex(ValueError,'not running'):r.run(None,'unknown','@none','missing.py',{},'/tmp/unused')
    def test_permission_error_is_not_empty_instance_list(self):
        import subprocess
        completed=subprocess.CompletedProcess([],0,stdout='Permission denied\n[]',stderr='')
        with patch.object(r.subprocess,'run',return_value=completed):
            with self.assertRaises(PermissionError):r.query(['fake'])

if __name__=='__main__':unittest.main()
