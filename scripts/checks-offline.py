"""Run public or independently supplied tests in a read-only offline namespace."""
import argparse,errno,hashlib,os,shutil,socket,subprocess,tempfile,importlib.util,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
OMIT={'.git','.venv','__pycache__','build','dist','.pytest_cache'}
SOURCE_FILES=('.github/workflows/tests.yml', '.gitignore', 'CONTRIBUTING.md', 'ENGINE-AUTHORING.txt', 'LICENSE', 'README.md', 'SECURITY.md', 'WORKSHOP-CONTRACT.json', 'examples/busca-limitada.json', 'examples/inviavel.json', 'examples/viavel.json', 'planejador_oficinas/__init__.py', 'planejador_oficinas/__main__.py', 'planejador_oficinas/core.py', 'planejador_oficinas/errors.py', 'pyproject.toml', 'scripts/checks-offline.py', 'scripts/ci-bootstrap.sh', 'scripts/engine-guard.py', 'tests/test_cli.py', 'tests/test_core.py')
def files(root):
 if root==ROOT:
  for name in SOURCE_FILES:
   p=root/name
   if not p.is_file()or p.is_symlink()or any(x.is_symlink()for x in p.parents):raise ValueError('Closed source file refused')
   yield p
  return
 for directory,names,filenames in os.walk(root,followlinks=False):
  names[:]=[n for n in names if n not in OMIT]
  for n in names:
   if (Path(directory)/n).is_symlink():raise ValueError('Source symlinks refused')
  for n in filenames:
   if n=='.env' or n.startswith('.env.') or n.endswith(('.jsonl','.log')):continue
   p=Path(directory)/n
   if p.is_symlink():raise ValueError('Source symlinks refused')
   yield p
def hashes(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files(root)}
def copy(source,target):
 for p in files(source):
  d=target/p.relative_to(source);d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,d)
def inner(oracle):
 status=dict(x.split(':',1) for x in Path('/proc/self/status').read_text().splitlines() if ':' in x)
 assert int(status['CapEff'],16)==0 and status['NoNewPrivs'].strip()=='1'
 assert not Path('/home').exists() and not Path('/root').exists() and not Path('/work/.git').exists() and not Path('/work/.env').exists()
 for p in ['/work/README.md']+(['/oracle/test_independent.py'] if oracle else []):
  try:os.open(p,os.O_WRONLY)
  except OSError as e:assert e.errno==errno.EROFS
  else:raise AssertionError('Source or oracle writable')
 with socket.socket() as s:
  try:s.connect(('1.1.1.1',443))
  except OSError as e:assert e.errno==errno.ENETUNREACH
  else:raise AssertionError('Network egress')
 print('PROOF source/oracleRO emptyhome noenv CapEff0 NoNewPrivs1 ENETUNREACH',flush=True)
 subprocess.run([str(Path(sys.executable).resolve()),'-B','-m','unittest','discover','-s','/oracle' if oracle else 'tests','-v'],check=True,timeout=90,stdin=subprocess.DEVNULL)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--oracle-dir');p.add_argument('--inner',action='store_true');a=p.parse_args()
 if a.inner:inner(bool(a.oracle_dir));return
 before=hashes(ROOT)
 spec=importlib.util.spec_from_file_location('workshop_trusted_engine_guard',ROOT/'scripts/engine-guard.py')
 guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
 guard.guard_engine_source((ROOT/'planejador_oficinas/core.py').read_text(encoding='utf-8'))
 with tempfile.TemporaryDirectory(prefix='workshop-check-') as temporary:
  scratch=Path(temporary);source=scratch/'source';copy(ROOT,source);assert hashes(source)==before
  if a.oracle_dir:
   original=Path(a.oracle_dir).resolve(strict=True);frozen=hashes(original);oracle=scratch/'oracle';copy(original,oracle);assert hashes(oracle)==frozen
  hosted=all(os.environ.get(k)==v for k,v in (('GITHUB_ACTIONS','true'),('CI','true'),('RUNNER_ENVIRONMENT','github-hosted'),('RUNNER_OS','Linux')))
  if hosted:
   scratch.chmod(0o755)
   for entry in source.rglob('*'):entry.chmod(0o755 if entry.is_dir() else 0o666)
   source.chmod(0o755)
   if a.oracle_dir:
    for entry in oracle.rglob('*'):entry.chmod(0o755 if entry.is_dir() else 0o666)
    oracle.chmod(0o755)
  command=['bwrap','--unshare-all',*(['--unshare-user'] if os.geteuid()!=0 else []),'--disable-userns','--cap-drop','ALL','--die-with-parent','--new-session','--clearenv']
  for n in ['usr','bin','sbin','lib','lib64']:
   path=Path('/')/n
   if path.is_symlink():command+=['--symlink',os.readlink(path),'/'+n]
   elif path.exists():command+=['--ro-bind',str(path),str(path)]
  if Path('/etc/ld.so.cache').exists():command+=['--ro-bind','/etc/ld.so.cache','/etc/ld.so.cache']
  command+=['--proc','/proc','--dev','/dev','--size','268435456','--tmpfs','/tmp','--ro-bind',str(source),'/work']
  if a.oracle_dir:command+=['--ro-bind',str(oracle),'/oracle']
  for k,v in {'PATH':'/usr/bin:/bin','HOME':'/tmp','LANG':'C.UTF-8','TMPDIR':'/tmp','PYTHONPATH':'/work','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'}.items():command+=['--setenv',k,v]
  executable=Path(sys.executable).resolve();prefix=Path(sys.prefix).resolve()
  if prefix!=Path('/usr') and not prefix.is_relative_to('/usr'):
   if not(hosted and prefix.is_relative_to('/opt/hostedtoolcache/Python') and executable.is_relative_to(prefix)):
    raise ValueError('Trusted Python runtime unavailable')
   command+=['--ro-bind',str(prefix),str(prefix),'--setenv','LD_LIBRARY_PATH',str(prefix/'lib')]
  command+=['--chdir','/work','--','/usr/bin/setpriv','--no-new-privs',str(executable),'-B','/work/scripts/checks-offline.py','--inner']
  if a.oracle_dir:command+=['--oracle-dir','/oracle']
  if hosted:command=['sudo','-n',*command]
  result=subprocess.run(command,env={'PATH':'/usr/bin:/bin'},timeout=120,stdin=subprocess.DEVNULL)
  assert hashes(source)==before and hashes(ROOT)==before,'Source changed'
  if a.oracle_dir:assert hashes(oracle)==frozen and hashes(original)==frozen,'Oracle changed'
  if result.returncode:raise SystemExit(result.returncode)
 print('Checks passed; source/oracle hashes preserved.')
if __name__=='__main__':main()
