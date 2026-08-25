import importlib
import sys


def test_launcher_routes_update_without_starting_cli(temp_home, monkeypatch):
    sys.modules.pop("solace.launcher", None)
    launcher = importlib.import_module("solace.launcher")
    result = type(
        "UpdateResult",
        (),
        {
            "changed": False,
            "previous_commit": "same",
            "current_commit": "same",
            "preserved_data": [],
        },
    )()
    monkeypatch.setattr(launcher, "update_solace", lambda _: result)
    monkeypatch.setattr(launcher.core, "main", lambda _: (_ for _ in ()).throw(AssertionError("CLI started")))

    assert launcher.main(["update"]) == 0


def test_launcher_rejects_update_arguments(temp_home):
    sys.modules.pop("solace.launcher", None)
    launcher = importlib.import_module("solace.launcher")

    assert launcher.main(["update", "--force"]) == 2
