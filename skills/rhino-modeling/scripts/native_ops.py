"""Rhino Python 3 geometry inspection and staged export; never modifies ActiveDoc."""
import hashlib
import json
import math
from pathlib import Path
import struct
import types
import uuid

import Rhino
from System.Threading import CancellationToken

G = Rhino.Geometry
_support_path = Path(__file__).resolve().with_name('job_support.py')
support = types.ModuleType('_rhino_support_' + uuid.uuid4().hex)
support.__file__ = str(_support_path)
exec(compile(_support_path.read_text(encoding='utf-8'), str(_support_path), 'exec'), support.__dict__)


def point(p):
    return [float(p.X), float(p.Y), float(p.Z)]


def sha256(path):
    with Path(path).open('rb') as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def bounds_report(geometry):
    box = geometry.GetBoundingBox(True)
    if not box.IsValid:
        return {'bounds': None, 'dimensions': None}
    return {'bounds': [point(box.Min), point(box.Max)],
            'dimensions': [box.Max.X - box.Min.X, box.Max.Y - box.Min.Y, box.Max.Z - box.Min.Z]}


def brep_report(brep):
    report = {'valid': bool(brep.IsValid), 'solid': bool(brep.IsSolid),
              'orientation': str(brep.SolidOrientation), 'faces': brep.Faces.Count,
              'naked_edges': sum(e.Valence == G.EdgeAdjacency.Naked for e in brep.Edges),
              'nonmanifold_edges': sum(e.Valence == G.EdgeAdjacency.NonManifold for e in brep.Edges),
              'volume': None, 'exact_global_self_intersection': 'not_run'}
    report.update(bounds_report(brep))
    volume = G.VolumeMassProperties.Compute(brep) if report['valid'] and report['solid'] else None
    if volume is not None:
        try:
            report['volume'] = float(volume.Volume)
        finally:
            volume.Dispose()
    return report


def check_solid(brep):
    report = brep_report(brep)
    if not (report['valid'] and report['solid'] and not report['naked_edges']
            and not report['nonmanifold_edges'] and report['orientation'] == 'Outward'):
        raise ValueError('Expected outward closed Brep: ' + json.dumps(report))
    return report


def mesh_report(mesh):
    report = {'valid': bool(mesh.IsValid), 'closed': bool(mesh.IsClosed),
              'manifold': bool(mesh.IsManifold()), 'solid': bool(mesh.IsSolid),
              'orientation': int(mesh.SolidOrientation()), 'vertices': mesh.Vertices.Count,
              'triangles': sum(face.IsTriangle for face in mesh.Faces),
              'faces': mesh.Faces.Count, 'self_intersection_screen': {'executed': False, 'reason': 'not_run'}}
    report.update(bounds_report(mesh))
    return report


def check_mesh_solid(mesh, allow_flip=False):
    if not (mesh.IsValid and mesh.IsClosed and mesh.IsManifold() and mesh.IsSolid):
        raise ValueError('Expected valid closed oriented manifold mesh')
    orientation = int(mesh.SolidOrientation())
    if orientation == -1 and allow_flip:
        mesh.Flip(True, True, True)
        orientation = int(mesh.SolidOrientation())
    if orientation != 1 or not mesh.IsSolid:
        raise ValueError('Expected outward solid mesh; orientation=' + str(orientation))
    return mesh_report(mesh)


def sample_mesh_deviation(mesh, brep, limit=512):
    """Sample triangle edge midpoints and centroids; this is not a global error bound."""
    count = mesh.Faces.Count
    stride = max(1, int(math.ceil(count / float(limit))))
    maximum = 0.0
    samples = 0
    for index in range(0, count, stride):
        face = mesh.Faces[index]
        vertices = [G.Point3d(mesh.Vertices[i]) for i in (face.A, face.B, face.C)]
        xyz = [point(p) for p in vertices]
        probes = [G.Point3d(*[(xyz[a][axis] + xyz[b][axis]) / 2 for axis in range(3)])
                  for a, b in ((0, 1), (1, 2), (2, 0))]
        probes.append(G.Point3d(*[sum(p[axis] for p in xyz) / 3 for axis in range(3)]))
        for probe in probes:
            closest = brep.ClosestPoint(probe)
            if not closest.IsValid:
                raise RuntimeError('Mesh-to-Brep deviation sampling failed')
            maximum = max(maximum, probe.DistanceTo(closest))
            samples += 1
    return {'method': 'triangle edge midpoints and centroids to Brep closest point',
            'samples': samples, 'face_stride': stride, 'max_sampled_distance': maximum,
            'global_error_bound': False}


