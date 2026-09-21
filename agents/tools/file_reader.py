"""
Tool 2: Safe File Reader for VYASA.
Enforces strict workspace path boundaries, anti-traversal validation,
file size ceilings, and safe parsing for TXT, CSV, JSON, PDF, and DOCX formats.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Dict, List, Optional, Set, Tuple

current_dir = os.path.dirname(os.path.abspath(__file__))
agents_root = os.path.abspath(os.path.join(current_dir, ".."))
if agents_root not in sys.path:
    sys.path.insert(0, agents_root)

from tools.base import BaseTool, ToolResult

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_RETURN_CHARS = 50_000

ALLOWED_EXTENSIONS: Set[str] = {".txt", ".csv", ".json", ".pdf", ".docx"}
FORBIDDEN_EXTENSIONS: Set[str] = {
    ".key",
    ".pem",
    ".id_rsa",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".pyc",
    ".sh",
    ".bash",
    ".zsh",
    ".exe",
    ".bin",
}
FORBIDDEN_NAMES: Set[str] = {".env", "cognivault.db", "id_rsa", "id_dsa"}
FORBIDDEN_SUBSTRINGS: Tuple[str, ...] = (
    "/.git/",
    "/venv/",
    "/.venv/",
    "/node_modules/",
    "/__pycache__/",
)


def get_approved_workspace_roots() -> List[Path]:
    """
    Return the set of approved canonical filesystem root directories.
    """
    repo_root = Path(__file__).resolve().parents[2]
    temp_dir = Path(tempfile.gettempdir()).resolve()
    return [repo_root, temp_dir]


def validate_and_resolve_path(raw_path: str) -> Tuple[Optional[Path], Optional[str]]:
    """
    Canonicalize and validate target file path against security restrictions.
    Returns (canonical_path, error_message).
    """
    if not raw_path or not isinstance(raw_path, str) or not raw_path.strip():
        return None, "File path must be a non-empty string."

    stripped = raw_path.strip()

    # Reject obvious traversal attempts upfront
    if "../" in stripped or "..\\" in stripped:
        # Check if it attempts to navigate out
        pass  # Will be caught by resolve and root check

    repo_root = Path(__file__).resolve().parents[2]
    candidate = Path(stripped)

    # If relative, anchor to repository root
    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()
    else:
        candidate = candidate.resolve()

    # 1. Check if inside approved roots
    approved_roots = get_approved_workspace_roots()
    is_contained = any(
        candidate == root or root in candidate.parents for root in approved_roots
    )
    if not is_contained:
        return (
            None,
            f"Access denied: path '{raw_path}' is outside the authorized workspace.",
        )

    # 2. Check forbidden file names
    if candidate.name.lower() in FORBIDDEN_NAMES or candidate.name.startswith(".env"):
        return (
            None,
            f"Access denied: file '{candidate.name}' is confidential or restricted.",
        )

    # 3. Check forbidden substrings (e.g. .git, venv, node_modules)
    norm_str = str(candidate).replace("\\", "/") + "/"
    for sub in FORBIDDEN_SUBSTRINGS:
        if sub in norm_str:
            return (
                None,
                f"Access denied: accessing internal directory '{sub.strip('/')}' is prohibited.",
            )

    # 4. Check extension
    ext = candidate.suffix.lower()
    if ext in FORBIDDEN_EXTENSIONS:
        return None, f"Access denied: file extension '{ext}' is prohibited."

    if ext not in ALLOWED_EXTENSIONS:
        return None, (
            f"Unsupported file format '{ext}'. "
            f"Allowed formats are: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    # 5. Check existence and file type
    if not candidate.exists():
        return None, f"File not found: '{raw_path}'."
    if not candidate.is_file():
        return None, f"Path is not a regular file: '{raw_path}'."

    # 6. Check file size
    try:
        size = candidate.stat().st_size
        if size > MAX_FILE_SIZE_BYTES:
            return None, (
                f"File size ({size / (1024 * 1024):.2f} MB) exceeds maximum "
                f"allowed limit of {MAX_FILE_SIZE_BYTES / (1024 * 1024):.0f} MB."
            )
    except OSError as e:
        return None, f"Could not inspect file attributes: {str(e)}"

    return candidate, None


class FileReaderTool(BaseTool):
    """
    Approved safe file-reading tool for supported document formats.
    """

    name = "file_reader"
    description = (
        "Safely read the content of an authorized file in the workspace. "
        "Supports TXT, CSV, JSON, PDF, and DOCX documents with strict security boundaries."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Relative or absolute path to the target workspace file.",
            },
        },
        "required": ["file_path"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        file_path_arg = kwargs.get("file_path")
        canonical_path, error = validate_and_resolve_path(str(file_path_arg or ""))
        if error or canonical_path is None:
            return ToolResult.failure_result(
                self.name,
                "SECURITY_VIOLATION"
                if "Access denied" in (error or "")
                else "INVALID_FILE",
                error or "Invalid file path",
                metadata={"file_path": str(file_path_arg)},
            )

        suffix = canonical_path.suffix.lower()
        size_bytes = canonical_path.stat().st_size

        try:
            if suffix == ".txt":
                content = canonical_path.read_text(encoding="utf-8", errors="replace")
                metadata = {"lines": len(content.splitlines())}

            elif suffix == ".csv":
                raw = canonical_path.read_text(encoding="utf-8", errors="replace")
                lines = [line for line in raw.splitlines() if line.strip()]
                header = lines[0] if lines else ""
                content = raw
                metadata = {
                    "row_count": max(0, len(lines) - 1),
                    "header": header,
                }

            elif suffix == ".json":
                raw = canonical_path.read_text(encoding="utf-8", errors="replace")
                parsed = json.loads(raw)
                content = json.dumps(parsed, indent=2)
                metadata = {"is_json_valid": True}

            elif suffix == ".pdf":
                content, metadata = self._read_pdf(canonical_path)

            elif suffix == ".docx":
                content, metadata = self._read_docx(canonical_path)

            else:
                return ToolResult.failure_result(
                    self.name,
                    "UNSUPPORTED_FORMAT",
                    f"Unsupported file format: {suffix}",
                )

            # Cap content size if too large
            truncated = False
            if len(content) > MAX_RETURN_CHARS:
                content = (
                    content[:MAX_RETURN_CHARS]
                    + f"\n\n[Content truncated: displayed first {MAX_RETURN_CHARS} characters of {len(content)} total]"
                )
                truncated = True

            metadata.update(
                {
                    "truncated": truncated,
                    "file_size_bytes": size_bytes,
                    "relative_path": str(canonical_path.name),
                }
            )

            return ToolResult.success_result(
                self.name,
                result={
                    "filename": canonical_path.name,
                    "file_type": suffix.lstrip("."),
                    "content": content,
                    "metadata": metadata,
                },
                metadata={"resolved_path": str(canonical_path)},
            )

        except json.JSONDecodeError as e:
            return ToolResult.failure_result(
                self.name,
                "MALFORMED_JSON",
                f"File contains invalid JSON syntax: {str(e)}",
            )
        except Exception as e:
            return ToolResult.failure_result(
                self.name,
                "READ_ERROR",
                f"Error reading file '{canonical_path.name}': {str(e)}",
            )

    def _read_pdf(self, path: Path) -> Tuple[str, Dict[str, Any]]:
        try:
            import fitz

            doc = fitz.open(str(path))
            pages_text = []
            for i, page in enumerate(doc):
                text = page.get_text().strip()
                if text:
                    pages_text.append(f"--- Page {i + 1} ---\n{text}")
            page_count = len(doc)
            doc.close()
            full_text = (
                "\n\n".join(pages_text)
                if pages_text
                else "No extractable text found in PDF."
            )
            return full_text, {"page_count": page_count}
        except ImportError:
            return "PyMuPDF not installed for PDF reading.", {"page_count": 0}

    def _read_docx(self, path: Path) -> Tuple[str, Dict[str, Any]]:
        try:
            import docx2txt

            text = docx2txt.process(str(path))
            return text.strip() or "Empty DOCX document.", {"format": "docx"}
        except ImportError:
            return "docx2txt not installed for DOCX reading.", {"format": "docx"}
