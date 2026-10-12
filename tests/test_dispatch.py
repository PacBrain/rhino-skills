import contextlib
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('runner', ROOT / 'skills/rhino-modeling/scripts/rhino_run.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class DispatcherTest(unittest.TestCase):
    def test_cli_streams_use_utf8_under_legacy_redirected_encoding(self):
        script = ROOT / 'skills/rhino-modeling/scripts/rhino_run.py'
        code = '''import importlib.util,json,sys
spec=importlib.util.spec_from_file_location('runner',sys.argv[1])
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
runner.cli=lambda binary: ['fake']
runner.query=lambda args: '8.35' if args[-1]=='-V' else json.dumps([{'activeDoc':{'title':'模型.3dm'}}],ensure_ascii=False)
sys.argv=['rhino_run.py','env']
runner.main()
print('诊断信息',file=sys.stderr)
'''
        environment = dict(os.environ, PYTHONIOENCODING='ascii')
        completed = subprocess.run([sys.executable, '-c', code, str(script)],
                                   capture_output=True, env=environment, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout.decode('utf-8'))['instances'][0]['activeDoc']['title'],
                         '模型.3dm')
        self.assertEqual(completed.stderr.decode('utf-8').strip(), '诊断信息')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='Rhino dispatch 测试 ')
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve()
        self.script = self.root / '脚本 with spaces.py'
        self.script.write_text("print('完成')\n", encoding='utf-8')
        self.output = self.root / '输出 files'

    def run_job(self, **overrides):
        args = dict(binary=None, instance='pipe-1', expected='@none', script=self.script,
                    job={'label': '测试'}, output=self.output, timeout=1)
        args.update(overrides)
        return r.run(**args)

    def dispatch_query(self, on_dispatch):
        def query(args, timeout=30):
            if args[-2:] == ['list', '--json']:
                return '[{"pipeId":"pipe-1"}]'
            self.assertEqual(args[:4], ['fake', '--rhino', 'pipe-1', 'script'])
            wrapper = pathlib.Path(args[4])
            request = json.loads(wrapper.with_name('request.json').read_text(encoding='utf-8'))
            self.assertEqual(request['job'], {'label': '测试'})
            self.assertEqual(request['script'], str(self.script))
            self.assertEqual(wrapper.read_text(encoding='utf-8'), r.WRAPPER)
            on_dispatch(wrapper, request)
            return 'queued'
        return query

    def result(self, wrapper, request, **values):
        data = dict(token=request['token'], status='passed', stdout='完成\n', stderr='警告\n')
        data.update(values)
        wrapper.with_name('result.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

    def test_missing_runtime(self):
        with self.assertRaises(FileNotFoundError):
            r.cli('/does/not/exist')

    def test_explicit_path_with_spaces(self):
        p = self.root / 'custom runtime'
        p.touch()
        self.assertEqual(r.cli(str(p)), [str(p)])

    def test_nonexistent_instance_rejected_before_dispatch(self):
        with patch.object(r, 'cli', return_value=['fake']), patch.object(r, 'query', return_value='[]'):
            with self.assertRaisesRegex(ValueError, 'not running'):
                self.run_job(instance='unknown')
        self.assertFalse(self.output.exists())

    def test_permission_error_is_not_empty_instance_list(self):
        completed = subprocess.CompletedProcess([], 1, stdout='Permission denied\n[]', stderr='failed')
        with patch.object(r.subprocess, 'run', return_value=completed):
            with self.assertRaises(PermissionError):
                r.query(['fake'])

    def test_query_decodes_utf8_and_retains_both_error_streams(self):
        completed = subprocess.CompletedProcess([], 1, stdout='输出内容', stderr='错误内容')
        with patch.object(r.subprocess, 'run', return_value=completed) as run:
            with self.assertRaisesRegex(RuntimeError, '输出内容\n错误内容'):
                r.query(['fake'], timeout=2)
        self.assertEqual(run.call_args.kwargs['encoding'], 'utf-8')
        self.assertEqual(run.call_args.kwargs['timeout'], 2)

    def test_invalid_timeouts_rejected_before_runtime_or_files(self):
        for timeout in [0, -1, float('nan'), float('inf'), -float('inf'), None, 'invalid', True]:
            with self.subTest(timeout=timeout), patch.object(r, 'cli') as cli:
                with self.assertRaisesRegex(ValueError, 'finite and positive'):
                    self.run_job(timeout=timeout)
                cli.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_invalid_jobs_rejected_before_runtime_or_files(self):
        for job in [[], None, 'text', {'value': float('nan')}, {'value': object()}]:
            with self.subTest(job=job), patch.object(r, 'cli') as cli:
                with self.assertRaisesRegex(ValueError, 'JSON'):
                    self.run_job(job=job)
                cli.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_relative_or_invalid_expected_document_rejected_upfront(self):
        for expected in ['model.3dm', '', None, b'/model.3dm']:
            with self.subTest(expected=expected), patch.object(r, 'cli') as cli:
                with self.assertRaisesRegex(ValueError, 'absolute path or @none'):
                    self.run_job(expected=expected)
                cli.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_matching_token_returns_unicode_stdout_and_stderr(self):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(r, 'cli', return_value=['fake']), \
                patch.object(r, 'query', side_effect=self.dispatch_query(self.result)) as query, \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = self.run_job(expected=self.root / '当前模型.3dm')
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(out.getvalue(), '完成\n')
        self.assertEqual(err.getvalue(), '警告\n')
        self.assertEqual(query.call_count, 2)

    def test_stale_token_does_not_complete_job(self):
        state = {}
        def dispatch(wrapper, request):
            state.update(wrapper=wrapper, request=request)
            self.result(wrapper, request, token='old-token', status='failed', error='stale failure')
        def advance(_):
            self.result(state['wrapper'], state['request'])
        with patch.object(r, 'cli', return_value=['fake']), \
                patch.object(r, 'query', side_effect=self.dispatch_query(dispatch)) as query, \
                patch.object(r.time, 'monotonic', side_effect=[0, 0]), \
                patch.object(r.time, 'sleep', side_effect=advance) as sleep, \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = self.run_job()
        self.assertEqual(result['status'], 'passed')
        self.assertNotEqual(result['token'], 'old-token')
        sleep.assert_called_once()
        self.assertEqual(query.call_count, 2)

    def test_malformed_or_nonobject_result_waits_for_valid_result(self):
        for content in ['{incomplete', '[]']:
            with self.subTest(content=content):
                state = {}
                def dispatch(wrapper, request):
                    state.update(wrapper=wrapper, request=request)
                    wrapper.with_name('result.json').write_text(content, encoding='utf-8')
                def advance(_):
                    self.result(state['wrapper'], state['request'])
                with patch.object(r, 'cli', return_value=['fake']), \
                        patch.object(r, 'query', side_effect=self.dispatch_query(dispatch)), \
                        patch.object(r.time, 'monotonic', side_effect=[0, 0]), \
                        patch.object(r.time, 'sleep', side_effect=advance), \
                        contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(self.run_job()['status'], 'passed')

    def test_matching_failure_is_reported_with_captured_streams(self):
        def dispatch(wrapper, request):
            self.result(wrapper, request, status='failed', error='原生脚本失败')
        out, err = io.StringIO(), io.StringIO()
        with patch.object(r, 'cli', return_value=['fake']), \
                patch.object(r, 'query', side_effect=self.dispatch_query(dispatch)), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with self.assertRaisesRegex(RuntimeError, '原生脚本失败'):
                self.run_job()
        self.assertEqual(out.getvalue(), '完成\n')
        self.assertEqual(err.getvalue(), '警告\n')

    def test_timeout_identifies_request_without_resubmitting(self):
        with patch.object(r, 'cli', return_value=['fake']), \
                patch.object(r, 'query', side_effect=self.dispatch_query(lambda *_: None)) as query, \
                patch.object(r.time, 'monotonic', side_effect=[0, 2]):
            with self.assertRaisesRegex(TimeoutError, r'No completion acknowledgement for token .*\. Inspect .*\.dispatch-.*may still be executing'):
                self.run_job()
        self.assertEqual(query.call_count, 2)

    def test_cli_timeout_keeps_polling_same_token_without_resubmitting(self):
        state = {}
        def dispatch(wrapper, request):
            state.update(wrapper=wrapper, request=request)
            raise subprocess.TimeoutExpired(['fake'], .01)
        def advance(_):
            self.result(state['wrapper'], state['request'])
        err = io.StringIO()
        with patch.object(r, 'cli', return_value=['fake']), \
                patch.object(r, 'query', side_effect=self.dispatch_query(dispatch)) as query, \
                patch.object(r.time, 'monotonic', side_effect=[0, .2]), \
                patch.object(r.time, 'sleep', side_effect=advance), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertEqual(self.run_job()['status'], 'passed')
        self.assertIn('without resubmitting', err.getvalue())
        self.assertEqual(query.call_count, 2)

    def test_terminal_result_is_read_even_when_dispatch_used_deadline(self):
        def dispatch(wrapper, request):
            self.result(wrapper, request)
            raise subprocess.TimeoutExpired(['fake'], 1)
        with patch.object(r, 'cli', return_value=['fake']), \
                patch.object(r, 'query', side_effect=self.dispatch_query(dispatch)), \
                patch.object(r.time, 'monotonic', return_value=0) as clock, \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.run_job()['status'], 'passed')
        clock.assert_called_once()


