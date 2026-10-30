"""Real shell helpers with fictional Git/Docker boundaries; no daemon or Git writes."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ["harness-machine-monitor.sh", "harness-machine-watchdog.sh"]


@pytest.fixture
def fixture(tmp_path):
    project = tmp_path / "fixture ' $(printf FICTIONAL_PATH) `printf FICTIONAL_TICK`"
    (project / "scripts").mkdir(parents=True)
    (project / ".git/objects").mkdir(parents=True)
    (project / "docker-compose.harness-machine.yaml").write_text("services: {}\n")
    for name in SCRIPTS:
        shutil.copyfile(ROOT / "templates/scripts" / name, project / "scripts" / name)
    commands = tmp_path / "commands"
    commands.mkdir()
    fake_git = '''import json,os,sys
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['FAKE_CALLS'],'a') as stream:stream.write(json.dumps({'tool':'git','args':args,'cwd':os.getcwd()})+'\\n')
assert args[:2]==['-C',os.environ['FAKE_PROJECT']]
args=args[2:]
if args==['rev-parse','--show-toplevel']:print(os.environ.get('FAKE_GIT_ROOT',os.environ['FAKE_PROJECT']))
elif args[:1]==['status']:
 if os.environ.get('FAKE_STATUS_FAIL')=='1':sys.exit(16)
 print('?? fictional.txt' if os.environ.get('FAKE_DIRTY')=='1' else '')
elif args[:1]==['rev-parse']:print('abc123')
elif args[:1]==['rev-list']:print('0')
elif args[:1] in [['add'],['commit']]:sys.exit(17 if os.environ.get('FAKE_GIT_SAVE_FAIL')=='1' else 0)
else:raise AssertionError(args)
'''
    fake_docker = '''import json,os,sys
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['FAKE_CALLS'],'a') as stream:stream.write(json.dumps({'tool':'docker','args':args,'cwd':os.getcwd()})+'\\n')
flag=Path(os.environ['FAKE_STARTED'])
state='running' if flag.exists() else os.environ.get('FAKE_CONTAINER_STATE','running')
if args[0]=='compose':
 if 'ps' in args and '--quiet' in args:print('a'*64)
 elif 'images' in args:print('sha256:'+'b'*64)
 elif 'ps' in args:
  if os.environ.get('FAKE_BAD_JSON')=='1':print('{broken')
  else:print(json.dumps([{'State':state}]))
 elif 'down' in args:sys.exit(18 if os.environ.get('FAKE_STOP_FAIL')=='1' else 0)
 elif 'up' in args:
  if os.environ.get('FAKE_START_FAIL')=='1':sys.exit(19)
  if os.environ.get('FAKE_STILL_STOPPED')!='1':flag.write_text('running')
 else:raise AssertionError(args)
elif args[0]=='inspect':print(state)
elif args[0]=='stats':print('0.00%' if any('CPUPerc' in a for a in args) else '10MiB / 1GiB')
elif args[0]=='logs':print('attempt 1')
elif args[0]=='run':
 assert args[args.index('--entrypoint')+1]=='chown' and '-c' not in args
 if os.environ.get('FAKE_CHOWN_FAIL')=='1':sys.exit(20)
 Path(args[-1]).chmod(0o600)
else:raise AssertionError(args)
'''
    for name, content in [("git", fake_git), ("docker", fake_docker)]:
        path = commands / name
        path.write_text("#!" + sys.executable + "\n" + content)
        path.chmod(0o700)
    (commands / "python3").symlink_to(sys.executable)
    env = {k: v for k, v in os.environ.items() if not any(s in k.upper() for s in ["TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "API_KEY"])}
    env.update(PATH=str(commands) + os.pathsep + env["PATH"], FAKE_PROJECT=str(project), FAKE_CALLS=str(tmp_path / "calls.jsonl"), FAKE_STARTED=str(tmp_path / "started"), PYTHONDONTWRITEBYTECODE="1")
    def run(name, **overrides):
        return subprocess.run(["/bin/bash", str(project / "scripts" / name)], cwd=tmp_path, env={**env, **overrides}, capture_output=True, text=True, timeout=20)
    def calls():
        p=Path(env['FAKE_CALLS']);return [json.loads(s) for s in p.read_text().splitlines()] if p.exists() else []
    return project, run, calls


@pytest.mark.parametrize("name", SCRIPTS)
def test_failed_cd_exits_before_any_git_or_docker(fixture, name):
    project, run, calls = fixture
    result = run(name, HARNESS_MACHINE_PROJECT_DIR=str(project / "missing"))
    assert result.returncode != 0 and "cannot enter project" in result.stderr
    assert calls() == []


@pytest.mark.parametrize("name", SCRIPTS)
def test_wrong_git_root_has_no_mutation_or_docker(fixture, name):
    project, run, calls = fixture
    result = run(name, FAKE_GIT_ROOT=str(project.parent))
    assert result.returncode != 0
    assert len(calls()) == 1 and calls()[0]["tool"] == "git"
    assert "worktree root" in result.stderr


def test_monitor_literal_paths_and_state_data_without_eval(fixture):
    project, run, calls = fixture
    state = {"epoch": 25, "environments": {"fictional": {"status": "blocked", "blockers": [{"description": "$(printf FICTIONAL_LABEL)", "since": 1}]}}, "blockers": []}
    (project / "STATE.yaml").write_text(yaml.safe_dump(state))
    result = run(SCRIPTS[0])
    assert result.returncode == 0, result.stderr
    assert yaml.safe_load((project / "STATE.yaml").read_text())["environments"]["fictional"]["status"] == "deferred"
    assert "$(printf FICTIONAL_LABEL)" in (project / "harness-machine-monitor.log").read_text()
    assert not any(r["tool"] == "git" and r["args"][2] in {"add", "commit"} for r in calls())


def test_monitor_resets_stale_state_and_saves_only_verified_project(fixture):
    project, run, calls = fixture
    (project / "STATE.yaml").write_text(yaml.safe_dump({"environments": {"fictional": {"status": "in-progress"}}}))
    result = run(SCRIPTS[0], FAKE_CONTAINER_STATE="exited", FAKE_DIRTY="1")
    assert result.returncode != 0  # A stopped container is an unhealthy result.
    assert yaml.safe_load((project / "STATE.yaml").read_text())["environments"]["fictional"]["status"] == "ready"
    mutations=[r for r in calls() if r["tool"]=='git' and r['args'][2] in {'add','commit'}]
    assert len(mutations)==2 and all(r['args'][:2]==['-C',str(project)] and r['cwd']==str(project) for r in mutations)


@pytest.mark.parametrize("name", SCRIPTS)
def test_log_ownership_path_is_argv_not_shell_program(fixture, name):
    project, run, calls = fixture
    log = project / name.replace('.sh','.log')
    log.write_text('fictional log\n');log.chmod(0o400)
    result = run(name)
    assert result.returncode==0, result.stderr
    chown=[r for r in calls() if r['tool']=='docker' and r['args'][0]=='run']
    assert len(chown)==1 and chown[0]['args'][-1]==str(log)
    assert chown[0]['args'][chown[0]['args'].index('--entrypoint')+1]=='chown'
    assert '-c' not in chown[0]['args']


@pytest.mark.parametrize("flag,expected", [("FAKE_START_FAIL", "startup failed"), ("FAKE_STOP_FAIL", "stop failed"), ("FAKE_STILL_STOPPED", "did not reach running")])
def test_watchdog_never_reports_failed_restart_as_success(fixture, flag, expected):
    project, run, calls = fixture
    result = run(SCRIPTS[1], FAKE_CONTAINER_STATE="exited", **{flag:"1"})
    log=(project/'harness-machine-watchdog.log').read_text()
    assert result.returncode != 0 and expected in log
    assert 'Container restarted and running' not in log


def test_watchdog_confirms_running_after_successful_restart(fixture):
    project, run, calls = fixture
    result = run(SCRIPTS[1], FAKE_CONTAINER_STATE="exited")
    assert result.returncode==0, result.stderr
    assert 'Container restarted and running' in (project/'harness-machine-watchdog.log').read_text()


def test_malformed_state_fails_and_does_not_claim_heal(fixture):
    project, run, calls = fixture
    (project/'STATE.yaml').write_text('broken: [')
    result=run(SCRIPTS[0])
    assert result.returncode != 0
    assert 'STATE.yaml parsing failed' in (project/'harness-machine-monitor.log').read_text()


def test_git_status_failure_cannot_save_or_claim_healthy(fixture):
    project, run, calls = fixture
    result=run(SCRIPTS[0], FAKE_STATUS_FAIL='1', FAKE_DIRTY='1', FAKE_CONTAINER_STATE='exited')
    assert result.returncode != 0
    assert 'Git status failed' in (project/'harness-machine-monitor.log').read_text()
    assert not any(r['tool']=='git' and r['args'][2] in {'add','commit'} for r in calls())


def test_watchdog_invalid_counter_is_data_not_arithmetic(fixture):
    project, run, calls = fixture
    (project/'.watchdog-last-commit').write_text('abc123')
    (project/'.watchdog-zero-count').write_text('$(printf FICTIONAL_COUNT)')
    result=run(SCRIPTS[1])
    assert result.returncode != 0
    assert 'invalid watchdog counter' in (project/'harness-machine-watchdog.log').read_text()


def test_watchdog_idle_restart_failure_is_nonzero(fixture):
    project, run, calls = fixture
    (project/'.watchdog-last-commit').write_text('abc123')
    (project/'.watchdog-zero-count').write_text('3')
    result=run(SCRIPTS[1], FAKE_START_FAIL='1')
    assert result.returncode != 0
    log=(project/'harness-machine-watchdog.log').read_text()
    assert 'container startup failed' in log and 'Container restarted and running' not in log


@pytest.mark.parametrize("name", SCRIPTS)
def test_symlinked_log_is_not_written(fixture, name):
    project, run, calls = fixture
    outside=project.parent/'fictional-outside.log';outside.write_text('unchanged')
    (project/name.replace('.sh','.log')).symlink_to(outside)
    result=run(name)
    assert result.returncode != 0 and 'symlinks' in result.stderr
    assert outside.read_text()=='unchanged'