def make_mesh(brep, tolerance=.05, minimum_edge_length=0.0):
    tolerance = support.finite_number(tolerance, 'mesh_tolerance_mm')
    minimum_edge_length = support.finite_number(minimum_edge_length, 'minimum_edge_length_mm', inclusive=True)
    parameters = G.MeshingParameters()
    parameters.Tolerance = tolerance
    parameters.MinimumEdgeLength = minimum_edge_length
    parameters.MaximumEdgeLength = 0.0
    parameters.RefineGrid = True
    parameters.JaggedSeams = False
    parameters.SimplePlanes = True
    parts = G.Mesh.CreateFromBrep(brep, parameters)
    if not parts:
        raise RuntimeError('Meshing returned no results')
    mesh = G.Mesh()
    for part in parts:
        mesh.Append(part)
    mesh.Vertices.CombineIdentical(True, True)
    mesh.Weld(math.pi)
    mesh.UnifyNormals()
    mesh.Faces.ConvertQuadsToTriangles()
    mesh.Normals.ComputeNormals()
    mesh.Compact()
    report = check_mesh_solid(mesh, allow_flip=True)
    report.update({'requested_tolerance_mm': tolerance,
                   'minimum_edge_length_mm': minimum_edge_length,
                   'maximum_edge_length_mm': 0.0,
                   'sampled_deviation': sample_mesh_deviation(mesh, brep)})
    try:
        result = mesh.GetSelfIntersections(1e-7, True, False, None, CancellationToken(False), None)
        screen = {'executed': bool(result[0]), 'curves': len(result[1] or []),
                  'overlaps': len(result[2] or []), 'tolerance': 1e-7}
        report['self_intersection_screen'] = screen
        if not screen['executed'] or screen['curves'] or screen['overlaps']:
            raise ValueError('Mesh self-intersection screening failed')
    except (AttributeError, TypeError) as error:
        report['self_intersection_screen'] = {'executed': False, 'reason': str(error)}
    return mesh, report


def write_stl(mesh, path):
    check_mesh_solid(mesh)
    if any(not face.IsTriangle for face in mesh.Faces):
        raise ValueError('Binary STL writer requires a triangulated mesh')
    mesh.FaceNormals.ComputeFaceNormals()
    with Path(path).open('xb') as stream:
        stream.write(b'Rhino derived mesh; units supplied in manifest'.ljust(80, b' '))
        stream.write(struct.pack('<I', mesh.Faces.Count))
        for index, face in enumerate(mesh.Faces):
            normal = mesh.FaceNormals[index]
            vertices = [mesh.Vertices[i] for i in (face.A, face.B, face.C)]
            stream.write(struct.pack('<12fH', *point(normal),
                                     *(v for p in vertices for v in point(p)), 0))


