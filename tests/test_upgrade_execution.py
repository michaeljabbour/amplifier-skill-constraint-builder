"""Execute real recipe Bash with fictional data and no provider/container calls."""
from pathlib import Path
import json
import os
import re
import subprocess
import sys
import tomllib

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CHECK = yaml.safe_load((ROOT / "recipes/check-upgrade.yaml").read_text())
UPGRADE = yaml.safe_load((ROOT / "recipes/execute-upgrade.yaml").read_text())
STEPS = {s["id"]: s for s in CHECK["steps"] + UPGRADE["stages"][1]["steps"]}


def run_step(identifier, context):
    step = STEPS[identifier]
    # Match official step.env substitution; command source remains static.
    env = {k: v for k, v in os.environ.items() if not any(s in k.upper() for s in ["KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL"])}
    env.update(AMPLIFIER_PYTHON=sys.executable, PYTHONDONTWRITEBYTECODE="1")
    for key, template in step["env"].items():
        def resolve(match):
            value = context
            for part in match.group(1).strip().split("."):
                value = value[part]
            return str(value)
        env[key] = re.sub(r"\{\{([^{}]+)\}\}", resolve, template)
    return subprocess.run(["/bin/bash", "-c", step["command"]], cwd=ROOT, env=env, capture_output=True, text=True, timeout=20)


def backup_context(target):
    context = {"target_path": str(target), "version_file": str(ROOT / "context/version.md")}
    result = run_step("backup", context)
    assert result.returncode == 0, result.stderr
    context["upgrade_backup"] = json.loads(result.stdout)
    return context


