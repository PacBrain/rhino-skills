#! python 3
"""Run through rhino_run.py: inspect, export, or isolated synthetic integration tests."""
import json
from pathlib import Path
import tempfile
import types
import uuid

_support_path = Path(__file__).resolve().with_name('job_support.py')
support = types.ModuleType('_rhino_support_' + uuid.uuid4().hex)
support.__file__ = str(_support_path)
exec(compile(_support_path.read_text(encoding='utf-8'), str(_support_path), 'exec'), support.__dict__)
op = support.load_sibling(__file__, 'native_ops.py')
Rhino = op.Rhino
G = op.G


def expect_rejection(function, label):
    try:
        function()
    except ValueError:
        return True
    raise RuntimeError(label + ' was not rejected')


def synthetic(job, output):
    dimensions = job.get('dimensions_mm', [24, 36, 18])
    if not isinstance(dimensions, list) or len(dimensions) != 3:
        raise ValueError('dimensions_mm must contain three positive finite numbers')
    dimensions = [support.finite_number(value, 'dimension_mm') for value in dimensions]
    tolerance = support.finite_number(job.get('mesh_tolerance_mm', .05), 'mesh_tolerance_mm')
    box_name = 'synthetic box 测试.3dm'
    sphere_name = 'synthetic sphere.3dm'
    names = [box_name, sphere_name] + op.export_names(Path(box_name)) + op.export_names(Path(sphere_name))
    names += ['synthetic.step', 'synthetic_validation.json']
    with support.staged_outputs(output, names) as stage:
        box = G.BoundingBox(G.Point3d.Origin, G.Point3d(*dimensions)).ToBrep()
        op.check_solid(box)
        mirror = box.DuplicateBrep()
        if not mirror.Transform(G.Transform.Mirror(G.Plane.WorldYZ)):
            raise RuntimeError('Mirror transform failed')
        if mirror.SolidOrientation == G.BrepSolidOrientation.Inward:
            mirror.Flip()
        op.check_solid(mirror)
        broken = box.DuplicateBrep()
        broken.Faces.RemoveAt(0)
        missing_face = expect_rejection(lambda: op.check_solid(broken), 'Missing-face Brep')
        source = stage / box_name
        op.write_3dm(box, source)
        box_result = op._export_body_to_stage(source, stage, tolerance)
        sphere = G.Sphere(G.Point3d.Origin, min(dimensions) / 4).ToBrep()
        op.check_solid(sphere)
        sphere_source = stage / sphere_name
        op.write_3dm(sphere, sphere_source)
        sphere_result = op._export_body_to_stage(sphere_source, stage, tolerance)
        step = op.step_roundtrip(source, stage / 'synthetic.step', dimensions)
        mesh, _ = op.make_mesh(box, tolerance)
        mesh.Flip(True, True, True)
        inward = expect_rejection(lambda: op.check_mesh_solid(mesh), 'Inward mesh')
        op.check_mesh_solid(mesh, allow_flip=True)
        with tempfile.TemporaryDirectory(prefix='negative-fixtures-', dir=str(stage)) as temporary:
            fixtures = Path(temporary)
            mixed = fixtures / 'mixed.3dm'
            model = Rhino.FileIO.File3dm()
            try:
                model.Settings.ModelUnitSystem = Rhino.UnitSystem.Millimeters
                model.Objects.AddBrep(box, Rhino.DocObjects.ObjectAttributes())
                model.Objects.AddMesh(mesh, Rhino.DocObjects.ObjectAttributes())
                if not model.Write(str(mixed), 8):
                    raise RuntimeError('Could not write mixed fixture')
            finally:
                model.Dispose()
            inventory = op.inspect_source(mixed)
            if inventory['object_count'] != 2:
                raise RuntimeError('Inspect did not inventory mixed objects')
            destination = fixtures / 'rejected-output'
            mixed_rejected = expect_rejection(lambda: op.export_body(mixed, destination), 'Mixed source')
            if destination.exists() and any(destination.iterdir()):
                raise RuntimeError('Rejected export left partial artifacts')
            inch_source = fixtures / 'inch.3dm'
            op.write_3dm(box, inch_source, Rhino.UnitSystem.Inches)
            units_rejected = expect_rejection(lambda: op.export_body(inch_source, destination), 'Non-mm source')
            before = op.sha256(mixed)
            op.inspect_source(mixed)
            if op.sha256(mixed) != before:
                raise RuntimeError('Read-only inspect changed the source')
        report = {'status': 'passed', 'rhino_version': str(Rhino.RhinoApp.Version),
                  'closed_solid': True, 'mirrored_outward': True, 'missing_face_rejected': missing_face,
                  'inward_mesh_rejected_and_corrected': inward, 'mixed_source_rejected': mixed_rejected,
                  'non_mm_source_rejected': units_rejected, 'inspection_source_unchanged': True,
                  'step_roundtrip': step, 'exports': [box_result, sphere_result],
                  'physical_test': 'not_run', 'viewport_capture': 'not_run'}
        support.write_json(stage / 'synthetic_validation.json', report)
    return report


def main(job, output):
    if not isinstance(job, dict):
        raise ValueError('Job must be an object')
    mode = job.get('mode')
    if mode == 'inspect':
        sources = support.source_paths(job.get('sources'))
        names = [source.stem + '.inspection.json' for source in sources]
        with support.staged_outputs(output, names) as stage:
            reports = [op.inspect_source(source) for source in sources]
            for name, report in zip(names, reports):
                support.write_json(stage / name, report)
        return reports
    if mode == 'export':
        sources = support.source_paths(job.get('sources'))
        return op.export_bodies(sources, output, job.get('mesh_tolerance_mm', .05),
                                job.get('minimum_edge_length_mm', 0.0))
    if mode == 'synthetic':
        return synthetic(job, output)
    raise ValueError('Unknown native mode; expected inspect, export, or synthetic')


if __name__ == '__main__':
    print(json.dumps(main(JOB, OUT_DIR), ensure_ascii=False, allow_nan=False))
