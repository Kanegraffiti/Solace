import hashlib

import pytest


def test_load_config_creates_defaults_and_dirs(reload_modules):
    configuration = reload_modules["solace.configuration"]

    config = configuration.load_config()
    configuration.ensure_storage_dirs(config)
    configuration.save_config(config)

    storage_paths = list(configuration.list_known_paths(config))
    assert storage_paths, "expected default storage paths to be present"
    for path in storage_paths:
        assert path.exists()
        assert path.is_dir()
    assert configuration.CONFIG_PATH.exists()


def test_get_cipher_uses_seed_and_round_trips(reload_modules):
    configuration = reload_modules["solace.configuration"]

    config = configuration.load_config()
    cipher = configuration.get_cipher(config, password="seed-password")

    token = cipher.encrypt(b"hello world")
    assert cipher.decrypt(token) == b"hello world"


@pytest.mark.parametrize(
    "attempts,raises",
    [
        (["secret"], False),
        (["wrong", "nope", "bad"], True),
    ],
)
def test_verify_password_prompts(monkeypatch, reload_modules, attempts, raises):
    configuration = reload_modules["solace.configuration"]
    config = configuration.load_config()

    security = config.setdefault("security", {})
    security.update(
        {
            "password_enabled": True,
            "password_hash": hashlib.sha256(b"secret").hexdigest(),
            "encryption_enabled": True,
        }
    )
    configuration.save_config(config)

    guesses = iter(attempts)
    monkeypatch.setattr("getpass.getpass", lambda *_args, **_kwargs: next(guesses))

    if raises:
        with pytest.raises(PermissionError):
            configuration.verify_password(config)
    else:
        assert configuration.verify_password(config) == "secret"
