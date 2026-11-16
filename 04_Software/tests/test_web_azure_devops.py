"""Azure enrollment, settings, RBAC and prerequisite contracts offline."""

import json
from pathlib import Path

from adore.config import load_config, validate_config
from adore.profiles import ProfileStore
from adore.util import CommandResult
from adore.web.app import create_app
from adore.wizard import ScriptedAsker, WizardSetup, run_wizard
import pytest

from tests.configuration_client import TestClient


def body(tmp_path, **changes):
    clone = tmp_path / "clone"
    (clone / ".git").mkdir(parents=True, exist_ok=True)
    return {"name": "azure", "kind": "azure_devops", "repo": "backend",
            "organization": "https://dev.azure.com/contoso", "project": "Payments",
            "area_path": "Payments\\Backend", "repo_path": str(clone),
            "provider": "openai", "model": "gpt-5.5", "image": "adore-test:latest",
            **changes}


def login(client):
    response = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
    return {"X-CSRF-Token": response.json()["csrf"]}


def offline(argv, **kwargs):
    return CommandResult(argv=argv, exit_code=127)


# PUBLIC API / TESTS

def test_cli_wizard_azure_answers_validate_without_az_global_defaults(tmp_path):
    answers = body(tmp_path)
    answers.pop("name")
    answers["confirm"] = "yes"
    setup = run_wizard(ProfileStore(tmp_path / "home"), name="azure",
                       asker=ScriptedAsker(answers, interactive=False), prepare_only=True,
                       runner=offline, out=lambda _: None)
    assert isinstance(setup, WizardSetup)
    path = tmp_path / "azure.toml"
    path.write_text(setup.document, encoding="utf-8")
    config = load_config(path)
    assert validate_config(config) == []
    assert config.platform.kind == "azure_devops"
    assert config.platform.area_path == "Payments\\Backend"


def test_web_azure_enrollment_and_settings_share_exact_scope_and_collections(tmp_path):
    app = create_app(tmp_path / "home", probe_runner=offline)
    with TestClient(app) as client:
        headers = login(client)
        result = client.post("/api/v1/projects/setup-preview", json=body(tmp_path), headers=headers)
        assert result.status_code == 200, result.text
        preview = result.json()
        assert preview["structural_valid"] and preview["review"]["area_path"] == "Payments\\Backend"
        created = client.post("/api/v1/projects/setup-create", json={
            **body(tmp_path), "revision": preview["revision"]}, headers=headers)
        assert created.status_code == 200, created.text
        assert created.json()["paused"]
        response = client.get("/api/v1/projects/azure/config")
        assert response.status_code == 200, response.text
        value = response.json()
        assert value["config"]["platform"]["project"] == "Payments"
        metadata = {entry["key"]: entry for entry in value["settings"]}
        assert "azure_devops" in metadata["platform.kind"]["choices"]
        for key in ("platform.organization", "platform.project", "platform.area_path",
                    "platform.work_item_types", "platform.closed_states"):
            assert metadata[key]["editable"] and metadata[key]["restart"]
        revision = value["revision"]
        candidate = client.post("/api/v1/projects/azure/config/pending", headers=headers, json={
            "key": "platform.closed_states", "value": '["Closed","Released"]',
            "revision": revision})
        assert candidate.status_code == 200, candidate.text
        pending = candidate.json()
        applied = client.post("/api/v1/projects/azure/config/apply", headers=headers, json={
            "candidate_revision": pending["candidate_revision"],
            "base_revision": pending["base_revision"]})
        assert applied.status_code == 200, applied.text
        assert load_config(app.state.profiles.config_path("azure")).platform.closed_states == [
            "Closed", "Released"]
        current = client.get("/api/v1/projects/azure/config").json()
        invalid_names = client.post("/api/v1/projects/azure/config/pending", headers=headers,
            json={"key": "platform.work_item_types", "value": '[]',
                  "revision": current["revision"]})
        assert invalid_names.status_code == 400
        # External host authentication only; an origin/token form cannot save Azure credentials.
        invalid = client.post("/api/v1/projects/azure/repository-connection", json={
            "server": "https://dev.azure.com/contoso", "token": "not-a-real-secret",
            "allow_http": False}, headers=headers)
        assert invalid.status_code == 422
        assert invalid.json()["detail"]["code"] == "repository_connection_invalid"
        assert "not-a-real-secret" not in invalid.text


@pytest.mark.parametrize("changes", [{"organization": "https://onprem/tfs"},
    {"organization": "https://token@dev.azure.com/contoso"}, {"project": ""},
    {"area_path": "Payments"}, {"area_path": "Other\\Backend"},
    {"reviewers": "display-name"}, {"env_keys": ["AZURE_DEVOPS_EXT_PAT"]}])
def test_web_rejects_invalid_azure_scope_credentials_and_reviewers(tmp_path, changes):
    app = create_app(tmp_path / "home", probe_runner=offline)
    with TestClient(app) as client:
        headers = login(client)
        result = client.post("/api/v1/projects/setup-preview", json=body(tmp_path, **changes),
                             headers=headers)
        assert result.status_code == 200, result.text
        assert not result.json()["structural_valid"]
        assert not app.state.profiles.exists("azure")


def test_azure_repository_source_and_auth_checks_are_scoped_and_redacted(tmp_path, monkeypatch):
    monkeypatch.setattr("adore.web.app._readiness_host", lambda: "f" * 64)
    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        data = None
        if argv[:2] == ["git", "ls-remote"]:
            return CommandResult(argv=argv, exit_code=0, stdout=(
                "ref: refs/heads/main\tHEAD\n" + "a" * 40 + "\trefs/heads/main\n"))
        if argv[:2] == ["az", "--version"]:
            return CommandResult(argv=argv, exit_code=0, stdout="azure-cli 2.80.0")
        if argv[:3] == ["az", "extension", "show"]:
            data = {"name": "azure-devops", "version": "1.0.2"}
        if argv[-2] == "request":
            spec = json.loads(Path(argv[-1]).read_text(encoding="utf-8"))
            resource = spec["resource"]
            assert spec["route"]["project"] == "Payments"
            assert spec["organization"] == "https://dev.azure.com/contoso"
            data = ({"name": "backend", "project": {"name": "Payments"}}
                    if resource == "repositories" else
                    {"id": 3, "path": "\\Payments\\Area\\Backend", "structureType": "area"}
                    if resource == "classificationNodes" else {"workItems": []})
        return CommandResult(argv=argv, exit_code=0 if data is not None else 127,
                             stdout=json.dumps(data) if data is not None else "")

    app = create_app(tmp_path / "home", probe_runner=runner)
    with TestClient(app) as client:
        headers = login(client)
        url = "https://dev.azure.com/contoso/Payments/_git/backend"
        detected = client.post("/api/v1/projects/repository-source", json={"url": url},
                               headers=headers)
        assert detected.status_code == 200, detected.text
        assert detected.json()["kind"] == "azure_devops"
        assert detected.json()["organization"] == "https://dev.azure.com/contoso"
        draft = body(tmp_path)
        preview = client.post("/api/v1/projects/setup-preview", json=draft, headers=headers).json()
        result = client.post("/api/v1/projects/setup-check", json={
            **draft, "revision": preview["revision"]}, headers=headers)
        assert result.status_code == 200, result.text
        assert result.json()["checks"]["forge_auth"] is True
        assert result.json()["checks"]["forge_cli"] is True
        assert all("--auto-complete" not in argv for argv in calls)