class WrapperTest(unittest.TestCase):
    def execute(self, expected, doc, script="print('完成')\n", optimize=0):
        with tempfile.TemporaryDirectory(prefix='Rhino wrapper 测试 ') as temp:
            work = pathlib.Path(temp)
            runner = work / 'runner.py'
            source = work / '脚本.py'
            source.write_text(script, encoding='utf-8')
            request = {'token': 'current-token', 'expected_doc': expected, 'script': str(source),
                       'job': {'message': '作业参数'}, 'output': str(work)}
            (work / 'request.json').write_text(json.dumps(request, ensure_ascii=False), encoding='utf-8')
            rhino = types.SimpleNamespace(RhinoDoc=types.SimpleNamespace(ActiveDoc=doc))
            with patch.dict(sys.modules, {'Rhino': rhino}), contextlib.redirect_stdout(io.StringIO()):
                exec(compile(r.WRAPPER, str(runner), 'exec', optimize=optimize), {'__file__': str(runner)})
            return json.loads((work / 'result.json').read_text(encoding='utf-8'))

    def document(self, path, count=0):
        return types.SimpleNamespace(Path=path, Objects=types.SimpleNamespace(Count=count))

    def test_wrong_document_stops_script_even_under_python_optimization(self):
        result = self.execute('/expected.3dm', self.document('/other.3dm'),
                              "print('SHOULD NOT RUN')\n", optimize=2)
        self.assertEqual(result['status'], 'failed')
        self.assertIn('Active document mismatch', result['error'])
        self.assertEqual(result['stdout'], '')

    def test_none_guard_accepts_no_document_or_empty_unnamed_document(self):
        for doc in [None, self.document('')]:
            with self.subTest(doc=doc):
                self.assertEqual(self.execute('@none', doc)['status'], 'passed')

    def test_none_guard_rejects_named_or_nonempty_document(self):
        for doc in [self.document('/existing.3dm'), self.document('', 1)]:
            with self.subTest(doc=doc):
                result = self.execute('@none', doc, optimize=2)
                self.assertEqual(result['status'], 'failed')
                self.assertIn('Expected no document or an empty unnamed document', result['error'])

    def test_valid_document_preserves_job_and_unicode_streams(self):
        path = str(pathlib.Path(tempfile.gettempdir()) / '当前模型.3dm')
        script = "import sys\nprint(JOB['message'])\nprint(GUARDED_DOC.Path)\nprint('诊断信息',file=sys.stderr)\n"
        result = self.execute(path, self.document(path), script)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['token'], 'current-token')
        self.assertEqual(result['stdout'], '作业参数\n' + path + '\n')
        self.assertEqual(result['stderr'], '诊断信息\n')

    def test_script_failure_preserves_stdout_stderr_and_traceback(self):
        script = "import sys\nprint('开始')\nprint('失败详情',file=sys.stderr)\nraise RuntimeError('测试异常')\n"
        result = self.execute('@none', None, script)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['stdout'], '开始\n')
        self.assertEqual(result['stderr'], '失败详情\n')
        self.assertIn('测试异常', result['error'])


if __name__ == '__main__':
    unittest.main()
