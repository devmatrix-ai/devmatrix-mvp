"""Tests for command dispatcher."""

import pytest
from src.console.command_dispatcher import CommandDispatcher


def test_dispatcher_initialization():
    """Test dispatcher initializes with builtin commands."""
    dispatcher = CommandDispatcher()
    commands = dispatcher.list_commands()

    assert "help" in commands
    assert "run" in commands
    assert "plan" in commands
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
    assert "run" in result.output
    assert "Available commands" in result.output


def test_execute_unknown_command():
    """Test executing unknown command."""
    dispatcher = CommandDispatcher()

    result = dispatcher.execute("unknown_command")
    assert result.success is False
    assert "Unknown command" in result.error


def test_execute_run_command():
    """Test executing run command."""
    dispatcher = CommandDispatcher()

    result = dispatcher.execute("/run my_task")
    assert result.success is True
    assert "my_task" in result.output


def test_execute_plan_command():
    """Test executing plan command."""
    dispatcher = CommandDispatcher()

    result = dispatcher.execute("/plan feature")
    assert result.success is True


def test_execute_plan_invalid_type():
    """Test plan command with invalid type."""
    dispatcher = CommandDispatcher()

    result = dispatcher.execute("/plan invalid_type")
    assert result.success is False
    assert "Invalid plan type" in result.error
