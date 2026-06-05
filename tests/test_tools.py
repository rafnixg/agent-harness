"""Tests for concrete tool implementations (primary)."""

import os
import sys
import tempfile

import pytest

from app.tools import BashTerminalTool, ReadFileTool, WriteFileTool, create_default_registry
from app.tools import ToolRegistry


# ---------------------------------------------------------------------------
# ReadFileTool
# ---------------------------------------------------------------------------

class TestReadFileTool:
    def setup_method(self):
        self.tool = ReadFileTool()

    def test_name(self):
        assert self.tool.name == "read_file"

    def test_description_is_non_empty(self):
        assert self.tool.description

    def test_parameters_schema_has_required_file_path(self):
        params = self.tool.parameters
        assert params["type"] == "object"
        assert "file_path" in params["properties"]
        assert "file_path" in params["required"]

    def test_reads_file_content(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("hello world")
            path = f.name
        try:
            assert self.tool.execute(file_path=path) == "hello world"
        finally:
            os.unlink(path)

    def test_reads_multiline_file(self):
        content = "line1\nline2\nline3"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            path = f.name
        try:
            assert self.tool.execute(file_path=path) == content
        finally:
            os.unlink(path)

    def test_raises_file_not_found_for_missing_path(self):
        with pytest.raises(FileNotFoundError, match="File not found"):
            self.tool.execute(file_path="/nonexistent/path/to/file.txt")

    def test_raises_file_not_found_for_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                self.tool.execute(file_path=tmpdir)


# ---------------------------------------------------------------------------
# WriteFileTool
# ---------------------------------------------------------------------------

class TestWriteFileTool:
    def setup_method(self):
        self.tool = WriteFileTool()

    def test_name(self):
        assert self.tool.name == "write_file"

    def test_description_is_non_empty(self):
        assert self.tool.description

    def test_parameters_schema_has_required_fields(self):
        params = self.tool.parameters
        assert "file_path" in params["required"]
        assert "content" in params["required"]

    def test_writes_content_to_existing_file(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            path = f.name
        try:
            result = self.tool.execute(file_path=path, content="written content")
            assert f"Successfully wrote to {path}" == result
            with open(path, encoding="utf-8") as fh:
                assert fh.read() == "written content"
        finally:
            os.unlink(path)

    def test_creates_new_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "newfile.txt")
            self.tool.execute(file_path=path, content="new")
            assert os.path.isfile(path)
            with open(path, encoding="utf-8") as fh:
                assert fh.read() == "new"

    def test_overwrites_existing_content(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("old content")
            path = f.name
        try:
            self.tool.execute(file_path=path, content="new content")
            with open(path, encoding="utf-8") as fh:
                assert fh.read() == "new content"
        finally:
            os.unlink(path)

    def test_return_message_contains_file_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "f.txt")
            result = self.tool.execute(file_path=path, content="")
            assert path in result

    def test_writes_empty_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "empty.txt")
            self.tool.execute(file_path=path, content="")
            with open(path, encoding="utf-8") as fh:
                assert fh.read() == ""


# ---------------------------------------------------------------------------
# BashTerminalTool
# ---------------------------------------------------------------------------

class TestBashTerminalTool:
    def setup_method(self):
        self.tool = BashTerminalTool()

    def test_name(self):
        assert self.tool.name == "bash_terminal"

    def test_description_is_non_empty(self):
        assert self.tool.description

    def test_parameters_schema_has_required_command(self):
        params = self.tool.parameters
        assert "command" in params["properties"]
        assert "command" in params["required"]

    @pytest.mark.skipif(sys.platform == "win32", reason="echo behaves differently on Windows shells")
    def test_executes_echo_command(self):
        result = self.tool.execute(command="echo hello")
        assert "hello" in result

    def test_returns_error_string_on_non_zero_exit(self):
        result = self.tool.execute(command="exit 1")
        # Should return an error message string, not raise
        assert isinstance(result, str)

    def test_captures_stdout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("captured")
            result = self.tool.execute(command=f"cat {path}")
            assert "captured" in result


# ---------------------------------------------------------------------------
# create_default_registry
# ---------------------------------------------------------------------------

class TestCreateDefaultRegistry:
    def setup_method(self):
        self.registry = create_default_registry()

    def test_returns_tool_registry(self):
        assert isinstance(self.registry, ToolRegistry)

    def test_contains_three_tools(self):
        assert len(self.registry) == 3

    def test_contains_read_file_tool(self):
        tool = self.registry.get("read_file")
        assert isinstance(tool, ReadFileTool)

    def test_contains_write_file_tool(self):
        tool = self.registry.get("write_file")
        assert isinstance(tool, WriteFileTool)

    def test_contains_bash_terminal_tool(self):
        tool = self.registry.get("bash_terminal")
        assert isinstance(tool, BashTerminalTool)

    def test_tools_are_functional(self):
        """Smoke-test: registry tools can produce OpenAI schemas."""
        schemas = self.registry.to_openai_schema()
        names = {s["function"]["name"] for s in schemas}
        assert names == {"read_file", "write_file", "bash_terminal"}
