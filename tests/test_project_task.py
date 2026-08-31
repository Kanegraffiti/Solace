import stat
import subprocess
import zipfile
from pathlib import Path

import pytest

from solace.project_task import (
    ProjectTaskError,
    choose_project_matches,
    execute_project_command,
    extract_zip,
    inspect_project,
    prepare_project_command,
    project_query,
    validate_zip,
    wants_project_execution,
)


def test_project_query_supports_conversational_and_explicit_requests() -> None:
    assert project_query('inspect "Lola website"') == "Lola website"
    assert project_query("find my portfolio zip in downloads, unpack it and inspect it") == "portfolio"
    assert project_query("analyse storefront project") == "storefront"
    assert project_query("run storefront") == "storefront"
    assert wants_project_execution("run storefront") is True
    assert wants_project_execution("inspect storefront") is False


def test_choose_project_matches_ignores_files_and_nested_duplicates(tmp_path: Path) -> None:
    project = tmp_path / "shop"
    nested = project / "src"
    nested.mkdir(parents=True)
    text = tmp_path / "shop.txt"
    text.write_text("not a project", encoding="utf-8")

    assert choose_project_matches([nested, text, project]) == [project]


def test_extract_zip_keeps_archive_and_returns_single_project_root(tmp_path: Path) -> None:
    archive = tmp_path / "storefront.zip"
    with zipfile.ZipFile(str(archive), "w") as bundle:
        bundle.writestr("storefront/package.json", '{"scripts":{"dev":"vite"},"devDependencies":{"vite":"latest"}}')

    root = extract_zip(archive)

    assert archive.exists()
    assert root == tmp_path / "storefront" / "storefront"
    assert (root / "package.json").exists()


def test_zip_path_traversal_is_refused_without_creating_destination(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(str(archive), "w") as bundle:
        bundle.writestr("../escaped.txt", "no")

    with pytest.raises(ProjectTaskError, match="unsafe path"):
        validate_zip(archive)

    assert not (tmp_path / "unsafe").exists()
    assert not (tmp_path / "escaped.txt").exists()


def test_zip_symbolic_link_is_refused(tmp_path: Path) -> None:
    archive = tmp_path / "links.zip"
    link = zipfile.ZipInfo("project/link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(str(archive), "w") as bundle:
        bundle.writestr(link, "../../outside")

    with pytest.raises(ProjectTaskError, match="symbolic link"):
        validate_zip(archive)


def test_inspect_vite_project_uses_package_scripts(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"scripts":{"dev":"vite"},"dependencies":{"react":"latest"},"devDependencies":{"vite":"latest"}}',
        encoding="utf-8",
    )
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")

    result = inspect_project(tmp_path)

    assert result.stack == ["Node.js", "Vite", "React"]
    assert result.evidence == ["package.json"]
    assert result.next_commands == ["npm install", "npm run dev"]


def test_inspect_static_and_python_projects(tmp_path: Path) -> None:
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<h1>Hello</h1>", encoding="utf-8")
    assert inspect_project(static).next_commands == ["python -m http.server 8000"]

    python = tmp_path / "api"
    python.mkdir()
    (python / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (python / "manage.py").write_text("", encoding="utf-8")
    result = inspect_project(python)
    assert result.stack == ["Python", "Django"]
    assert "python manage.py runserver" in result.next_commands


def test_existing_extraction_destination_is_never_merged(tmp_path: Path) -> None:
    archive = tmp_path / "site.zip"
    with zipfile.ZipFile(str(archive), "w") as bundle:
        bundle.writestr("index.html", "new")
    destination = tmp_path / "site"
    destination.mkdir()
    original = destination / "keep.txt"
    original.write_text("keep", encoding="utf-8")

    with pytest.raises(ProjectTaskError, match="already exists"):
        extract_zip(archive)

    assert original.read_text(encoding="utf-8") == "keep"


def test_project_command_must_come_from_inspection(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("hello", encoding="utf-8")
    inspection = inspect_project(tmp_path)

    with pytest.raises(ProjectTaskError, match="only run commands produced"):
        prepare_project_command("rm -rf .", inspection)


def test_project_command_runs_without_a_shell(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "package.json").write_text(
        '{"scripts":{"dev":"vite"}}', encoding="utf-8"
    )
    inspection = inspect_project(tmp_path)
    prepared = prepare_project_command("npm run dev", inspection)
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr("solace.project_task.subprocess.run", fake_run)

    assert execute_project_command(prepared, tmp_path) == 0
    assert calls[0][0] == ["npm", "run", "dev"]
    assert calls[0][1]["cwd"] == str(tmp_path.resolve())
    assert calls[0][1]["shell"] is False
