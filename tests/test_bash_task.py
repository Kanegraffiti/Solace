import pytest

from solace.bash_task import BashTaskError, execute_bash_task, plan_bash_task


def test_find_plan_is_shell_free_and_checked(tmp_path):
    plan = plan_bash_task("find final invoice", home=tmp_path)

    assert plan.argv == ["find", str(tmp_path), "-iname", "*final invoice*"]
    assert plan.check.syntax_valid is True
    assert plan.effect == "Read-only file search"


def test_git_pull_is_fast_forward_only(tmp_path):
    project = tmp_path / "project"
    project.mkdir()

    plan = plan_bash_task("git pull project", home=tmp_path)

    assert plan.argv == ["git", "pull", "--ff-only"]
    assert plan.cwd == project
    assert plan.risk == "Medium"


def test_script_must_be_inside_home(tmp_path):
    outside = tmp_path.parent / "outside.sh"
    outside.write_text("echo unsafe", encoding="utf-8")

    with pytest.raises(BashTaskError, match="outside your home"):
        plan_bash_task("run script {}".format(outside), home=tmp_path)


@pytest.mark.parametrize(
    "task_text",
    [
        "download http://example.com/file.zip",
        "download https://user:secret@example.com/file.zip",
        "find *",
        "show process python; rm -rf ~",
        "make my phone faster",
    ],
)
def test_unsafe_or_unknown_requests_are_refused(tmp_path, task_text):
    with pytest.raises(BashTaskError):
        plan_bash_task(task_text, home=tmp_path)


def test_planning_download_does_not_create_a_directory(tmp_path):
    plan = plan_bash_task("download https://example.com/file.zip", home=tmp_path)

    assert plan.cwd == tmp_path
    assert list(tmp_path.iterdir()) == []


def test_execute_uses_argv_and_returns_bounded_output(tmp_path, monkeypatch):
    script = tmp_path / "hello.sh"
    script.write_text("printf 'abcdefghij'", encoding="utf-8")
    plan = plan_bash_task("run script hello.sh", home=tmp_path)

    result = execute_bash_task(plan, max_output_bytes=5)

    assert result.returncode == 0
    assert result.output.endswith("fghij")
    assert result.output_truncated is True


def test_backup_refuses_overwrite(tmp_path):
    source = tmp_path / "notes"
    source.mkdir()
    (tmp_path / "notes-solace-backup.tar.gz").touch()

    with pytest.raises(BashTaskError, match="already exists"):
        plan_bash_task("backup notes", home=tmp_path)