def readback_stl(path, source_bounds, max_error, units):
    max_error = support.finite_number(max_error, 'max_bounds_error')
    doc = Rhino.RhinoDoc.CreateHeadless(None)
    if doc is None:
        raise RuntimeError('Could not create headless STL readback document')
    doc.ModelUnitSystem = units
    try:
        options = Rhino.FileIO.FileStlReadOptions()
        options.STLModelUnits = units
        options.Weld = True
        options.WeldAngle = math.pi
        options.SplitDisjointMeshes = False
        if not doc.Import(str(path), options.ToDictionary()):
            raise RuntimeError('Rhino failed to read STL')
        objects = list(doc.Objects)
        meshes = [obj.Geometry for obj in objects if isinstance(obj.Geometry, G.Mesh)]
        if len(meshes) != 1 or len(objects) != 1:
            raise ValueError('Expected exactly one mesh on STL readback')
        report = check_mesh_solid(meshes[0])
        error = max(abs(a - b) for left, right in zip(source_bounds, report['bounds'])
                    for a, b in zip(left, right))
        if error > max_error:
            raise ValueError('Readback bounds exceed allowed error: ' + str(error))
        return {'valid_closed_meshes': 1, 'outward_solid': True, 'max_bounds_error_mm': error,
                'allowed_bounds_error_mm': max_error, 'units': str(doc.ModelUnitSystem),
                'import_options': {'units': str(units), 'weld': True,
                                   'weld_angle_radians': math.pi, 'split_disjoint_meshes': False}}
    finally:
        doc.Dispose()


def write_3dm(brep, path, units=Rhino.UnitSystem.Millimeters):
    if Path(path).exists():
        raise FileExistsError(path)
    model = Rhino.FileIO.File3dm()
    try:
        model.Settings.ModelUnitSystem = units
        model.Settings.ModelAbsoluteTolerance = .01
        attributes = Rhino.DocObjects.ObjectAttributes()
        attributes.Name = 'synthetic_body'
        model.Objects.AddBrep(brep, attributes)
        if not model.Write(str(path), 8):
            raise RuntimeError('3DM write failed')
    finally:
        model.Dispose()


def inspect_source(source):
    source = support.source_paths([str(source)])[0]
    digest = sha256(source)
    model = Rhino.FileIO.File3dm.Read(str(source))
    if model is None:
        raise ValueError('Could not read 3DM')
    try:
        objects = []
        types_count = {}
        for obj in model.Objects:
            geometry = obj.Geometry
            kind = geometry.GetType().Name
            types_count[kind] = types_count.get(kind, 0) + 1
            item = {'id': str(obj.Attributes.ObjectId), 'name': obj.Attributes.Name,
                    'layer_index': obj.Attributes.LayerIndex, 'type': kind}
            layer = model.Layers.FindIndex(obj.Attributes.LayerIndex)
            item['layer'] = layer.Name if layer is not None else None
            try:
                item.update(bounds_report(geometry))
                item['valid'] = bool(geometry.IsValid)
                if isinstance(geometry, G.Brep):
                    item['brep'] = brep_report(geometry)
                elif isinstance(geometry, G.Mesh):
                    item['mesh'] = mesh_report(geometry)
                else:
                    item['type_specific_checks'] = 'not_run'
                item['inspection_status'] = 'inspected'
            except Exception as error:
                item['inspection_status'] = 'failed'
                item['error'] = str(error)
            objects.append(item)
        if digest != sha256(source):
            raise RuntimeError('Source changed while inspecting')
        return {'status': 'inspected', 'source': source.name, 'source_sha256': digest,
                'software': str(Rhino.RhinoApp.Version), 'units': str(model.Settings.ModelUnitSystem),
                'absolute_tolerance': model.Settings.ModelAbsoluteTolerance,
                'angle_tolerance_radians': model.Settings.ModelAngleToleranceRadians,
                'object_count': len(objects), 'object_types': types_count, 'objects': objects,
                'manufacturing_validation': 'not_run'}
    finally:
        model.Dispose()


def export_names(source):
    return [source.stem + suffix for suffix in ('.stl', '.mesh.json', '.validation.json')]


