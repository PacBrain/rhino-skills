#! python 3
"""Invoke using rhino_run.py, which injects JOB and OUT_DIR after its document guard."""
import pathlib,sys,json
sys.path.insert(0,str(pathlib.Path(__file__).parent))
import native_ops as op
import Rhino
G=Rhino.Geometry
out=pathlib.Path(OUT_DIR)
if JOB['mode']=='export':
    reports=[op.export_body(p,out,float(JOB.get('mesh_tolerance_mm',.05))) for p in JOB['sources']]
    print(json.dumps(reports,ensure_ascii=False))
elif JOB['mode']=='synthetic':
    dims=JOB.get('dimensions_mm',[24,36,18])
    if len(dims)!=3 or min(dims)<=0:raise ValueError('Three positive dimensions required')
    b=G.BoundingBox(G.Point3d.Origin,G.Point3d(*dims)).ToBrep();op.check_solid(b)
    mirror=b.DuplicateBrep();mirror.Transform(G.Transform.Mirror(G.Plane.WorldYZ))
    if mirror.SolidOrientation==G.BrepSolidOrientation.Inward:mirror.Flip()
    op.check_solid(mirror)
    broken=b.DuplicateBrep();broken.Faces.RemoveAt(0)
    rejected=False
    try:op.check_solid(broken)
    except ValueError:rejected=True
    assert rejected,'Missing-face geometry was not rejected'
    source=out/'synthetic box 测试.3dm';op.write_3dm(b,source)
    r=op.export_body(source,out)
    doc=Rhino.RhinoDoc.OpenHeadless(str(source));step=out/'synthetic.step'
    try:
        assert not step.exists() and doc.Export(str(step))
    finally:doc.Dispose()
    doc=Rhino.RhinoDoc.CreateHeadless(None);doc.ModelUnitSystem=Rhino.UnitSystem.Millimeters
    try:
        assert doc.Import(str(step));bs=[o.Geometry for o in doc.Objects if isinstance(o.Geometry,G.Brep)];assert len(bs)==1
        back=op.check_solid(bs[0]);error=max(abs(a-c) for a,c in zip(back['dimensions'],dims));assert error<.1
    finally:doc.Dispose()
    report={'status':'passed','rhino_version':str(Rhino.RhinoApp.Version),'closed_solid':True,'mirrored_outward':True,'missing_face_rejected':rejected,'step_roundtrip_bounds_error_mm':error,'export':r}
    (out/'synthetic_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
else:raise ValueError('Unknown native mode')
