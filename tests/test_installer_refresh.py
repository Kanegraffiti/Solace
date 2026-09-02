import importlib.util
from pathlib import Path


def _load_installer():
    path = Path(__file__).resolve().parents[1] / "install.py"
    spec = importlib.util.spec_from_file_location("solace_installer", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_refresh_preserves_existing_profile_and_password(monkeypatch, tmp_path, capsys):
    installer = _load_installer()
    config_path = tmp_path / ".solaceconfig.json"
    config_path.write_text("{}", encoding="utf-8")
    existing = {
        "alias": "my-solace",
        "profile": {"name": "Anna", "goal": "Bash fluency"},
        "security": {
            "password_enabled": True,
            "password_hash": "existing-hash",
            "salt": "existing-salt",
        },
    }
    password_calls = []
    saved = []
    storage_calls = []
    monkeypatch.setattr(installer, "CONFIG_PATH", config_path)
    monkeypatch.setattr(installer, "load_config", lambda: existing)
    monkeypatch.setattr(installer, "save_config", lambda config: saved.append(config))
    monkeypatch.setattr(installer, "set_password", lambda config: password_calls.append(config))
    monkeypatch.setattr(installer, "ensure_storage_dirs", lambda config: storage_calls.append(config))

    installer._initialise_config("solace", preserve_existing=True)

    assert existing["alias"] == "my-solace"
    assert existing["security"]["password_hash"] == "existing-hash"
    assert password_calls == []
    assert saved == []
    assert storage_calls == [existing]
    assert "profile and security settings preserved" in capsys.readouterr().out


def test_normal_install_still_runs_password_onboarding(monkeypatch, tmp_path):
    installer = _load_installer()
    config_path = tmp_path / ".solaceconfig.json"
    config_path.write_text("{}", encoding="utf-8")
    existing = {"profile": {"name": "Anna", "goal": "journal"}}
    password_calls = []
    monkeypatch.setattr(installer, "CONFIG_PATH", config_path)
    monkeypatch.setattr(installer, "load_config", lambda: existing)
    monkeypatch.setattr(installer, "save_config", lambda config: None)
    monkeypatch.setattr(installer, "ensure_storage_dirs", lambda config: None)
    monkeypatch.setattr(installer, "set_password", lambda config: password_calls.append(config))

    installer._initialise_config("solace")

    assert password_calls == [existing]
