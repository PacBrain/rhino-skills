"""Offline validation/restoration tests; no native Rhino rendering is performed."""
import importlib.util
import pathlib
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/rhino-modeling/scripts/capture_views.py'


class Point:
    def __init__(self, x, y, z):
        self.X, self.Y, self.Z = x, y, z

    def coordinates(self):
        return (self.X, self.Y, self.Z)


class Viewport:
    def __init__(self):
        self.projection = 'original perspective'
        self.CameraLocation = Point(11, 22, 33)
        self.CameraTarget = Point(1, 2, 3)
        self.CameraUp = Point(0, 1, 0)
        self.DisplayMode = types.SimpleNamespace(Id='original-mode')
        self.ConstructionGridVisible = True
        self.ConstructionAxesVisible = True
        self.restored_projections = []
        self.restored_targets = []

    def ChangeToParallelProjection(self, preserve):
        self.projection = 'parallel'

    def SetCameraLocations(self, target, camera):
        self.CameraTarget, self.CameraLocation = target, camera

    def ZoomBoundingBox(self, bounds):
        return True

    def SetViewProjection(self, snapshot, update_target):
        self.restored_projections.append(snapshot)
        self.projection = snapshot.projection
        self.CameraLocation = snapshot.camera
        self.CameraUp = snapshot.up
        # Deliberately leave target to the separate SetCameraTarget restoration.
        return True

    def SetCameraTarget(self, target, update_location):
        self.restored_targets.append(target)
        self.CameraTarget = target


class Projection:
    def __init__(self, viewport):
        self.projection = viewport.projection
        self.camera = viewport.CameraLocation
        self.up = viewport.CameraUp
        self.disposed = False

    def Dispose(self):
        self.disposed = True


class Bitmap:
    def __init__(self, fail=False):
        self.fail = fail
        self.disposed = False
        self.saved = []

    def Save(self, path, image_format):
        self.saved.append(pathlib.Path(path))
        pathlib.Path(path).write_bytes(b'offline bitmap placeholder')
        if self.fail:
            raise OSError('simulated bitmap save failure')

    def Dispose(self):
        self.disposed = True


