"""Tests for the bundled OQ workflow extension (extensions/oq/)."""

import os
from pathlib import Path

from typer.testing import CliRunner

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
EXT_DIR = PROJECT_ROOT / "extensions" / "oq"


class TestOqExtensionManifest:
    def test_manifest_validates(self):
        from specify_cli.extensions import ExtensionManifest

        manifest = ExtensionManifest(EXT_DIR / "extension.yml")
        assert manifest.id == "oq"
        assert manifest.version == "1.0.0"

    def test_manifest_declares_expected_commands_and_aliases(self):
        from specify_cli.extensions import ExtensionManifest

        manifest = ExtensionManifest(EXT_DIR / "extension.yml")
        commands = {command["name"]: command.get("aliases", []) for command in manifest.commands}

        assert commands["speckit.oq.prepare"] == ["speckit.prepare"]
        assert commands["speckit.oq.collab-review"] == ["speckit.collab-review"]
        assert commands["speckit.oq.auto-review"] == ["speckit.auto-review"]
        assert commands["speckit.oq.auto-review-strict"] == ["speckit.auto-review-strict"]
        assert commands["speckit.oq.doc-review"] == ["speckit.doc-review"]
        assert commands["speckit.oq.full-auto"] == ["speckit.full-auto"]

    def test_manifest_command_files_exist(self):
        from specify_cli.extensions import ExtensionManifest

        manifest = ExtensionManifest(EXT_DIR / "extension.yml")
        for command in manifest.commands:
            assert (EXT_DIR / command["file"]).is_file(), command["file"]


class TestOqExtensionInstall:
    def test_install_from_directory(self, tmp_path: Path):
        from specify_cli.extensions import ExtensionManager

        (tmp_path / ".specify").mkdir()
        manager = ExtensionManager(tmp_path)
        manifest = manager.install_from_directory(EXT_DIR, "0.8.1", register_commands=False)

        assert manifest.id == "oq"
        assert manager.registry.is_installed("oq")

    def test_bundled_extension_locator(self):
        from specify_cli import _locate_bundled_extension

        path = _locate_bundled_extension("oq")
        assert path is not None
        assert (path / "extension.yml").is_file()

    def test_cli_install_registers_alias_skills_for_codex(self, tmp_path: Path):
        from specify_cli import app

        project = tmp_path / "oq-ext"
        project.mkdir()

        runner = CliRunner()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            init_result = runner.invoke(
                app,
                [
                    "init",
                    "--here",
                    "--integration",
                    "codex",
                    "--script",
                    "sh",
                    "--no-git",
                    "--ignore-agent-tools",
                ],
                catch_exceptions=False,
            )
            assert init_result.exit_code == 0, init_result.output

            add_result = runner.invoke(
                app,
                ["extension", "add", "oq"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert add_result.exit_code == 0, add_result.output

        skills_dir = project / ".agents" / "skills"
        assert (skills_dir / "speckit-oq-prepare" / "SKILL.md").is_file()
        assert (skills_dir / "speckit-prepare" / "SKILL.md").is_file()
        assert (skills_dir / "speckit-oq-full-auto" / "SKILL.md").is_file()
        assert (skills_dir / "speckit-full-auto" / "SKILL.md").is_file()
