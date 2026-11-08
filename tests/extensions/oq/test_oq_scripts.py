"""Tests for the OQ extension's enforcement scripts (extensions/oq/scripts/bash/).

The scripts run against a real local git repository with a bare ``origin``.
``codex`` and ``gh`` are replaced by small stubs on PATH so the tests can
control the banner model, exit codes and PR metadata, and can see exactly
which arguments the scripts passed.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS = PROJECT_ROOT / "extensions" / "oq" / "scripts" / "bash"
REVIEW = SCRIPTS / "codex-review.sh"
GATE = SCRIPTS / "merge-gate.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash required")

CODEX_STUB = r"""#!/usr/bin/env bash
printf '%s\n' "$@" > "$STUB_DIR/codex-args"
echo "OpenAI Codex v0.0-stub"
echo "--------"
echo "model: ${FAKE_MODEL:-gpt-6.1-sol}"
echo "--------"
if [ -n "${FAKE_TOUCH:-}" ]; then echo dirty > "$FAKE_TOUCH"; fi
echo "codex"
echo "No issues found."
exit "${FAKE_RC:-0}"
"""

GH_STUB = r"""#!/usr/bin/env bash
case "$*" in
  *baseRefName*) [ -n "${FAKE_BASE:-}" ] && echo "$FAKE_BASE" && exit 0; exit 1 ;;
  *headRefOid*) [ -n "${FAKE_PR_HEAD:-}" ] && echo "$FAKE_PR_HEAD" && exit 0; exit 1 ;;
  *nameWithOwner*) echo "qo-kr/example"; exit 0 ;;
