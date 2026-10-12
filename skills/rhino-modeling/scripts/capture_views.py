#! python 3
"""Capture real Rhino viewports. Run via rhino_run.py with a guarded named document."""
import json,pathlib
import Rhino
from System import Guid
from System.Drawing.Imaging import ImageFormat
G=Rhino.Geometry
doc=GUARDED_DOC
if doc is None or doc.Views.ActiveView is None:raise RuntimeError('Open the intended document with a viewport before capture')
view=doc.Views.ActiveView;vp=view.ActiveViewport
old_mode=vp.DisplayMode;old_grid=vp.ConstructionGridVisible;old_axes=vp.ConstructionAxesVisible
vp.PushViewProjection()
reports=[]
try:
    mode_id=Guid(JOB['display_mode_id']) if JOB.get('display_mode_id') else Rhino.Display.DisplayModeDescription.ShadedId
    vp.DisplayMode=Rhino.Display.DisplayModeDescription.GetDisplayMode(mode_id)
    vp.ConstructionGridVisible=False;vp.ConstructionAxesVisible=False
    for item in JOB['views']:
        filename=item['filename']
        if pathlib.Path(filename).name!=filename or not filename.endswith('.png'):raise ValueError('Use a simple PNG filename')
        vp.ChangeToParallelProjection(True);vp.CameraUp=G.Vector3d(*item.get('up',[0,0,1]))
        vp.SetCameraLocations(G.Point3d(*item['target']),G.Point3d(*item['camera']))
        box=G.BoundingBox(G.Point3d(*item['bounds'][0]),G.Point3d(*item['bounds'][1]));vp.ZoomBoundingBox(box)
        doc.Views.Redraw();Rhino.RhinoApp.Wait()
        capture=Rhino.Display.ViewCapture();capture.Width=int(JOB.get('width',2000));capture.Height=int(JOB.get('height',1400));capture.DrawGrid=False;capture.DrawAxes=False
        bitmap=capture.CaptureToBitmap(view)
        if bitmap is None:raise RuntimeError('Native ViewCapture failed')
        path=pathlib.Path(OUT_DIR)/filename
        if path.exists():bitmap.Dispose();raise FileExistsError(path)
        bitmap.Save(str(path),ImageFormat.Png);bitmap.Dispose()
        reports.append({'file':filename,'source_document':pathlib.Path(doc.Path).name,'method':'Rhino native ViewCapture','camera':item['camera'],'target':item['target']})
finally:
    vp.PopViewProjection();vp.DisplayMode=old_mode;vp.ConstructionGridVisible=old_grid;vp.ConstructionAxesVisible=old_axes;doc.Views.Redraw()
(pathlib.Path(OUT_DIR)/'views.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2));print(json.dumps(reports,ensure_ascii=False))
