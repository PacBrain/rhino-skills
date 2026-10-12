"""Rhino Python 3 only. In-memory diagnosis and derived file export; no active-document mutation."""
import hashlib,json,math,pathlib,struct
import Rhino
from System.Threading import CancellationToken
G=Rhino.Geometry
Path=pathlib.Path

def point(p):return [float(p.X),float(p.Y),float(p.Z)]

def brep_report(b):
    bb=b.GetBoundingBox(True);v=G.VolumeMassProperties.Compute(b) if b.IsSolid else None
    return {'valid':bool(b.IsValid),'solid':bool(b.IsSolid),'orientation':str(b.SolidOrientation),
            'faces':b.Faces.Count,'naked_edges':sum(e.Valence==G.EdgeAdjacency.Naked for e in b.Edges),
            'nonmanifold_edges':sum(e.Valence==G.EdgeAdjacency.NonManifold for e in b.Edges),
            'bounds':[point(bb.Min),point(bb.Max)],'dimensions':[bb.Max.X-bb.Min.X,bb.Max.Y-bb.Min.Y,bb.Max.Z-bb.Min.Z],
            'volume':float(v.Volume) if v else None,'exact_global_self_intersection':'not_run'}

def check_solid(b):
    r=brep_report(b)
    if not (r['valid'] and r['solid'] and not r['naked_edges'] and not r['nonmanifold_edges'] and r['orientation']=='Outward'):
        raise ValueError('Expected outward closed Brep: '+json.dumps(r))
    return r

def make_mesh(b,tolerance=.05):
    if tolerance<=0:raise ValueError('Mesh tolerance must be positive in document units')
    mp=G.MeshingParameters();mp.Tolerance=tolerance;mp.MinimumEdgeLength=tolerance*2;mp.MaximumEdgeLength=tolerance*120
    mp.RefineGrid=True;mp.JaggedSeams=False;mp.SimplePlanes=True
    parts=G.Mesh.CreateFromBrep(b,mp)
    if not parts:raise RuntimeError('Meshing returned no results')
    m=G.Mesh()
    for part in parts:m.Append(part)
    m.Vertices.CombineIdentical(True,True);m.Weld(math.pi);m.UnifyNormals();m.Faces.ConvertQuadsToTriangles();m.Normals.ComputeNormals();m.Compact()
    if not (m.IsValid and m.IsClosed and m.IsManifold()):raise ValueError('Derived mesh is invalid/open/nonmanifold; do not enlarge CAD tolerance to hide this')
    if m.SolidOrientation()==-1:m.Flip(True,True,True)
    report={'valid':bool(m.IsValid),'closed':bool(m.IsClosed),'manifold':bool(m.IsManifold()),'tolerance':tolerance,'vertices':m.Vertices.Count,'triangles':m.Faces.Count}
    try:
        out=m.GetSelfIntersections(1e-7,True,False,None,CancellationToken(False),None)
        report['self_intersection_screen']={'executed':bool(out[0]),'curves':len(out[1] or []),'overlaps':len(out[2] or [])}
        if not out[0] or report['self_intersection_screen']['curves'] or report['self_intersection_screen']['overlaps']:raise ValueError('Mesh self-intersection screening failed')
    except (AttributeError,TypeError) as e:report['self_intersection_screen']={'executed':False,'reason':str(e)}
    return m,report

def write_stl(mesh,path):
    path=Path(path)
    if path.exists():raise FileExistsError(path)
    mesh.FaceNormals.ComputeFaceNormals()
    with path.open('wb') as f:
        f.write(b'Rhino derived mesh; units supplied in manifest'.ljust(80,b' '));f.write(struct.pack('<I',mesh.Faces.Count))
        for i,face in enumerate(mesh.Faces):
            n=mesh.FaceNormals[i];verts=[mesh.Vertices[j] for j in [face.A,face.B,face.C]]
            f.write(struct.pack('<12fH',*point(n),*(v for p in verts for v in point(p)),0))

def readback_stl(path,source_bounds,max_error,units):
    d=Rhino.RhinoDoc.CreateHeadless(None);d.ModelUnitSystem=units
    try:
        if not d.Import(str(path)):raise RuntimeError('Rhino failed to read STL')
        meshes=[o.Geometry for o in d.Objects if isinstance(o.Geometry,G.Mesh)]
        if not meshes:raise ValueError('No mesh on readback')
        bb=G.BoundingBox.Empty
        for m in meshes:
            if not m.IsClosed or not m.IsValid or not m.IsManifold():raise ValueError('Readback STL is not valid and closed')
            bb.Union(m.GetBoundingBox(True))
        error=max(abs(a-b) for p,q in zip(source_bounds,[point(bb.Min),point(bb.Max)]) for a,b in zip(p,q))
        if error>max_error:raise ValueError('Readback bounds exceed tolerance: '+str(error))
        return {'valid_closed_meshes':len(meshes),'max_bounds_error':error}
    finally:d.Dispose()

def write_3dm(b,path,units=Rhino.UnitSystem.Millimeters):
    if Path(path).exists():raise FileExistsError(path)
    f=Rhino.FileIO.File3dm();f.Settings.ModelUnitSystem=units;f.Settings.ModelAbsoluteTolerance=.01
    a=Rhino.DocObjects.ObjectAttributes();a.Name='synthetic_body';f.Objects.AddBrep(b,a)
    if not f.Write(str(path),8):raise RuntimeError('3DM write failed')

def export_body(source,out,tolerance=.05):
    source=Path(source);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    f=Rhino.FileIO.File3dm.Read(str(source))
    if f is None:raise ValueError('Could not read 3DM')
    if f.Settings.ModelUnitSystem!=Rhino.UnitSystem.Millimeters:raise ValueError('This export workflow requires explicit mm sources; normalize in a new document first')
    bs=[o.Geometry for o in f.Objects if isinstance(o.Geometry,G.Brep)]
    if len(bs)!=1:raise ValueError('Expected one solid Brep per source file; use named-object selection for assemblies')
    b=bs[0];r=check_solid(b);m,mr=make_mesh(b,tolerance)
    name=source.stem;stl=out/(name+'.stl');write_stl(m,stl)
    back=readback_stl(stl,r['bounds'],max(.1,2*tolerance),f.Settings.ModelUnitSystem)
    meshjson={'positions':[v for p in m.Vertices for v in point(p)],'triangles':[v for face in m.Faces for v in [face.A,face.B,face.C]]}
    (out/(name+'.mesh.json')).write_text(json.dumps(meshjson,separators=(',',':')))
    report={'source':source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'software':str(Rhino.RhinoApp.Version),
            'units':'mm','geometry':r,'mesh':mr,'stl_readback':back,'stl_sha256':hashlib.sha256(stl.read_bytes()).hexdigest(),'physical_test':'not_run'}
    (out/(name+'.validation.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2));return report
