"""Tests for command dispatcher."""

import pytest
from src.console.command_dispatcher import CommandDispatcher


def test_dispatcher_initialization():
    """Test dispatcher initializes with builtin commands."""
    dispatcher = CommandDispatcher()
    commands = dispatcher.list_commands()

    assert "help" in commands
    assert "spec" in commands
    assert "plan" in commands
    assert "execute" in commands
    assert "validate" in commands
    assert "test" in commands
    assert "exit" in commands


def test_parse_command_simple():
    """Test simple command parsing."""
    dispatcher = CommandDispatcher()

    cmd, args, options = dispatcher.parse_command("run task_name")
    assert cmd == "run"
    assert args == ["task_name"]
    assert options == {}


def test_parse_command_with_options():
    """Test command parsing with options."""
    dispatcher = CommandDispatcher()

    cmd, args, options = dispatcher.parse_command("run --focus security --depth deep task")
    assert cmd == "run"
    assert "task" in args
    assert options["focus"] == "security"
    assert options["depth"] == "deep"


def test_parse_command_with_leading_slash():
    """Test command parsing with leading slash."""
    dispatcher = CommandDispatcher()

    cmd, args, options = dispatcher.parse_command("/run task_name")
    assert cmd == "run"


def test_alias_resolution():
    """Test command alias resolution."""
    dispatcher = CommandDispatcher()

    cmd, args, options = dispatcher.parse_command("q")
    assert cmd == "exit"

    cmd, args, options = dispatcher.parse_command("h")
    assert cmd == "help"


def test_execute_help_command():
    """Test executing help command."""
    dispatcher = CommandDispatcher()

    result = dispatcher.execute("help")
    assert result.success is True
    assert "spec" in result.output or "plan" in result.output
    assert "Available commands" in result.output


def test_execute_unknown_command():
    """Test executing unknown command."""
    dispatcher = CommandDispatcher()

    result = dispatcher.execute("unknown_command")
    assert result.success is False
    assert "Unknown command" in result.error


def test_execute_spec_command():
    """Test executing spec command."""
    dispatcher = CommandDispatcher()

    result = dispatcher.execute("/spec build a REST API")
    assert result.success is True
    assert "REST API" in result.output


def test_execute_plan_command():
    """Test executing plan command."""
    dispatcher = CommandDispatcher()

    result = dispatcher.execute("/plan show")
    assert result.success is True
    assert "masterplan" in result.output.lower()


def test_execute_plan_invalid_action():
    """Test plan command with invalid action."""
    dispatcher = CommandDispatcher()

    result = dispatcher.execute("/plan invalid_action")
    assert result.success is False
    assert "Invalid plan action" in result.error
