"""Offline helper contracts; stubs do not establish Rhino geometry correctness."""
import importlib.util
import pathlib
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/rhino-modeling/scripts/native_ops.py'


class Collection(list):
    @property
    def Count(self):
        return len(self)


def point(x, y, z):
    return types.SimpleNamespace(X=x, Y=y, Z=z)


class Mesh:
    CreateFromBrep = Mock()

    def __init__(self, orientation=1, solid=True, triangles=True, flip_succeeds=True):
        self.IsValid = True
        self.IsClosed = True
        self.IsSolid = solid
        self.orientation = orientation
        self.flip_succeeds = flip_succeeds
        self.flips = []
        self.Vertices = Collection([point(0, 0, 0), point(1, 0, 0), point(0, 1, 0), point(0, 0, 1)])
        self.Faces = Collection([types.SimpleNamespace(IsTriangle=triangles, A=0, B=1, C=2, D=3)])
        self.FaceNormals = Collection([point(0, 0, 1)])
        self.FaceNormals.ComputeFaceNormals = Mock()

    def IsManifold(self):
        return True

    def SolidOrientation(self):
        return self.orientation

    def Flip(self, *args):
        self.flips.append(args)
        if self.flip_succeeds:
            self.orientation *= -1

    def GetBoundingBox(self, accurate):
        return types.SimpleNamespace(IsValid=True, Min=point(0, 0, 0), Max=point(1, 1, 1))


class Brep:
    pass


