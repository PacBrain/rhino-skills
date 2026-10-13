#! python 3
"""Capture guarded native viewports, with staged files and restoration on failure."""
import json
import math
from pathlib import Path
import types
import uuid

import Rhino
from System import Guid
from System.Drawing.Imaging import ImageFormat

G = Rhino.Geometry
_support_path = Path(__file__).resolve().with_name('job_support.py')
support = types.ModuleType('_rhino_support_' + uuid.uuid4().hex)
support.__file__ = str(_support_path)
exec(compile(_support_path.read_text(encoding='utf-8'), str(_support_path), 'exec'), support.__dict__)


def vector3(value, label):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(label + ' must have three finite coordinates')
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in value):
        raise ValueError(label + ' must have three finite coordinates')
    return [float(v) for v in value]


def validate(job):
    if not isinstance(job, dict) or not isinstance(job.get('views'), list) or not job['views']:
        raise ValueError('views must be a nonempty list')
    width, height = job.get('width', 2000), job.get('height', 1400)
    for size in (width, height):
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0 or size > 16384:
            raise ValueError('Capture width/height must be integers from 1 to 16384')
    if width * height > 64000000:
        raise ValueError('Capture may contain at most 64 million pixels')
    views = []
    for item in job['views']:
        if not isinstance(item, dict):
            raise ValueError('Each view must be an object')
        name = support.output_name(item.get('filename'))
        if not name.lower().endswith('.png'):
            raise ValueError('Each view needs a PNG filename')
        camera = vector3(item.get('camera'), 'camera')
        target = vector3(item.get('target'), 'target')
        up = vector3(item.get('up', [0, 0, 1]), 'up')
        direction = [b - a for a, b in zip(camera, target)]
        cross = [direction[1] * up[2] - direction[2] * up[1],
                 direction[2] * up[0] - direction[0] * up[2],
                 direction[0] * up[1] - direction[1] * up[0]]
        if not any(direction) or not any(up) or not any(cross):
            raise ValueError('Camera must differ from target and up must not be parallel to the view direction')
        bounds = item.get('bounds')
        if not isinstance(bounds, list) or len(bounds) != 2:
            raise ValueError('bounds must contain minimum and maximum coordinates')
        bounds = [vector3(value, 'bounds') for value in bounds]
        if any(a > b for a, b in zip(*bounds)) or bounds[0] == bounds[1]:
            raise ValueError('bounds must form a nonempty ordered box')
        views.append({'filename': name, 'camera': camera, 'target': target, 'up': up, 'bounds': bounds})
    return width, height, views


def coordinates(value):
    return [float(value.X), float(value.Y), float(value.Z)]


def main(job, output, doc):
    width, height, views = validate(job)
    if doc is None or not doc.Path or doc.Views.ActiveView is None:
        raise RuntimeError('Open the intended named document with a viewport before capture')
    mode_id = Guid(job['display_mode_id']) if job.get('display_mode_id') else Rhino.Display.DisplayModeDescription.ShadedId
    mode = Rhino.Display.DisplayModeDescription.GetDisplayMode(mode_id)
    if mode is None:
        raise ValueError('Unknown display_mode_id')
    reports = []
    with support.staged_outputs(output, [item['filename'] for item in views] + ['views.json']) as stage:
        view = doc.Views.ActiveView
        viewport = view.ActiveViewport
        projection = Rhino.DocObjects.ViewportInfo(viewport)
        old_target = viewport.CameraTarget
        old_mode = viewport.DisplayMode
        old_grid = viewport.ConstructionGridVisible
        old_axes = viewport.ConstructionAxesVisible
        capture_error = None
        try:
            viewport.DisplayMode = mode
            viewport.ConstructionGridVisible = False
            viewport.ConstructionAxesVisible = False
            for item in views:
                viewport.ChangeToParallelProjection(True)
                viewport.CameraUp = G.Vector3d(*item['up'])
                viewport.SetCameraLocations(G.Point3d(*item['target']), G.Point3d(*item['camera']))
                box = G.BoundingBox(G.Point3d(*item['bounds'][0]), G.Point3d(*item['bounds'][1]))
                if not viewport.ZoomBoundingBox(box):
                    raise RuntimeError('Could not frame capture bounds')
                doc.Views.Redraw()
                Rhino.RhinoApp.Wait()
                capture = Rhino.Display.ViewCapture()
                capture.Width, capture.Height = width, height
                capture.DrawGrid, capture.DrawAxes = False, False
                bitmap = capture.CaptureToBitmap(view)
                if bitmap is None:
                    raise RuntimeError('Native ViewCapture failed')
                try:
                    bitmap.Save(str(stage / item['filename']), ImageFormat.Png)
                finally:
                    bitmap.Dispose()
                reports.append({'file': item['filename'], 'source_document': Path(doc.Path).name,
                                'document_serial_number': int(doc.RuntimeSerialNumber),
                                'method': 'Rhino native ViewCapture', 'width': width, 'height': height,
                                'camera': coordinates(viewport.CameraLocation),
                                'target': coordinates(viewport.CameraTarget),
                                'up': coordinates(viewport.CameraUp), 'requested_view': item,
                                'display_mode_id': str(mode.Id)})
        except BaseException as error:
            capture_error = error
            raise
        finally:
            errors = []
            try:
                if not viewport.SetViewProjection(projection, False):
                    errors.append('projection restore failed')
            except Exception as error:
                errors.append(str(error))
            restorations = [lambda: viewport.SetCameraTarget(old_target, False),
                            lambda: setattr(viewport, 'DisplayMode', old_mode),
                            lambda: setattr(viewport, 'ConstructionGridVisible', old_grid),
                            lambda: setattr(viewport, 'ConstructionAxesVisible', old_axes),
                            lambda: doc.Views.Redraw(), lambda: projection.Dispose()]
            for restore in restorations:
                try:
                    restore()
                except Exception as error:
                    errors.append(str(error))
            if errors:
                raise RuntimeError('Viewport restoration failed: ' + '; '.join(errors)) from capture_error
        support.write_json(stage / 'views.json', reports)
    return reports


if __name__ == '__main__':
    print(json.dumps(main(JOB, OUT_DIR, GUARDED_DOC), ensure_ascii=False, allow_nan=False))
