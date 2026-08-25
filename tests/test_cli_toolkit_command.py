from types import SimpleNamespace


class FakeToolkit:
    available = True

    def __init__(self):
        self.calls = []

    def version(self):
        return "v1.0-alpha"

    def root(self):
        return "/tmp/.termux-toolkit"

    def list_tools(self):
        return ["move-files", "ping-check"]

    def has(self, tool):
        return tool == "move-files"

    def run(self, tool, arguments):
        self.calls.append((tool, list(arguments)))
        return SimpleNamespace(returncode=0)

    def man(self, arguments):
        self.calls.append(("man", list(arguments)))
        return SimpleNamespace(returncode=0)


def test_toolkit_status_uses_discovery_interface(main_module, monkeypatch):
    client = FakeToolkit()
    printed = []
    monkeypatch.setattr(main_module, "ToolkitClient", lambda: client)
    monkeypatch.setattr(main_module.console, "print", lambda value, *args, **kwargs: printed.append(value))

    assert main_module._process_command("/toolkit status") is True
    assert printed


def test_toolkit_run_preserves_quoted_arguments(main_module, monkeypatch):
    client = FakeToolkit()
    monkeypatch.setattr(main_module, "ToolkitClient", lambda: client)

    assert main_module._process_command('/toolkit run move-files "My Photos" --help') is True
    assert client.calls == [("move-files", ["My Photos", "--help"])]
