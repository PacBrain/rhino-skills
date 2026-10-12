#! python 3
"""Run with rhino_run.py --script THIS_FILE --job a JSON synthetic job.

The dispatcher must guard an explicitly chosen document or @none. This helper
uses only headless documents and never changes the guarded active document.
It requires Rhino 8.11+ with StartScriptServer active; no external Python geometry.
"""
from pathlib import Path
import json
import types

path = Path(__file__).resolve().parents[1] / 'skills/rhino-modeling/scripts/native_job.py'
module = types.ModuleType('_native_integration_job')
module.__file__ = str(path)
exec(compile(path.read_text(encoding='utf-8'), str(path), 'exec'), module.__dict__)
job = dict(JOB)
job['mode'] = 'synthetic'
print(json.dumps(module.main(job, OUT_DIR), ensure_ascii=False, allow_nan=False))