@pytest.mark.parametrize("identifier", [s for s in STEPS if STEPS[s].get("type") == "bash"])
def test_real_bash_syntax_and_no_template_source(identifier):
    step = STEPS[identifier]
    assert "{{" not in step["command"]
    assert step["env"]
    assert step["on_error"] == "fail"
    result = subprocess.run(["/bin/bash", "-n", "-c", step["command"]], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_read_and_present_preserve_shell_markers_as_literal_data(tmp_path):
    target = tmp_path / "fixture ' $(printf FICTIONAL_PATH) `printf FICTIONAL_TICK`"
    target.mkdir()
    (target / "config.yaml").write_text("generated_version: 0.1.0\n")
    report = 'upgrade available yes\n$(printf FICTIONAL_REPORT) `printf FICTIONAL_REPORT_TICK` " \' '
    context = {"target_path": str(target), "upgrade_report": report}
    read = run_step("read-version-stamp", context)
    assert read.returncode == 0 and "generated_version: 0.1.0" in read.stdout
    shown = run_step("present-report", context)
    assert shown.returncode == 0, shown.stderr
    assert str(target) in shown.stdout and report in shown.stdout


def test_missing_version_source_is_failure(tmp_path):
    result = run_step("read-version-stamp", {"target_path": str(tmp_path)})
    assert result.returncode != 0 and "ERROR" in result.stderr


def test_upgrade_without_config_uses_latest_and_actual_unique_backup(tmp_path):
    target = tmp_path / "fixture ' $(printf FICTIONAL_PATH)"
    target.mkdir()
    original = "---\nbundle:\n  name: fictional\n  version: 0.1.0\n---\n\nFictional guide.\n"
    (target / "bundle.md").write_text(original)
    context = backup_context(target)
    backup = Path(context["upgrade_backup"]["backup_path"])
    assert backup.is_dir() and backup.parent == target.parent
    result = run_step("execute-upgrade", context)
    assert result.returncode == 0, result.stderr + result.stdout
    data = json.loads(result.stdout)
    assert data["status"] == "success" and data["version"] == "0.2.0"
    assert data["backup_path"] == str(backup)
    assert data["files_modified"] == ["bundle.md"]
    assert "version: 0.2.0" in (target / "bundle.md").read_text()
    assert (backup / "bundle.md").read_text() == original
    assert run_step("validate", context).returncode == 0


def test_all_version_files_update_and_remain_parseable(tmp_path):
    (tmp_path / "config.yaml").write_text("generated_version: 0.1.0\ntier: pico\n")
    (tmp_path / "behaviors").mkdir()
    behavior = tmp_path / "behaviors" / "fixture ' $(printf FICTIONAL_NAME).yaml"
    behavior.write_text("bundle:\n  name: fixture\n  version: 0.1.0\n")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "fictional"\nversion = "0.1.0"\n\n[tool.fixture]\nversion = "untouched"\n')
    (tmp_path / "constraints.py").write_text("def is_legal_action(tool, args):\n    return True, ''\n")
    context = backup_context(tmp_path)
    result = run_step("execute-upgrade", context)
    assert result.returncode == 0, result.stderr + result.stdout
    assert yaml.safe_load((tmp_path / "config.yaml").read_text())["generated_version"] == "0.2.0"
    assert yaml.safe_load(behavior.read_text())["bundle"]["version"] == "0.2.0"
    project = tomllib.loads((tmp_path / "pyproject.toml").read_text())
    assert project["project"]["version"] == "0.2.0"
    assert project["tool"]["fixture"]["version"] == "untouched"
    assert run_step("validate", context).returncode == 0


def test_invalid_python_fails_before_any_upgrade_write(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("generated_version: 0.1.0\n")
    (tmp_path / "broken.py").write_text("def fictional(:\n")
    context = backup_context(tmp_path)
    result = run_step("execute-upgrade", context)
    assert result.returncode != 0
    assert json.loads(result.stdout)["status"] == "failed"
    assert json.loads(result.stdout)["files_modified"] == []
    assert config.read_text() == "generated_version: 0.1.0\n"
    assert Path(context["upgrade_backup"]["backup_path"]).is_dir()


@pytest.mark.parametrize("filename,content", [("config.yaml", "broken: ["), ("constraints.py", "def fictional(:")])
def test_validation_failure_exits_nonzero(tmp_path, filename, content):
    (tmp_path / filename).write_text(content)
    result = run_step("validate", {"target_path": str(tmp_path)})
    assert result.returncode != 0
    assert json.loads(result.stdout)["status"] == "failed"


def test_wrong_backup_receipt_refuses_upgrade(tmp_path):
    (tmp_path / "config.yaml").write_text("generated_version: 0.1.0\n")
    context = backup_context(tmp_path)
    context["upgrade_backup"]["target_path"] = str(tmp_path.parent)
    result = run_step("execute-upgrade", context)
    assert result.returncode != 0
    assert "Backup receipt" in json.loads(result.stdout)["error"]


def test_missing_version_declaration_is_not_fabricated(tmp_path):
    (tmp_path / "config.yaml").write_text("generated_version: 0.1.0\n")
    context = backup_context(tmp_path)
    version = tmp_path.parent / "fictional-version.md"
    version.write_text("No version declaration.\n")
    context["version_file"] = str(version)
    result = run_step("execute-upgrade", context)
    assert result.returncode != 0 and "valid HARNESS_MACHINE_VERSION" in json.loads(result.stdout)["error"]


def test_escaping_symlink_is_not_modified(tmp_path):
    outside = tmp_path.parent / "fictional-outside.yaml"
    outside.write_text("generated_version: 0.1.0\n")
    (tmp_path / "config.yaml").symlink_to(outside)
    result = run_step("execute-upgrade", backup_context(tmp_path))
    assert result.returncode != 0
    assert outside.read_text() == "generated_version: 0.1.0\n"


def test_compose_has_no_ssh_forwarding_and_keeps_hardening():
    content = (ROOT / "templates/docker-compose.harness-machine.yaml").read_text()
    values = {"project_name": "fictional", "user_uid": "1000", "user_gid": "1000", "container_name": "fictional", "image_name": "fictional", "project_dir": "/workspace/fictional", "bundle_dir": "/workspace/bundle"}
    for name, value in values.items():
        content = content.replace("{{" + name + "}}", value)
    service = yaml.safe_load(content)["services"]["harness-machine"]
    volumes = service["volumes"]
    assert not any("ssh-agent" in p or "known_hosts" in p for p in volumes)
    assert "SSH_AUTH_SOCK" not in service.get("environment", [])
    assert service["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in service["security_opt"]
    assert any("HARNESS_MACHINE_KEYS_FILE:?" in p for p in service["env_file"])
    assert any(p.endswith(":ro") and "/workspace/bundle" in p for p in volumes)
    dockerfile = (ROOT / "templates/harness-machine.Dockerfile").read_text()
    assert 'url."git@github.com:".insteadOf' not in dockerfile
    monitor = (ROOT / "templates/scripts/harness-machine-monitor.sh").read_text()
    assert not re.search(r"(?m)^\s*(?:if\s+)?git (?:push|pull|stash)\b", monitor)
