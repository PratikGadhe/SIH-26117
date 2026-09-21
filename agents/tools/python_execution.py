"""
Tool 4: Controlled Python Execution for VYASA.
Prototype execution boundary for safe mathematical calculations and data transformations.
Employs AST pre-execution validation, restricted builtins, strict module allowlisting,
timeout bounding, and stdout capture.

LIMITATION NOTE:
This is a prototype restricted in-process execution boundary designed for safe calculations.
It is not an operating-system-level microVM or container isolation sandbox.
"""

from __future__ import annotations

import ast
from contextlib import redirect_stdout
import datetime
import io
import json
import math
import os
import random
import re
import statistics
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Set

current_dir = os.path.dirname(os.path.abspath(__file__))
agents_root = os.path.abspath(os.path.join(current_dir, ".."))
if agents_root not in sys.path:
    sys.path.insert(0, agents_root)

from tools.base import BaseTool, ToolResult

DEFAULT_TIMEOUT_SECONDS = 5.0
MAX_OUTPUT_CHARS = 10_000

# Modules explicitly permitted for import in safe calculations
ALLOWED_MODULES: Set[str] = {
    "math",
    "statistics",
    "datetime",
    "time",
    "json",
    "random",
    "re",
    "collections",
    "itertools",
    "numpy",
}

# Modules explicitly banned (any import attempt is immediately rejected)
BLOCKED_MODULES: Set[str] = {
    "os",
    "sys",
    "subprocess",
    "shutil",
    "socket",
    "urllib",
    "requests",
    "http",
    "builtins",
    "posix",
    "pty",
    "platform",
    "ctypes",
    "threading",
    "multiprocessing",
    "signal",
    "inspect",
    "importlib",
    "pickle",
    "asyncio",
}

# Dangerous builtin function names that must never be called or accessed
BLOCKED_BUILTIN_NAMES: Set[str] = {
    "eval",
    "exec",
    "open",
    "__import__",
    "globals",
    "locals",
    "getattr",
    "setattr",
    "delattr",
    "compile",
    "breakpoint",
    "input",
    "help",
    "quit",
    "exit",
}

# Dangerous attribute names (dunder escapes)
BLOCKED_ATTRIBUTES: Set[str] = {
    "__class__",
    "__subclasses__",
    "__bases__",
    "__globals__",
    "__code__",
    "__mro__",
    "__dict__",
    "__builtins__",
}