esac
exit 1
"""


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    stub = tmp_path / "stub"
    stub.mkdir()
    for name, body in (("codex", CODEX_STUB), ("gh", GH_STUB)):
        p = stub / name
        p.write_text(body)
        p.chmod(p.stat().st_mode | stat.S_IEXEC)

    for key in ("FAKE_MODEL", "FAKE_RC", "FAKE_TOUCH", "FAKE_BASE", "FAKE_PR_HEAD", "OQ_REVIEW_MODEL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("STUB_DIR", str(stub))
    monkeypatch.setenv("PATH", f"{stub}{os.pathsep}{os.environ['PATH']}")
    for key, value in {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
    }.items():
        monkeypatch.setenv(key, value)

    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True)
    _git(work, "remote", "add", "origin", str(origin))
    (work / "README.md").write_text("base\n")
    _git(work, "add", ".")
    _git(work, "commit", "-q", "-m", "base")
    _git(work, "push", "-q", "origin", "main")
    _git(work, "push", "-q", "origin", "main:dev")
    _git(work, "remote", "set-head", "origin", "main")
    _git(work, "checkout", "-q", "-b", "feature")
    feature = work / "specs" / "001-x"
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("spec\n")
    _git(work, "add", ".")
    _git(work, "commit", "-q", "-m", "feature")
    return work, stub


def _run(script: Path, cwd: Path, *args: str, **env: str) -> subprocess.CompletedProcess:
    full_env = dict(os.environ)
    full_env.update(env)
    return subprocess.run(
        ["bash", str(script), *args], cwd=cwd, capture_output=True, text=True, env=full_env
    )


def _ledger(work: Path) -> Path:
    return work / ".git" / "oq-reviews" / "ledger.tsv"


def _commit_docs(work: Path, *names: str) -> None:
    for name in names:
        (work / "specs" / "001-x" / name).write_text(f"{name}\n")
    _git(work, "add", ".")
    _git(work, "commit", "-q", "-m", "docs")


# ---------------------------------------------------------------- codex-review.sh


class TestCodexReview:
    def test_pins_model_uses_pr_base_and_records_sha(self, repo):
        work, stub = repo
        head = _git(work, "rev-parse", "HEAD")
        result = _run(REVIEW, work, FAKE_BASE="dev")

        assert result.returncode == 0, result.stderr
        args = (stub / "codex-args").read_text().splitlines()
        assert args[0] == "review"
        assert 'review_model="gpt-6.1-sol"' in args
        assert 'model="gpt-6.1-sol"' in args
        assert "--base" not in args, "codex 0.166 rejects --base together with a prompt"
        prompt = args[-1]
        assert f"git diff origin/dev...{head}" in prompt

        assert f"OQ_REVIEWED_SHA={head}" in result.stdout
        assert "OQ_REVIEW_BASE=origin/dev" in result.stdout
        line = _ledger(work).read_text().splitlines()[-1].split("\t")
        assert line[:3] == [head, "origin/dev", "gpt-6.1-sol"]

    def test_falls_back_to_origin_head_without_pr(self, repo):
        work, stub = repo
        result = _run(REVIEW, work)
        assert result.returncode == 0, result.stderr
        assert "OQ_REVIEW_BASE=origin/main" in result.stdout

    def test_explicit_base_wins_over_pr_base(self, repo):
        work, stub = repo
        result = _run(REVIEW, work, "--base", "main", FAKE_BASE="dev")
        assert result.returncode == 0, result.stderr
        assert "OQ_REVIEW_BASE=origin/main" in result.stdout

    def test_prompt_file_is_appended(self, repo, tmp_path):
        work, stub = repo
        focus = tmp_path / "focus.txt"
        focus.write_text("Focus on document consistency.\n")
        result = _run(REVIEW, work, "--prompt-file", str(focus))
        assert result.returncode == 0, result.stderr
        assert "Focus on document consistency." in (stub / "codex-args").read_text()

    @pytest.mark.parametrize("model", ["gpt-6-astra", "gpt-6.1-sol-ultrafast", "bad model"])
    def test_refuses_disallowed_models_before_calling_codex(self, repo, model):
        work, stub = repo
        result = _run(REVIEW, work, OQ_REVIEW_MODEL=model)
        assert result.returncode == 2
        assert not (stub / "codex-args").exists()
        assert not _ledger(work).exists()

    def test_banner_model_mismatch_fails_and_records_nothing(self, repo):
        work, stub = repo
        result = _run(REVIEW, work, FAKE_MODEL="gpt-6-astra")
        assert result.returncode == 4, result.stderr
        assert "gpt-6-astra" in result.stderr
        assert not _ledger(work).exists()

    def test_dirty_tree_is_refused_before_review(self, repo):
        work, stub = repo
        (work / "untracked.txt").write_text("x\n")
        result = _run(REVIEW, work)
        assert result.returncode == 3
        assert not (stub / "codex-args").exists()

    def test_review_that_dirties_tree_is_not_recorded(self, repo):
        work, stub = repo
        result = _run(REVIEW, work, FAKE_TOUCH=str(work / "touched.txt"))
        assert result.returncode == 3
        assert not _ledger(work).exists()

    def test_codex_failure_propagates_and_records_nothing(self, repo):
        work, stub = repo
        result = _run(REVIEW, work, FAKE_RC="7")
        assert result.returncode == 7
        assert not _ledger(work).exists()

    @pytest.mark.parametrize("base", ["-x", "a..b", "a b", "no-such-branch"])
    def test_bad_or_missing_base_is_refused(self, repo, base):
        work, stub = repo
        result = _run(REVIEW, work, "--base", base)
        assert result.returncode == 2
        assert not (stub / "codex-args").exists()


# ---------------------------------------------------------------- merge-gate.sh


class TestMergeGate:
    def _review(self, work: Path) -> str:
        result = _run(REVIEW, work)
        assert result.returncode == 0, result.stderr
        return _git(work, "rev-parse", "HEAD")

    def test_passes_when_everything_holds(self, repo):
        work, _ = repo
        _commit_docs(work, "VALUE.md", "POSTMORTEM.md")
        head = self._review(work)
        result = _run(GATE, work, "--pr", "12", "--feature-dir", "specs/001-x", FAKE_PR_HEAD=head)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "OQ_MERGE_GATE=PASS" in result.stdout
        assert (
            f"OQ_MERGE_COMMAND=gh pr merge 12 -R qo-kr/example --squash --match-head-commit {head}"
            in result.stdout
        )

    def test_missing_value_doc_fails(self, repo):
        work, _ = repo
        _commit_docs(work, "POSTMORTEM.md")
        head = self._review(work)
        result = _run(GATE, work, "--pr", "12", "--feature-dir", "specs/001-x", FAKE_PR_HEAD=head)
        assert result.returncode == 1
        assert "value-doc     FAIL" in result.stdout
        assert "OQ_MERGE_COMMAND" not in result.stdout

    def test_uncommitted_value_doc_does_not_count(self, repo):
        work, _ = repo
        _commit_docs(work, "POSTMORTEM.md")
        head = self._review(work)
        (work / "specs" / "001-x" / "VALUE.md").write_text("only on disk\n")
        result = _run(GATE, work, "--pr", "12", "--feature-dir", "specs/001-x", FAKE_PR_HEAD=head)
        assert result.returncode == 1
        assert "value-doc     FAIL" in result.stdout

    def test_commit_after_review_fails_reviewed_sha(self, repo):
        work, _ = repo
        _commit_docs(work, "VALUE.md", "POSTMORTEM.md")
        self._review(work)
        (work / "late.txt").write_text("late\n")
        _git(work, "add", ".")
        _git(work, "commit", "-q", "-m", "late commit")
        head = _git(work, "rev-parse", "HEAD")
        result = _run(GATE, work, "--pr", "12", "--feature-dir", "specs/001-x", FAKE_PR_HEAD=head)
        assert result.returncode == 1
        assert "reviewed-sha  FAIL" in result.stdout

    def test_pr_head_differs_from_local_fails(self, repo):
        work, _ = repo
        _commit_docs(work, "VALUE.md", "POSTMORTEM.md")
        self._review(work)
        result = _run(GATE, work, "--pr", "12", "--feature-dir", "specs/001-x", FAKE_PR_HEAD="0" * 40)
        assert result.returncode == 1
        assert "pr-head       FAIL" in result.stdout

    def test_unmeasured_is_not_a_pass(self, repo):
        work, _ = repo
        _commit_docs(work, "VALUE.md", "POSTMORTEM.md")
        head = self._review(work)
        result = _run(GATE, work, "--pr", "12", FAKE_PR_HEAD=head)
        assert result.returncode == 1
        assert "value-doc     UNMEASURED" in result.stdout
        assert "OQ_MERGE_GATE=FAIL" in result.stdout

    def test_unreadable_pr_is_unmeasured_not_pass(self, repo):
        work, _ = repo
        _commit_docs(work, "VALUE.md", "POSTMORTEM.md")
        self._review(work)
        result = _run(GATE, work, "--pr", "12", "--feature-dir", "specs/001-x")
        assert result.returncode == 1
        assert "pr-head       UNMEASURED" in result.stdout

    @pytest.mark.parametrize("args", [["--pr", "x"], ["--pr", "1", "--method", "force"], []])
    def test_bad_arguments(self, repo, args):
        work, _ = repo
        assert _run(GATE, work, *args).returncode == 2


# ---------------------------------------------------------------- command wiring


class TestCommandsUseScripts:
    COMMANDS = PROJECT_ROOT / "extensions" / "oq" / "commands"

    @pytest.mark.parametrize(
        "name", ["speckit.oq.auto-review.md", "speckit.oq.auto-review-strict.md"]
    )
    def test_review_commands_call_wrapper_not_codex_directly(self, name):
        text = (self.COMMANDS / name).read_text(encoding="utf-8")
        assert ".specify/extensions/oq/scripts/bash/codex-review.sh" in text
        assert "codex review --base" not in text

    def test_full_auto_requires_value_doc_and_merge_gate(self):
        text = (self.COMMANDS / "speckit.oq.full-auto.md").read_text(encoding="utf-8")
        assert "VALUE.md" in text
        assert ".specify/extensions/oq/scripts/bash/merge-gate.sh" in text
        assert "--match-head-commit" in text

    def test_scripts_are_installed_executable(self, tmp_path: Path):
        from specify_cli.extensions import ExtensionManager

        (tmp_path / ".specify").mkdir()
        manager = ExtensionManager(tmp_path)
        manager.install_from_directory(
            PROJECT_ROOT / "extensions" / "oq", "0.8.1", register_commands=False
        )
        for name in ("codex-review.sh", "merge-gate.sh"):
            installed = tmp_path / ".specify" / "extensions" / "oq" / "scripts" / "bash" / name
            assert installed.is_file(), installed
            assert os.access(installed, os.X_OK), f"{installed} is not executable"
