"""Portable job validation, fresh imports and staged output; no Rhino dependency."""
import contextlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import types
import uuid


def load_sibling(caller, filename):
    """Read source afresh without sys.modules or timestamp-based bytecode caches."""
    path = Path(caller).resolve().with_name(filename)
    module = types.ModuleType('_rhino_job_' + uuid.uuid4().hex)
    module.__file__ = str(path)
    exec(compile(path.read_text(encoding='utf-8'), str(path), 'exec'), module.__dict__)
    return module


def finite_number(value, label, minimum=0, inclusive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(label + ' must be a finite number')
    value = float(value)
    if not math.isfinite(value) or (value < minimum if inclusive else value <= minimum):
        raise ValueError(label + ' is outside its allowed range')
    return value


def source_paths(values):
    if not isinstance(values, list) or not values:
        raise ValueError('sources must be a nonempty list of absolute 3DM paths')
    paths = []
    for value in values:
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise ValueError('Each source must be an absolute path')
        path = Path(value).resolve()
        if path.suffix.lower() != '.3dm' or not path.is_file():
            raise ValueError('Expected an existing 3DM source: ' + str(path))
        paths.append(path)
    if len(set(paths)) != len(paths):
        raise ValueError('Duplicate source paths')
    return paths


def output_name(name):
    if not isinstance(name, str) or not name or name in ('.', '..'):
        raise ValueError('Output must have a simple filename')
    if any(c in name for c in '\\/:<>"|?*') or any(ord(c) < 32 for c in name):
        raise ValueError('Output filename is not portable: ' + name)
    if name.endswith((' ', '.')) or name.split('.')[0].upper() in (
        {'CON', 'PRN', 'AUX', 'NUL'} | {'COM' + str(i) for i in range(1, 10)}
        | {'LPT' + str(i) for i in range(1, 10)}
    ):
        raise ValueError('Output filename is not portable: ' + name)
    return name


def write_json(path, value):
    payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(payload)


@contextlib.contextmanager
def staged_outputs(output, names):
    """Validate all files first; publish without overwrite, rolling back on error.

    A group of flat files cannot be atomically renamed as one filesystem operation.
    Each file is exclusively created only after validation; exceptions roll back
    files created by this call. A process crash can still interrupt publication.
    Consumers must wait for the dispatch completion acknowledgement.
    """
    output = Path(output)
    names = [output_name(name) for name in names]
    if not names or len({name.casefold() for name in names}) != len(names):
        raise ValueError('Output filenames must be nonempty and unique across platforms')
    output.mkdir(parents=True, exist_ok=True)
    existing = {p.name.casefold() for p in output.iterdir()}
    if existing.intersection(name.casefold() for name in names):
        raise FileExistsError('An output already exists; use a new output directory')
    stage = Path(tempfile.mkdtemp(prefix='.stage-', dir=str(output)))
    published = []
    try:
        yield stage
        actual = {p.name for p in stage.iterdir()}
        if actual != set(names) or not all((stage / name).is_file() for name in names):
            raise RuntimeError('Staged outputs do not match the expected artifact set')
        for name in names:
            destination = output / name
            # Exclusive creation works without symlink/hardlink privileges on Windows.
            with destination.open('xb') as target:
                published.append(destination)
                with (stage / name).open('rb') as source:
                    shutil.copyfileobj(source, target)
                target.flush()
                os.fsync(target.fileno())
    except BaseException:
        for path in reversed(published):
            path.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(stage)
