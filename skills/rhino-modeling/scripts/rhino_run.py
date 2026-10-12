#!/usr/bin/env python3
"""Discover and run scripts through McNeel RhinoCode with a document guard and completion token."""
import argparse,json,os,pathlib,platform,shutil,subprocess,sys,time,uuid
Path=pathlib.Path

def cli(binary=None):
    p=binary or os.environ.get('RHINO_CODE_BIN') or shutil.which('rhinocode')
    if not p and sys.platform=='darwin':p='/Applications/Rhino 8.app/Contents/Resources/bin/rhinocode'
    if not p and sys.platform=='win32':p=str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Rhino 8/System/rhinocode.exe')
    if not p or not Path(p).is_file():raise FileNotFoundError('RhinoCode unavailable; provide --binary or RHINO_CODE_BIN')
    # Rhino 8.35 macOS launcher expands arguments without preserving spaces.
    # Use the same bundled assembly, with subprocess argument boundaries intact.
    if sys.platform=='darwin' and Path(p).name=='rhinocode':
        contents=Path(p).resolve().parents[2]
        res=contents/'Frameworks/RhCore.framework/Versions/Current/Resources'
        assembly=res/'RhinoCode.dll';dotnet=res/'dotnet'/platform.machine()/'dotnet'
        if assembly.is_file() and dotnet.is_file():return [str(dotnet),str(assembly)]
    return [str(p)]

def query(args,timeout=30):
    r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    if r.returncode:raise RuntimeError(r.stderr or r.stdout)
    if 'Permission denied' in r.stdout+r.stderr:raise PermissionError('Local Rhino pipe access denied; request narrow local-process access')
    return r.stdout.strip()

WRAPPER='''#! python 3
import Rhino,json,pathlib,time,traceback,contextlib,io,os
p=pathlib.Path(__file__).with_name('request.json')
req=json.loads(p.read_text()); out=io.StringIO()
result={'token':req['token'],'status':'running'}
dest=p.with_name('result.json')
def save():
 tmp=dest.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2));os.replace(str(tmp),str(dest))
save()
try:
 with contextlib.redirect_stdout(out):
  doc=Rhino.RhinoDoc.ActiveDoc;expected=req['expected_doc']
  if expected=='@none':
   assert doc is None or (not doc.Path and doc.Objects.Count==0),'Expected no document or an empty unnamed document'
  else:
   assert doc and doc.Path and pathlib.Path(doc.Path).resolve()==pathlib.Path(expected).resolve(),'Active document mismatch'
  script=pathlib.Path(req['script'])
  exec(compile(script.read_text(),str(script),'exec'),{'__name__':'__main__','__file__':str(script),'JOB':req['job'],'OUT_DIR':req['output'],'GUARDED_DOC':doc})
 result['status']='passed'
except BaseException:
 result['status']='failed';result['error']=traceback.format_exc()
finally:
 result['stdout']=out.getvalue();result['finished']=time.time();save();print(result['status']+' '+req['token'])
'''

def run(binary,instance,expected,script,job,output,timeout=600):
    cmd=cli(binary);instances=json.loads(query(cmd+['list','--json']))
    if not any(x['pipeId']==instance for x in instances):raise ValueError('Requested Rhino instance is not running')
    script=Path(script).resolve()
    if not script.is_file():raise FileNotFoundError(script)
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    token=str(uuid.uuid4());work=output/('.dispatch-'+token);work.mkdir()
    request={'token':token,'expected_doc':expected,'script':str(script),'job':job,'output':str(output)}
    (work/'request.json').write_text(json.dumps(request,ensure_ascii=False));(work/'runner.py').write_text(WRAPPER)
    # A zero exit code can mean only that the script was queued.
    response=query(cmd+['--rhino',instance,'script',str(work/'runner.py')])
    end=time.monotonic()+timeout;result=work/'result.json'
    while time.monotonic()<end:
        if result.exists():
            try:r=json.loads(result.read_text())
            except json.JSONDecodeError:r={}
            if r.get('token')==token and r.get('status') in ['passed','failed']:
                print(r.get('stdout',''))
                if r['status']=='failed':raise RuntimeError(r.get('error','Rhino execution failed'))
                return r
        time.sleep(.25)
    raise TimeoutError('No completion acknowledgement. Inspect the running job before retrying; it may still be executing.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary');s=p.add_subparsers(dest='cmd',required=True)
    s.add_parser('env')
    q=s.add_parser('run');q.add_argument('--instance',required=True);q.add_argument('--expected-doc',required=True);q.add_argument('--script',required=True);q.add_argument('--job',required=True);q.add_argument('--output',required=True);q.add_argument('--timeout',type=int,default=600)
    a=p.parse_args()
    if a.cmd=='env':print(json.dumps({'version':query(cli(a.binary)+['-V']),'instances':json.loads(query(cli(a.binary)+['list','--json']))},ensure_ascii=False,indent=2))
    else:run(a.binary,a.instance,a.expected_doc,a.script,json.loads(Path(a.job).read_text()),a.output,a.timeout)

if __name__=='__main__':
    try:main()
    except Exception as e:print(str(e),file=sys.stderr);sys.exit(1)
