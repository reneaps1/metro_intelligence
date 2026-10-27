"""IQ-F9: static checks of the two-edition VPS deployment.

Docker is not required: the compose file is interpolated here the way
`docker compose` does (`${VAR}` and `${VAR:-default}`), once per edition, and
the result is checked for the properties the runbook relies on. The real
`docker compose config` still runs on the VPS (scripts/deploy_edition.sh).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE = REPO_ROOT / "docker-compose.vps.yml"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
SCRIPT = REPO_ROOT / "scripts" / "deploy_edition.sh"

_VAR = re.compile(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}")

# Secrets every env file provides; their values do not matter here.
COMMON = {
    "POSTGRES_DB": "db",
    "POSTGRES_USER": "user",
    "POSTGRES_PASSWORD": "pw",
    "MINIO_ACCESS_KEY": "key",
    "MINIO_SECRET_KEY": "secret",
}
METROLOGY_ENV = dict(COMMON)  # the current .env on the VPS sets none of the new variables
INDUSTRIAL_ENV = {
    **COMMON,
    "INSTANCE": "metro-industrial",
    "PUBLIC_HOST": "industrial.example.invalid",
    "APP_ENV_FILE": ".env.industrial",
    "DEMO_PRIVATE_DIR": "/home/demo/metro-private",
}


def _render(env: dict[str, str]) -> dict:
    def sub(match: re.Match[str]) -> str:
        name, default = match.group(1), match.group(2)
        if name in env:
            return env[name]
        if default is None:
            raise KeyError(f"${{{name}}} has no default and is not set")
        return default

    return yaml.safe_load(_VAR.sub(sub, COMPOSE.read_text(encoding="utf-8")))


def _labels(cfg: dict, service: str) -> dict[str, str]:
    return dict(label.split("=", 1) for label in cfg["services"][service]["labels"])


def _names(cfg: dict) -> dict[str, str]:
    routers = {
        key.split(".")[3]
        for service in ("backend", "frontend")
        for key in _labels(cfg, service)
        if key.startswith("traefik.http.routers.")
    }
    return {
        "pgdata": cfg["volumes"]["pgdata"]["name"],
        "minio": cfg["volumes"]["minio-data"]["name"],
        "net_data": cfg["networks"]["net_data"]["name"],
        "routers": ",".join(sorted(routers)),
    }


def test_metrology_defaults_keep_the_current_deployment_names() -> None:
    cfg = _render(METROLOGY_ENV)
    assert _names(cfg) == {
        "pgdata": "metro_pgdata",
        "minio": "metro_minio_data",
        "net_data": "metro_net_data",
        "routers": "metro-api,metro-web",
    }
    assert cfg["name"] == "metro-intelligence"
    assert cfg["services"]["backend"]["env_file"] == [".env"]
    assert "Host(`metro.onkaizen.com.mx`)" in _labels(cfg, "frontend")["traefik.http.routers.metro-web.rule"]
    assert cfg["services"]["backend"]["volumes"] == ["./infra/demo-private-empty:/run/demo-private:ro"]
    assert (REPO_ROOT / "infra" / "demo-private-empty").is_dir()


def test_industrial_edition_shares_nothing_but_the_proxy_network() -> None:
    metro, industrial = _render(METROLOGY_ENV), _render(INDUSTRIAL_ENV)
    a, b = _names(metro), _names(industrial)
    for key in ("pgdata", "minio", "net_data"):
        assert a[key] != b[key], key
    assert set(a["routers"].split(",")).isdisjoint(b["routers"].split(","))
    # Only the reverse-proxy network is shared, and it is external to both projects.
    assert metro["networks"]["net_app"] == industrial["networks"]["net_app"] == {
        "name": "metro_net_app",
        "external": True,
    }
    assert industrial["networks"]["net_data"]["internal"] is True
    assert industrial["services"]["backend"]["env_file"] == [".env.industrial"]
    assert industrial["services"]["backend"]["volumes"] == ["/home/demo/metro-private:/run/demo-private:ro"]
    rule = _labels(industrial, "backend")["traefik.http.routers.metro-industrial-api.rule"]
    assert rule == "Host(`industrial.example.invalid`) && PathPrefix(`/api`)"


def test_no_fixed_container_names_and_data_services_stay_internal() -> None:
    cfg = _render(INDUSTRIAL_ENV)
    for name, service in cfg["services"].items():
        assert "container_name" not in service, name
        assert "ports" not in service, f"{name} must only be reachable through Traefik"
    for name in ("db", "minio"):
        assert cfg["services"][name]["networks"] == ["net_data"], name


def test_missing_secret_is_an_error_not_an_empty_string() -> None:
    with pytest.raises(KeyError):
        _render({k: v for k, v in METROLOGY_ENV.items() if k != "POSTGRES_PASSWORD"})


def test_workflow_checks_the_host_before_connecting_and_uses_the_script() -> None:
    wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = wf["jobs"]["deploy"]["steps"]
    names = [s.get("name", s.get("uses", "")) for s in steps]
    assert names.index("Check that VPS_HOST resolves") < names.index("Deploy to VPS via SSH")
    check = next(s for s in steps if s.get("name") == "Check that VPS_HOST resolves")
    assert "echo \"$VPS_HOST\"" not in check["run"], "never print the secret"
    ssh = next(s for s in steps if s.get("name") == "Deploy to VPS via SSH")
    assert "bash scripts/deploy_edition.sh" in ssh["with"]["script"]
    # `on:` parses as True in YAML 1.1.
    triggers = wf.get("on", wf.get(True))
    assert set(triggers) == {"push", "workflow_dispatch"}
    assert triggers["push"]["branches"] == ["main"]


def test_deploy_script_is_valid_bash_with_its_guards() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    for guard in ("APP_EDITION=", "SKIP industrial", "config --quiet", "app_edition", "/health"):
        assert guard in text, guard
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash not available for a syntax check")
    subprocess.run([bash, "-n", str(SCRIPT)], check=True)