class NativeHelpersTest(unittest.TestCase):
    def setUp(self):
        self.geometry = types.SimpleNamespace(Mesh=Mesh, Brep=Brep, MeshingParameters=Mock())
        self.file3dm = types.SimpleNamespace(Read=Mock())
        self.rhino = types.SimpleNamespace(
            Geometry=self.geometry,
            UnitSystem=types.SimpleNamespace(Millimeters='mm'),
            FileIO=types.SimpleNamespace(File3dm=self.file3dm),
            RhinoApp=types.SimpleNamespace(Version='offline-stub'),
        )
        threading = types.ModuleType('System.Threading')
        threading.CancellationToken = Mock()
        system = types.ModuleType('System')
        system.Threading = threading
        spec = importlib.util.spec_from_file_location('offline_native_helpers', SCRIPT)
        self.op = importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules', {'Rhino': self.rhino, 'System': system, 'System.Threading': threading}):
            spec.loader.exec_module(self.op)
        self.temp = tempfile.TemporaryDirectory(prefix='Rhino helper 测试 ')
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve()

    def test_orientation_zero_rejected(self):
        for solid in [False, True]:
            with self.subTest(solid=solid):
                mesh = Mesh(orientation=0, solid=solid)
                with self.assertRaises(ValueError):
                    self.op.check_mesh_solid(mesh, allow_flip=True)
                self.assertEqual(mesh.flips, [])

    def test_inward_mesh_rejected_without_authorized_flip(self):
        mesh = Mesh(orientation=-1)
        with self.assertRaisesRegex(ValueError, 'outward solid'):
            self.op.check_mesh_solid(mesh)
        self.assertEqual(mesh.flips, [])
        self.assertEqual(mesh.orientation, -1)

    def test_inward_mesh_is_flipped_and_rechecked_when_allowed(self):
        mesh = Mesh(orientation=-1)
        report = self.op.check_mesh_solid(mesh, allow_flip=True)
        self.assertEqual(mesh.flips, [(True, True, True)])
        self.assertEqual(report['orientation'], 1)
        self.assertTrue(report['solid'])

    def test_unsuccessful_flip_cannot_pass_solid_validation(self):
        mesh = Mesh(orientation=-1, flip_succeeds=False)
        with self.assertRaisesRegex(ValueError, 'orientation=-1'):
            self.op.check_mesh_solid(mesh, allow_flip=True)
        self.assertEqual(len(mesh.flips), 1)

    def test_outward_mesh_requires_no_flip(self):
        mesh = Mesh()
        self.assertEqual(self.op.check_mesh_solid(mesh)['orientation'], 1)
        self.assertEqual(mesh.flips, [])

    def test_invalid_tolerance_rejected_before_meshing_api(self):
        for value in [0, -1, float('nan'), float('inf'), -float('inf'), True, None, '.05']:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.op.make_mesh(Brep(), tolerance=value)
        self.geometry.MeshingParameters.assert_not_called()

    def test_invalid_minimum_edge_rejected_before_meshing_api(self):
        for value in [-1, float('nan'), float('inf'), -float('inf'), True, None, '0']:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.op.make_mesh(Brep(), minimum_edge_length=value)
        self.geometry.MeshingParameters.assert_not_called()

    def test_zero_minimum_edge_is_accepted_and_empty_meshing_fails(self):
        self.geometry.MeshingParameters.return_value = types.SimpleNamespace()
        with patch.object(Mesh, 'CreateFromBrep', return_value=[]):
            with self.assertRaisesRegex(RuntimeError, 'Meshing returned no results'):
                self.op.make_mesh(Brep(), tolerance=.05, minimum_edge_length=0)
        parameters = self.geometry.MeshingParameters.return_value
        self.assertEqual(parameters.MinimumEdgeLength, 0)
        self.assertEqual(parameters.Tolerance, .05)

    def test_stl_rejects_quads_before_creating_output(self):
        mesh = Mesh(triangles=False)
        target = self.root / '四边面.stl'
        with self.assertRaisesRegex(ValueError, 'triangulated'):
            self.op.write_stl(mesh, target)
        self.assertFalse(target.exists())
        mesh.FaceNormals.ComputeFaceNormals.assert_not_called()

    def test_stl_does_not_overwrite_existing_output(self):
        target = self.root / 'existing.stl'
        target.write_bytes(b'keep this file')
        with self.assertRaises(FileExistsError):
            self.op.write_stl(Mesh(), target)
        self.assertEqual(target.read_bytes(), b'keep this file')

    def test_stl_rejects_inward_mesh_before_creating_output(self):
        mesh = Mesh(orientation=-1)
        target = self.root / 'inward.stl'
        with self.assertRaisesRegex(ValueError, 'outward solid'):
            self.op.write_stl(mesh, target)
        self.assertFalse(target.exists())
        self.assertEqual(mesh.flips, [])

    def model(self, geometries, units='mm'):
        return types.SimpleNamespace(
            Settings=types.SimpleNamespace(ModelUnitSystem=units),
            Objects=[types.SimpleNamespace(Geometry=geometry) for geometry in geometries],
            Dispose=Mock(),
        )

    def source(self):
        source = self.root / '源 模型.3dm'
        source.write_bytes(b'offline model placeholder')
        return source

    def test_export_rejects_mixed_empty_or_nonbrep_sources_before_geometry_work(self):
        source = self.source()
        cases = [[], [object()], [Brep(), Mesh()], [Brep(), object()], [Brep(), Brep()]]
        for index, geometries in enumerate(cases):
            with self.subTest(case=index):
                model = self.model(geometries)
                self.file3dm.Read.return_value = model
                output = self.root / ('output-' + str(index))
                with patch.object(self.op, 'check_solid') as check, patch.object(self.op, 'make_mesh') as make:
                    with self.assertRaisesRegex(ValueError, 'exactly one Brep object and no other objects'):
                        self.op.export_body(source, output)
                    check.assert_not_called()
                    make.assert_not_called()
                model.Dispose.assert_called_once()
                self.assertEqual(list(output.iterdir()), [])

    def test_export_rejects_non_mm_source_before_geometry_work(self):
        model = self.model([Brep()], units='inches')
        self.file3dm.Read.return_value = model
        with patch.object(self.op, 'check_solid') as check:
            with self.assertRaisesRegex(ValueError, 'explicit mm sources'):
                self.op.export_body(self.source(), self.root / 'output')
            check.assert_not_called()
        model.Dispose.assert_called_once()

    def test_single_brep_selection_reaches_validation_and_disposes_on_failure(self):
        brep = Brep()
        model = self.model([brep])
        self.file3dm.Read.return_value = model
        with patch.object(self.op, 'check_solid', side_effect=ValueError('invalid source solid')) as check:
            with self.assertRaisesRegex(ValueError, 'invalid source solid'):
                self.op.export_body(self.source(), self.root / 'output')
        check.assert_called_once_with(brep)
        model.Dispose.assert_called_once()


if __name__ == '__main__':
    unittest.main()
