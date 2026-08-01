"""Config value object and its file store."""

import json
import os
import stat

import pytest

from zsp.core import AuthError, Config, ConfigStore, UsageError


class TestConfig:
    def test_round_trips_through_a_dict(self, config):
        assert Config.from_dict(config.to_dict()).to_dict() == config.to_dict()

    def test_ignores_unknown_keys(self):
        restored = Config.from_dict({
            "client_id": "a", "client_secret": "b", "refresh_token": "c",
            "dc": "in", "unexpected": "ignored",
        })
        assert restored.client_id == "a"
        assert not hasattr(restored, "unexpected")

    def test_redacts_every_secret(self, config):
        redacted = config.redacted()
        assert redacted["client_secret"] == "***redacted***"
        assert redacted["refresh_token"] == "***redacted***"
        assert redacted["access_token"] == "***redacted***"
        # Non-secret fields survive so the output stays useful.
        assert redacted["client_id"] == config.client_id
        assert redacted["dc"] == "in"

    def test_redaction_leaves_empty_secrets_alone(self):
        config = Config("id", "", "", "in")
        assert config.redacted()["client_secret"] == ""

    def test_repr_hides_secrets(self, config):
        assert "testsecret" not in repr(config)


class TestResolve:
    def test_explicit_values_win(self, config):
        config.default_project = "saved"
        assert config.resolve("passed", "sprint") == ("passed", "sprint")

    def test_falls_back_to_defaults(self, config):
        config.default_project = "p1"
        config.default_sprint = "s1"
        assert config.resolve() == ("p1", "s1")

    def test_missing_project_names_the_fix(self, config):
        with pytest.raises(UsageError) as caught:
            config.resolve()
        assert "zsp use" in str(caught.value)
        assert caught.value.exit_code == 2

    def test_missing_sprint_is_reported(self, config):
        config.default_project = "p1"
        with pytest.raises(UsageError):
            config.resolve()

    def test_sprint_can_be_optional(self, config):
        config.default_project = "p1"
        assert config.resolve(need_sprint=False) == ("p1", None)


class TestConfigStore:
    def test_load_without_a_file_raises(self, tmp_path):
        with pytest.raises(AuthError) as caught:
            ConfigStore(str(tmp_path)).load()
        assert "zsp login" in str(caught.value)
        assert caught.value.exit_code == 3

    def test_save_then_load(self, tmp_path, config):
        store = ConfigStore(str(tmp_path))
        store.save(config)
        assert store.load().client_id == config.client_id

    def test_saved_file_is_owner_only(self, tmp_path, config):
        """Credentials must never be group- or world-readable."""
        store = ConfigStore(str(tmp_path))
        store.save(config)
        mode = stat.S_IMODE(os.stat(store.path).st_mode)
        assert mode == 0o600

    def test_save_creates_the_directory(self, tmp_path, config):
        store = ConfigStore(str(tmp_path / "nested" / "deeper"))
        store.save(config)
        assert os.path.exists(store.path)

    def test_delete_reports_whether_anything_went(self, tmp_path, config):
        store = ConfigStore(str(tmp_path))
        assert store.delete() is False
        store.save(config)
        assert store.delete() is True
        assert not store.exists()

    def test_set_defaults_persists(self, tmp_path, config):
        store = ConfigStore(str(tmp_path))
        store.save(config)
        store.set_defaults("proj", "spr")

        reloaded = store.load()
        assert reloaded.default_project == "proj"
        assert reloaded.default_sprint == "spr"

    def test_set_defaults_keeps_sprint_when_omitted(self, tmp_path, config):
        store = ConfigStore(str(tmp_path))
        config.default_sprint = "existing"
        store.save(config)
        store.set_defaults("newproj")
        assert store.load().default_sprint == "existing"

    def test_honours_the_environment_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZSP_CONFIG_DIR", str(tmp_path))
        assert ConfigStore().directory == str(tmp_path)

    def test_written_file_is_valid_json(self, tmp_path, config):
        store = ConfigStore(str(tmp_path))
        store.save(config)
        with open(store.path) as handle:
            assert json.load(handle)["dc"] == "in"
