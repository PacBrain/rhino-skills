#!/usr/bin/env python3
"""Discover and run scripts through McNeel RhinoCode with a document guard and completion token."""
import argparse,json,math,os,pathlib,platform,shutil,subprocess,sys,time,uuid
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
    r=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
    diagnostics='\n'.join(part for part in [r.stdout,r.stderr] if part)
    if 'Permission denied' in diagnostics:raise PermissionError('Local Rhino pipe access denied; request narrow local-process access')
    if r.returncode:raise RuntimeError(diagnostics or 'RhinoCode command failed with exit code '+str(r.returncode))
    return r.stdout.strip()

WRAPPER='''#! python 3
import Rhino,json,pathlib,time,traceback,contextlib,io,os
p=pathlib.Path(__file__).with_name('request.json')
req=json.loads(p.read_text(encoding='utf-8')); out=io.StringIO(); err=io.StringIO()
result={'token':req['token'],'status':'running'}
dest=p.with_name('result.json')
def save():
 tmp=dest.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(str(tmp),str(dest))
save()
try:
 with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
  doc=Rhino.RhinoDoc.ActiveDoc;expected=req['expected_doc']
  if expected=='@none':
   if not (doc is None or (not doc.Path and doc.Objects.Count==0)):
    raise RuntimeError('Expected no document or an empty unnamed document')
  else:
   if not (doc is not None and doc.Path and pathlib.Path(doc.Path).resolve()==pathlib.Path(expected).resolve()):
    raise RuntimeError('Active document mismatch')
  script=pathlib.Path(req['script'])
  exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),{'__name__':'__main__','__file__':str(script),'JOB':req['job'],'OUT_DIR':req['output'],'GUARDED_DOC':doc})
 result['status']='passed'
except BaseException:
 result['status']='failed';result['error']=traceback.format_exc()
finally:
 result['stdout']=out.getvalue();result['stderr']=err.getvalue();result['finished']=time.time();save();print(result['status']+' '+req['token'])
'''

def run(binary,instance,expected,script,job,output,timeout=600):
    # Reject malformed requests before contacting Rhino or creating dispatch files.
    if isinstance(timeout,bool):raise ValueError('Timeout must be finite and positive')
    try:timeout=float(timeout)
    except (TypeError,ValueError,OverflowError) as e:raise ValueError('Timeout must be finite and positive') from e
    if not math.isfinite(timeout) or timeout<=0:raise ValueError('Timeout must be finite and positive')
    if not isinstance(job,dict):raise ValueError('Job must be a JSON object')
    try:job_json=json.dumps(job,ensure_ascii=False,allow_nan=False)
    except (TypeError,ValueError) as e:raise ValueError('Job must contain valid JSON values') from e
    try:expected=os.fspath(expected)
    except TypeError as e:raise ValueError('Expected document must be an absolute path or @none') from e
    if not isinstance(expected,str) or (expected!='@none' and not Path(expected).is_absolute()):
        raise ValueError('Expected document must be an absolute path or @none')
    if expected!='@none':expected=str(Path(expected).resolve())
    cmd=cli(binary);instances=json.loads(query(cmd+['list','--json']))
    if not any(x['pipeId']==instance for x in instances):raise ValueError('Requested Rhino instance is not running')
    script=Path(script).resolve()
    if not script.is_file():raise FileNotFoundError(script)
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    token=str(uuid.uuid4());work=output/('.dispatch-'+token);work.mkdir()
    request={'token':token,'expected_doc':expected,'script':str(script),'job':json.loads(job_json),'output':str(output)}
    (work/'request.json').write_text(json.dumps(request,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    (work/'runner.py').write_text(WRAPPER,encoding='utf-8')
    # A zero exit code can mean only that the script was queued. A CLI timeout
    # can also occur after dispatch, so keep observing this token without retrying.
    end=time.monotonic()+timeout;result=work/'result.json'
    try:query(cmd+['--rhino',instance,'script',str(work/'runner.py')],timeout=min(30,timeout))
    except subprocess.TimeoutExpired:
        print('RhinoCode dispatch command timed out; waiting for its completion token without resubmitting.',file=sys.stderr)
    while True:
        if result.exists():
            try:r=json.loads(result.read_text(encoding='utf-8'))
            except (json.JSONDecodeError,UnicodeDecodeError):r={}
            if isinstance(r,dict) and r.get('token')==token and r.get('status') in ['passed','failed']:
                if r.get('stdout'):print(r['stdout'],end='')
                if r.get('stderr'):print(r['stderr'],end='',file=sys.stderr)
                if r['status']=='failed':raise RuntimeError(r.get('error','Rhino execution failed'))
                return r
        remaining=end-time.monotonic()
        if remaining<=0:break
        time.sleep(min(.25,remaining))
    raise TimeoutError('No completion acknowledgement for token '+token+'. Inspect '+str(work)+' and the running job before retrying; it may still be executing.')

def main():
    # JSON and replayed job diagnostics use UTF-8 even when a redirected Windows
    # console inherits a legacy code page. Leave embedded/custom streams alone.
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):
            stream.reconfigure(encoding='utf-8',errors='backslashreplace')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary');s=p.add_subparsers(dest='cmd',required=True)
    s.add_parser('env')
    q=s.add_parser('run');q.add_argument('--instance',required=True);q.add_argument('--expected-doc',required=True);q.add_argument('--script',required=True);q.add_argument('--job',required=True);q.add_argument('--output',required=True);q.add_argument('--timeout',type=float,default=600)
    a=p.parse_args()
    if a.cmd=='env':print(json.dumps({'version':query(cli(a.binary)+['-V']),'instances':json.loads(query(cli(a.binary)+['list','--json']))},ensure_ascii=False,indent=2))
    else:run(a.binary,a.instance,a.expected_doc,a.script,json.loads(Path(a.job).read_text(encoding='utf-8')),a.output,a.timeout)

if __name__=='__main__':
    try:main()
    except Exception as e:print(str(e),file=sys.stderr);sys.exit(1)