def _export_body_to_stage(source, stage, tolerance=.05, minimum_edge_length=0.0):
    digest = sha256(source)
    model = Rhino.FileIO.File3dm.Read(str(source))
    if model is None:
        raise ValueError('Could not read 3DM')
    try:
        if model.Settings.ModelUnitSystem != Rhino.UnitSystem.Millimeters:
            raise ValueError('Export requires explicit mm sources; normalize in a new document first')
        objects = list(model.Objects)
        if len(objects) != 1 or not isinstance(objects[0].Geometry, G.Brep):
            raise ValueError('Export requires exactly one Brep object and no other objects; use inspect first')
        brep = objects[0].Geometry
        geometry = check_solid(brep)
        mesh, meshing = make_mesh(brep, tolerance, minimum_edge_length)
        stl, mesh_path, report_path = [stage / name for name in export_names(source)]
        write_stl(mesh, stl)
        readback = readback_stl(stl, geometry['bounds'], max(.1, 2 * tolerance), model.Settings.ModelUnitSystem)
        if digest != sha256(source):
            raise RuntimeError('Source changed while exporting')
        support.write_json(mesh_path, {'positions': [v for p in mesh.Vertices for v in point(p)],
                                      'triangles': [v for face in mesh.Faces for v in (face.A, face.B, face.C)]})
        report = {'status': 'validated', 'source': source.name, 'source_sha256': digest,
                  'source_object_id': str(objects[0].Attributes.ObjectId),
                  'software': str(Rhino.RhinoApp.Version), 'units': 'mm',
                  'document_absolute_tolerance_mm': model.Settings.ModelAbsoluteTolerance,
                  'geometry': geometry, 'mesh': meshing, 'stl_readback': readback,
                  'stl_sha256': sha256(stl), 'physical_test': 'not_run'}
        support.write_json(report_path, report)
        return report
    finally:
        model.Dispose()


def export_bodies(sources, output, tolerance=.05, minimum_edge_length=0.0):
    paths = support.source_paths([str(source) for source in sources])
    tolerance = support.finite_number(tolerance, 'mesh_tolerance_mm')
    minimum_edge_length = support.finite_number(minimum_edge_length, 'minimum_edge_length_mm', inclusive=True)
    names = [name for source in paths for name in export_names(source)]
    with support.staged_outputs(output, names) as stage:
        reports = [_export_body_to_stage(source, stage, tolerance, minimum_edge_length) for source in paths]
    return reports


def export_body(source, output, tolerance=.05, minimum_edge_length=0.0):
    return export_bodies([source], output, tolerance, minimum_edge_length)[0]


def step_roundtrip(source, target, dimensions):
    if Path(target).exists():
        raise FileExistsError(target)
    doc = Rhino.RhinoDoc.OpenHeadless(str(source))
    if doc is None:
        raise RuntimeError('Could not open headless STEP export document')
    try:
        options = Rhino.FileIO.FileStpWriteOptions()
        options.Schema = Rhino.FileIO.FileStpWriteOptions.StepSchema.SF_214
        options.Export2dCurves = False
        options.ExportBlack = True
        options.SplitClosedSurfaces = False
        if not doc.Export(str(target), options.ToDictionary()):
            raise RuntimeError('STEP export failed')
    finally:
        doc.Dispose()
    doc = Rhino.RhinoDoc.CreateHeadless(None)
    if doc is None:
        raise RuntimeError('Could not create headless STEP readback document')
    doc.ModelUnitSystem = Rhino.UnitSystem.Millimeters
    doc.ModelAbsoluteTolerance = .01
    try:
        read = Rhino.FileIO.FileStpReadOptions()
        read.JoinSurfaces = True
        read.LimitFaces = False
        if not doc.Import(str(target), read.ToDictionary()):
            raise RuntimeError('STEP import failed')
        objects = list(doc.Objects)
        if len(objects) != 1 or not isinstance(objects[0].Geometry, G.Brep):
            raise ValueError('Expected one Brep after STEP readback')
        back = check_solid(objects[0].Geometry)
        error = max(abs(a - b) for a, b in zip(back['dimensions'], dimensions))
        if error > .1:
            raise ValueError('STEP readback dimensions exceed allowed error')
        return {'dimensions_error_mm': error, 'allowed_error_mm': .1, 'units': str(doc.ModelUnitSystem),
                'export_schema': 'AP214', 'join_surfaces': True, 'geometry': back}
    finally:
        doc.Dispose()