class CaptureTest(unittest.TestCase):
    def setUp(self):
        self.capture = types.SimpleNamespace(CaptureToBitmap=Mock())
        self.shaded = types.SimpleNamespace(Id='shaded-mode')
        self.snapshots = []
        def snapshot(viewport):
            saved = Projection(viewport)
            self.snapshots.append(saved)
            return saved
        self.rhino = types.SimpleNamespace(
            Geometry=types.SimpleNamespace(Point3d=Point, Vector3d=Point,
                                           BoundingBox=lambda low, high: (low, high)),
            Display=types.SimpleNamespace(
                DisplayModeDescription=types.SimpleNamespace(
                    ShadedId='shaded-mode', GetDisplayMode=Mock(return_value=self.shaded)),
                ViewCapture=Mock(return_value=self.capture)),
            DocObjects=types.SimpleNamespace(ViewportInfo=snapshot),
            RhinoApp=types.SimpleNamespace(Wait=Mock()),
        )
        system = types.ModuleType('System')
        system.Guid = lambda value: value
        drawing = types.ModuleType('System.Drawing')
        imaging = types.ModuleType('System.Drawing.Imaging')
        imaging.ImageFormat = types.SimpleNamespace(Png='png')
        drawing.Imaging = imaging
        system.Drawing = drawing
        spec = importlib.util.spec_from_file_location('offline_capture', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules', {'Rhino': self.rhino, 'System': system,
                                      'System.Drawing': drawing, 'System.Drawing.Imaging': imaging}):
            spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory(prefix='Rhino capture 测试 ')
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve()
        self.output = self.root / 'screenshots'

    def item(self, **changes):
        item = {'filename': '正面.png', 'camera': [10, -10, 10], 'target': [0, 0, 0],
                'up': [0, 0, 1], 'bounds': [[-1, -1, -1], [1, 1, 1]]}
        item.update(changes)
        return item

    def job(self, **changes):
        job = {'views': [self.item()]}
        job.update(changes)
        return job

    def test_empty_or_invalid_view_collections_rejected(self):
        for job in [None, [], {}, {'views': []}, {'views': 'front'}, {'views': [None]}]:
            with self.subTest(job=job), self.assertRaises(ValueError):
                self.module.validate(job)

    def test_nonfinite_or_nonnumeric_coordinates_rejected(self):
        for field in ['camera', 'target', 'up']:
            for value in [float('nan'), float('inf'), -float('inf'), True, '1']:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, 'finite coordinates'):
                    self.module.validate({'views': [self.item(**{field: [value, 1, 1]})]})
        for coordinates in [[0, 1], [0, 1, 2, 3], None]:
            with self.subTest(coordinates=coordinates), self.assertRaises(ValueError):
                self.module.validate({'views': [self.item(camera=coordinates)]})

    def test_zero_or_parallel_camera_up_and_coincident_camera_rejected(self):
        cases = [self.item(camera=[0, 0, 0]), self.item(up=[0, 0, 0]),
                 self.item(camera=[0, 0, 10], up=[0, 0, 1]),
                 self.item(camera=[0, 0, 10], up=[0, 0, -1])]
        for item in cases:
            with self.subTest(item=item), self.assertRaisesRegex(ValueError, 'Camera must differ'):
                self.module.validate({'views': [item]})

    def test_invalid_width_height_or_pixel_budget_rejected(self):
        for field in ['width', 'height']:
            for value in [0, -1, 16385, True, 2.5, '100', None, float('inf'), float('nan')]:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.module.validate(self.job(**{field: value}))
        with self.assertRaisesRegex(ValueError, '64 million pixels'):
            self.module.validate(self.job(width=10000, height=10000))

    def test_invalid_bounds_or_filename_rejected(self):
        for bounds in [None, [[0, 0, 0]], [[0, 0, 0], [0, 0, 0]],
                       [[1, 0, 0], [0, 1, 1]], [[0, 0, 0], [1, float('inf'), 1]]]:
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                self.module.validate({'views': [self.item(bounds=bounds)]})
        for filename in [None, '../escape.png', 'front.jpg', 'NUL.png']:
            with self.subTest(filename=filename), self.assertRaises(ValueError):
                self.module.validate({'views': [self.item(filename=filename)]})

    def test_valid_view_uses_default_size_and_up(self):
        item = self.item()
        del item['up']
        width, height, views = self.module.validate({'views': [item]})
        self.assertEqual((width, height), (2000, 1400))
        self.assertEqual(views[0]['up'], [0., 0., 1.])
        self.assertEqual(views[0]['filename'], '正面.png')

    def document(self):
        viewport = Viewport()
        view = types.SimpleNamespace(ActiveViewport=viewport)
        doc = types.SimpleNamespace(Path=str(self.root / '模型.3dm'), RuntimeSerialNumber=123,
                                    Views=types.SimpleNamespace(ActiveView=view, Redraw=Mock()))
        original = dict(projection=viewport.projection, camera=viewport.CameraLocation,
                        target=viewport.CameraTarget, up=viewport.CameraUp,
                        mode=viewport.DisplayMode, grid=viewport.ConstructionGridVisible,
                        axes=viewport.ConstructionAxesVisible)
        return doc, viewport, original

    def assert_restored_without_outputs(self, viewport, original):
        self.assertEqual(viewport.projection, original['projection'])
        self.assertEqual(viewport.CameraLocation.coordinates(), original['camera'].coordinates())
        self.assertIs(viewport.CameraTarget, original['target'])
        self.assertEqual(viewport.CameraUp.coordinates(), original['up'].coordinates())
        self.assertIs(viewport.DisplayMode, original['mode'])
        self.assertEqual(viewport.ConstructionGridVisible, original['grid'])
        self.assertEqual(viewport.ConstructionAxesVisible, original['axes'])
        self.assertEqual(viewport.restored_targets, [original['target']])
        self.assertEqual(viewport.restored_projections, self.snapshots)
        self.assertEqual(len(self.snapshots), 1)
        self.assertTrue(self.snapshots[0].disposed)
        self.assertFalse((self.output / 'views.json').exists())
        self.assertEqual(list(self.output.iterdir()), [])

    def test_empty_bitmap_restores_viewport_and_publishes_nothing(self):
        self.capture.CaptureToBitmap.return_value = None
        doc, viewport, original = self.document()
        with self.assertRaisesRegex(RuntimeError, 'Native ViewCapture failed'):
            self.module.main(self.job(), self.output, doc)
        self.assert_restored_without_outputs(viewport, original)

    def test_save_failure_disposes_bitmap_restores_viewport_and_removes_partial_png(self):
        bitmap = Bitmap(fail=True)
        self.capture.CaptureToBitmap.return_value = bitmap
        doc, viewport, original = self.document()
        with self.assertRaisesRegex(OSError, 'simulated bitmap save failure'):
            self.module.main(self.job(), self.output, doc)
        self.assertTrue(bitmap.disposed)
        self.assertEqual(len(bitmap.saved), 1)
        self.assertFalse(bitmap.saved[0].exists())
        self.assert_restored_without_outputs(viewport, original)

    def test_later_capture_failure_removes_earlier_staged_png_and_restores_viewport(self):
        first = Bitmap()
        self.capture.CaptureToBitmap.side_effect = [first, None]
        doc, viewport, original = self.document()
        job = self.job(views=[self.item(), self.item(filename='侧面.png', camera=[10, 0, 0])])
        with self.assertRaisesRegex(RuntimeError, 'Native ViewCapture failed'):
            self.module.main(job, self.output, doc)
        self.assertTrue(first.disposed)
        self.assertEqual(len(first.saved), 1)
        self.assertFalse(first.saved[0].exists())
        self.assertEqual(self.capture.CaptureToBitmap.call_count, 2)
        self.assert_restored_without_outputs(viewport, original)


if __name__ == '__main__':
    unittest.main()