class SecurityCheckVisitor(ast.NodeVisitor):
    """
    Validates the AST of submitted Python code to block dangerous operations
    before execution begins.
    """

    def __init__(self) -> None:
        self.violations: List[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root_module = alias.name.split(".")[0]
            if root_module in BLOCKED_MODULES or root_module not in ALLOWED_MODULES:
                self.violations.append(
                    f"Importing module '{alias.name}' is prohibited for security reasons."
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        root_module = module.split(".")[0]
        if root_module in BLOCKED_MODULES or root_module not in ALLOWED_MODULES:
            self.violations.append(
                f"Importing from module '{module}' is prohibited for security reasons."
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check direct call to blocked functions like open(), eval(), exec()
        if isinstance(node.func, ast.Name):
            if node.func.id in BLOCKED_BUILTIN_NAMES:
                self.violations.append(
                    f"Calling function '{node.func.id}()' is prohibited for security reasons."
                )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Check access to dangerous dunder attributes
        if node.attr in BLOCKED_ATTRIBUTES:
            self.violations.append(
                f"Accessing restricted attribute '{node.attr}' is prohibited."
            )
        self.generic_visit(node)


def build_safe_builtins() -> Dict[str, Any]:
    """
    Construct a restricted builtins dictionary without file I/O or meta-programming.
    """

    def safe_import(name: str, *args: Any, **kwargs: Any) -> Any:
        root = name.split(".")[0]
        if root in ALLOWED_MODULES:
            return __import__(name, *args, **kwargs)
        raise ImportError(
            f"Importing module '{name}' is not allowed in safe execution environment."
        )

    return {
        "abs": abs,
        "all": all,
        "any": any,
        "bin": bin,
        "bool": bool,
        "chr": chr,
        "dict": dict,
        "divmod": divmod,
        "enumerate": enumerate,
        "filter": filter,
        "float": float,
        "format": format,
        "frozenset": frozenset,
        "hex": hex,
        "int": int,
        "isinstance": isinstance,
        "issubclass": issubclass,
        "iter": iter,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "next": next,
        "oct": oct,
        "ord": ord,
        "pow": pow,
        "print": print,
        "range": range,
        "reversed": reversed,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "zip": zip,
        "True": True,
        "False": False,
        "None": None,
        "__import__": safe_import,
    }


def build_safe_globals() -> Dict[str, Any]:
    """
    Construct safe execution globals with pre-imported utility libraries.
    """
    safe_globals: Dict[str, Any] = {
        "__builtins__": build_safe_builtins(),
        "math": math,
        "statistics": statistics,
        "datetime": datetime,
        "time": time,
        "json": json,
        "random": random,
        "re": re,
    }
    try:
        import numpy as np

        safe_globals["np"] = np
        safe_globals["numpy"] = np
    except ImportError:
        pass
    return safe_globals


class PythonExecutionTool(BaseTool):
    """
    Approved tool for controlled, safe local Python calculation scripts.
    """

    name = "python_execute"
    description = (
        "Execute a safe, isolated Python calculation or data-processing snippet. "
        "Strictly restricted: no OS/shell commands, no network requests, no file system access. "
        "Permits math, statistics, datetime, json, re, and numpy."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Valid Python code to execute (e.g. calculation script).",
            },
            "timeout_seconds": {
                "type": "number",
                "description": f"Maximum execution timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS}s, max: 10s).",
                "default": DEFAULT_TIMEOUT_SECONDS,
            },
        },
        "required": ["code"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        raw_code = kwargs.get("code")
        if not raw_code or not isinstance(raw_code, str) or not raw_code.strip():
            return ToolResult.failure_result(
                self.name,
                "EMPTY_CODE",
                "Parameter 'code' is required and must be a non-empty string.",
            )

        code_str = raw_code.strip()
        timeout = float(kwargs.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS))
        if timeout <= 0 or timeout > 10.0:
            timeout = DEFAULT_TIMEOUT_SECONDS

        # 1. AST syntax parsing and security validation
        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            return ToolResult.failure_result(
                self.name,
                "SYNTAX_ERROR",
                f"Syntax error at line {e.lineno}: {e.msg}",
            )

        visitor = SecurityCheckVisitor()
        visitor.visit(tree)
        if visitor.violations:
            return ToolResult.failure_result(
                self.name,
                "SECURITY_VIOLATION",
                "Code contains prohibited operations: " + "; ".join(visitor.violations),
            )

        # 2. Compile AST to bytecode
        try:
            compiled_code = compile(tree, filename="<restricted_snippet>", mode="exec")
        except Exception as e:
            return ToolResult.failure_result(
                self.name,
                "COMPILATION_ERROR",
                f"Failed to compile snippet: {str(e)}",
            )

        # 3. Thread-based timeout execution with stdout capture
        stdout_buffer = io.StringIO()
        exec_globals = build_safe_globals()
        exec_locals: Dict[str, Any] = {}

        execution_error: List[Exception] = []
        start_time = time.time()

        def runner() -> None:
            try:
                with redirect_stdout(stdout_buffer):
                    exec(compiled_code, exec_globals, exec_locals)
            except Exception as e:
                execution_error.append(e)

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        elapsed = round(time.time() - start_time, 4)

        if thread.is_alive():
            return ToolResult.failure_result(
                self.name,
                "TIMEOUT",
                f"Execution timed out after {timeout:.1f} seconds. Infinite loops or intensive operations are halted.",
                metadata={"timeout_seconds": timeout, "elapsed_seconds": elapsed},
            )

        if execution_error:
            err = execution_error[0]
            return ToolResult.failure_result(
                self.name,
                "RUNTIME_ERROR",
                f"Runtime exception ({type(err).__name__}): {str(err)}",
                metadata={"elapsed_seconds": elapsed},
            )

        output = stdout_buffer.getvalue()
        truncated = False
        if len(output) > MAX_OUTPUT_CHARS:
            output = (
                output[:MAX_OUTPUT_CHARS]
                + f"\n[Output truncated at {MAX_OUTPUT_CHARS} characters]"
            )
            truncated = True

        # Extract meaningful scalar or serializable results from locals
        clean_locals = {}
        for k, v in exec_locals.items():
            if k.startswith("_"):
                continue
            if isinstance(v, (int, float, str, bool, list, dict, tuple, set)):
                clean_locals[k] = v

        return ToolResult.success_result(
            self.name,
            result={
                "stdout": output.strip() if output else "(No output printed)",
                "variables": clean_locals,
                "execution_time_seconds": elapsed,
            },
            metadata={
                "truncated": truncated,
                "sandbox_level": "in_process_ast_restricted_boundary",
            },
        )
