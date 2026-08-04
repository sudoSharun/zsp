"""Parser construction, dispatch and exit codes."""

import pytest

from zsp.cli import Application
from zsp.cli.commands import COMMANDS
from zsp.core import ApiError, AuthError, UsageError, ZspError


class TestParser:
    def test_every_command_is_registered(self, interface):
        parser = interface.build_parser()
        choices = parser._subparsers._group_actions[0].choices
        assert set(choices) == {command.name for command in COMMANDS}

    def test_command_names_are_unique(self):
        names = [command.name for command in COMMANDS]
        assert len(names) == len(set(names))

    def test_every_command_declares_help(self):
        assert all(command.help for command in COMMANDS)

    def test_version_flag_exits_cleanly(self, interface):
        with pytest.raises(SystemExit) as caught:
            interface.run(["--version"])
        assert caught.value.code == 0

    def test_missing_subcommand_is_a_usage_error(self, interface):
        with pytest.raises(SystemExit) as caught:
            interface.run([])
        assert caught.value.code == 2

    def test_writes_expose_dry_run(self, interface):
        parser = interface.build_parser()
        choices = parser._subparsers._group_actions[0].choices
        for command in COMMANDS:
            if command.writes:
                options = {a.dest for a in choices[command.name]._actions}
                assert "dry_run" in options, command.name

    def test_scoped_commands_expose_project(self, interface):
        parser = interface.build_parser()
        choices = parser._subparsers._group_actions[0].choices
        for command in COMMANDS:
            if command.scoped:
                options = {a.dest for a in choices[command.name]._actions}
                assert "project" in options, command.name
                assert ("sprint" in options) is command.needs_sprint, command.name


class TestExitCodes:
    """Distinct codes let scripts tell auth problems from usage mistakes."""

    @pytest.mark.parametrize("error,expected", [
        (UsageError("bad flags"), 2),
        (AuthError("not logged in"), 3),
        (ApiError(500, "{}"), 4),
        (ZspError("generic"), 1),
    ])
    def test_errors_map_to_their_code(self, interface, monkeypatch, capsys,
                                      error, expected):
        monkeypatch.setattr(
            "zsp.cli.commands.read.TeamsCommand.execute",
            lambda self, args: (_ for _ in ()).throw(error))

        assert interface.run(["teams"]) == expected
        assert "error:" in capsys.readouterr().err

    def test_success_returns_zero(self, interface, opener):
        from ..conftest import TEAMS_RESPONSE

        opener.payloads.append(TEAMS_RESPONSE)
        assert interface.run(["teams"]) == 0

    def test_keyboard_interrupt_returns_130(self, interface, monkeypatch, capsys):
        monkeypatch.setattr(
            "zsp.cli.commands.read.TeamsCommand.execute",
            lambda self, args: (_ for _ in ()).throw(KeyboardInterrupt()))

        assert interface.run(["teams"]) == 130
        assert "aborted" in capsys.readouterr().err


class TestJsonFlag:
    def test_json_switches_the_renderer(self, interface, opener):
        from ..conftest import TEAMS_RESPONSE

        opener.payloads.append(TEAMS_RESPONSE)
        interface.run(["teams", "--json"])
        assert interface.application.renderer.as_json is True

    def test_default_renderer_is_human(self, interface, opener):
        from ..conftest import TEAMS_RESPONSE

        opener.payloads.append(TEAMS_RESPONSE)
        interface.run(["teams"])
        assert interface.application.renderer.as_json is False


class TestApplicationWiring:
    def test_services_are_built_once(self, application):
        assert application.items is application.items

    def test_item_and_timesheet_share_a_lookup_service(self, application):
        assert application.items.lookups is application.timesheets.lookups

    def test_services_share_one_client(self, application):
        assert application.items.client is application.comments.client

    def test_config_is_loaded_lazily(self, tmp_path):
        from zsp.core import ConfigStore

        # Nothing on disk: constructing must not raise, only using it should.
        app = Application(store=ConfigStore(str(tmp_path)))
        with pytest.raises(AuthError):
            _ = app.config


class TestHelpText:
    """Help is the only documentation an agent reads. Keep it correct."""

    def top_level(self, interface):
        return interface.build_parser().format_help()

    def test_top_level_explains_ids_versus_names(self, interface):
        """The single most common mistake: passing a name to --project."""
        text = self.top_level(interface)
        assert "--project and --sprint take numeric ids" in text
        assert "--status, --assignee, --type and --priority take human names" in text

    def test_top_level_points_at_value_discovery(self, interface):
        text = self.top_level(interface)
        assert "zsp statuses" in text
        assert "zsp use" in text

    def test_top_level_advertises_dry_run_and_json(self, interface):
        text = self.top_level(interface)
        assert "--dry-run" in text
        assert "--json" in text

    def test_top_level_documents_exit_codes(self, interface):
        """Scripts branch on these; they must be discoverable."""
        assert "Exit codes" in self.top_level(interface)

    def test_top_level_states_what_is_unsupported(self, interface):
        """Stops an agent hunting for a command that cannot exist."""
        assert "not supported" in self.top_level(interface)

    def test_every_command_has_a_description(self):
        missing = [c.name for c in COMMANDS if not (c.description or c.help)]
        assert missing == []

    def test_commands_needing_lookups_carry_examples(self):
        """Anything taking a name or an id needs a worked example."""
        needs = {"create", "update", "log", "comment", "attach", "detach",
                 "rm", "items", "statuses", "standup", "use"}
        missing = [c.name for c in COMMANDS if c.name in needs and not c.examples]
        assert missing == []

    def test_examples_survive_formatting(self, interface):
        """RawDescriptionHelpFormatter keeps line breaks; the default
        formatter would reflow examples into an unreadable paragraph."""
        parser = interface.build_parser()
        create = parser._subparsers._group_actions[0].choices["create"]
        text = create.format_help()

        assert "zsp create --title" in text
        assert text.count("\n") > 15

    def test_rm_help_explains_the_role_restriction(self, interface):
        parser = interface.build_parser()
        text = parser._subparsers._group_actions[0].choices["rm"].format_help()
        assert "7401.14" in text

    def test_attach_help_states_the_item_level_limitation(self, interface):
        parser = interface.build_parser()
        text = parser._subparsers._group_actions[0].choices["attach"].format_help()
        assert "item-level" in text
