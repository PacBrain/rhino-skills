"""Portable staging and input guarantees; no Rhino runtime required."""
import importlib.util
import pathlib
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / 'skills/rhino-modeling/scripts/job_support.py'
spec = importlib.util.spec_from_file_location('job_support_test', PATH)
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)


class SupportTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='Rhino 支持 ')
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        self.output = self.root / 'output'

    def test_loader_ignores_module_cache_and_reads_current_source(self):
        caller = self.root / 'job.py'
        helper = self.root / 'native_ops.py'
        helper.write_text('VALUE = "当前"\n', encoding='utf-8')
        stale = types.ModuleType('native_ops')
        stale.VALUE = 'old'
        with patch.dict('sys.modules', {'native_ops': stale}):
            first = support.load_sibling(caller, helper.name)
            helper.write_text('VALUE = "修改"\n', encoding='utf-8')
            second = support.load_sibling(caller, helper.name)
        self.assertEqual(first.VALUE, '当前')
        self.assertEqual(second.VALUE, '修改')
        self.assertNotEqual(first.__name__, second.__name__)

    def test_exception_publishes_nothing_and_removes_stage(self):
        with self.assertRaisesRegex(RuntimeError, 'later validation'):
            with support.staged_outputs(self.output, ['one.json', 'two.json']) as stage:
                support.write_json(stage / 'one.json', {'text': '中文'})
                raise RuntimeError('later validation failed')
        self.assertEqual(list(self.output.iterdir()), [])

    def test_complete_batch_publishes_unicode_json(self):
        with support.staged_outputs(self.output, ['报告.json', 'mesh.stl']) as stage:
            support.write_json(stage / '报告.json', {'text': '中文'})
            (stage / 'mesh.stl').write_bytes(b'mesh')
            self.assertFalse((self.output / 'mesh.stl').exists())
        self.assertIn('中文', (self.output / '报告.json').read_text(encoding='utf-8'))
        self.assertEqual(sorted(p.name for p in self.output.iterdir()), ['mesh.stl', '报告.json'])

    def test_preexisting_output_and_case_collision_refused(self):
        self.output.mkdir()
        original = self.output / 'Model.STL'
        original.write_bytes(b'original')
        with self.assertRaises(FileExistsError):
            with support.staged_outputs(self.output, ['model.stl']):
                self.fail('staging should not start')
        self.assertEqual(original.read_bytes(), b'original')

    def test_duplicate_and_nonportable_names_refused(self):
        for names in [['model.stl', 'MODEL.stl'], ['../model.stl'], ['dir/model.stl'],
                      ['CON.stl'], ['model?.stl'], ['name.'], []]:
            with self.subTest(names=names), self.assertRaises(ValueError):
                with support.staged_outputs(self.output, names):
                    self.fail('staging should not start')

    def test_missing_or_extra_artifacts_abort_batch(self):
        for extra in [False, True]:
            with self.subTest(extra=extra), self.assertRaisesRegex(RuntimeError, 'artifact set'):
                with support.staged_outputs(self.output, ['one.json']) as stage:
                    if extra:
                        (stage / 'one.json').write_text('{}', encoding='utf-8')
                        (stage / 'extra.json').write_text('{}', encoding='utf-8')
            self.assertEqual(list(self.output.iterdir()), [])

    def test_publication_failure_rolls_back_only_its_own_files(self):
        with self.assertRaises(FileExistsError):
            with support.staged_outputs(self.output, ['one.json', 'two.json']) as stage:
                for name in ['one.json', 'two.json']:
                    support.write_json(stage / name, {})
                # A concurrent creator after preflight must not be overwritten.
                (self.output / 'two.json').write_text('concurrent', encoding='utf-8')
        self.assertFalse((self.output / 'one.json').exists())
        self.assertEqual((self.output / 'two.json').read_text(encoding='utf-8'), 'concurrent')

    def test_write_json_refuses_overwrite_and_nonfinite(self):
        path = self.root / 'report.json'
        support.write_json(path, {'valid': True})
        with self.assertRaises(FileExistsError):
            support.write_json(path, {})
        with self.assertRaises(ValueError):
            support.write_json(self.root / 'nan.json', {'value': float('nan')})
        self.assertFalse((self.root / 'nan.json').exists())

    def test_sources_require_existing_absolute_unique_3dm(self):
        source = self.root / 'model.3dm'
        source.write_bytes(b'fixture')
        self.assertEqual(support.source_paths([str(source)]), [source.resolve()])
        for value in [[], None, ['relative.3dm'], [str(source), str(source)], [str(self.root / 'missing.3dm')]]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                support.source_paths(value)


if __name__ == '__main__':
    unittest.main()
