"""
Tool 3: Structured Data Analysis for VYASA.
Performs deterministic tabular operations on CSV files within the authorized workspace.
Supports column inspection, row counting, missing-value profiling, numeric summaries,
filtering, sorting/top-k, and categorical grouping/aggregation without executing arbitrary code.
"""

from __future__ import annotations

import csv
import math
import os
from pathlib import Path
import statistics
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

current_dir = os.path.dirname(os.path.abspath(__file__))
agents_root = os.path.abspath(os.path.join(current_dir, ".."))
if agents_root not in sys.path:
    sys.path.insert(0, agents_root)

from tools.base import BaseTool, ToolResult
from tools.file_reader import validate_and_resolve_path

MAX_ROWS_LIMIT = 100_000
MAX_RETURN_ROWS = 50


class DataAnalysisTool(BaseTool):
    """
    Approved tool for structured tabular data analysis on CSV files.
    """

    name = "data_analysis"
    description = (
        "Analyze structured tabular data from a CSV file in the workspace. "
        "Supports operations: inspect_columns, row_count, missing_values, "
        "numeric_summary, filter, aggregate (group_by), and top_k."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the target CSV file in the workspace.",
            },
            "operation": {
                "type": "string",
                "enum": [
                    "inspect_columns",
                    "row_count",
                    "missing_values",
                    "numeric_summary",
                    "filter",
                    "aggregate",
                    "top_k",
                ],
                "description": "Target analysis operation to execute.",
            },
            "column": {
                "type": "string",
                "description": "Optional column name to focus on (e.g. for numeric_summary or top_k).",
            },
            "group_by": {
                "type": "string",
                "description": "Column name to group by for aggregate operation.",
            },
            "target_column": {
                "type": "string",
                "description": "Numeric column to aggregate for aggregate operation.",
            },
            "agg_func": {
                "type": "string",
                "enum": ["mean", "sum", "count", "min", "max"],
                "description": "Aggregation function (default: mean).",
            },
            "filter_column": {
                "type": "string",
                "description": "Column name to filter by.",
            },
            "filter_operator": {
                "type": "string",
                "enum": ["equals", "==", "!=", ">", "<", ">=", "<=", "contains"],
                "description": "Comparison operator for filter operation.",
            },
            "filter_value": {
                "type": "string",
                "description": "Comparison value for filter operation.",
            },
            "top_k_count": {
                "type": "integer",
                "description": "Number of records to return for top_k (default: 5).",
            },
            "ascending": {
                "type": "boolean",
                "description": "Sort ascending for top_k (default: false = highest first).",
            },
        },
        "required": ["file_path", "operation"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs.get("file_path")
        operation = kwargs.get("operation")

        if not operation or not isinstance(operation, str):
            return ToolResult.failure_result(
                self.name,
                "INVALID_OPERATION",
                "Operation parameter is required and must be a string.",
            )
        operation = operation.strip().lower()

        canonical_path, path_err = validate_and_resolve_path(str(file_path or ""))
        if path_err or canonical_path is None:
            return ToolResult.failure_result(
                self.name,
                "FILE_ERROR",
                path_err or "Invalid file path",
                metadata={"file_path": str(file_path)},
            )

        if canonical_path.suffix.lower() != ".csv":
            return ToolResult.failure_result(
                self.name,
                "UNSUPPORTED_FORMAT",
                f"Data analysis tool only supports CSV files, got: '{canonical_path.suffix}'",
            )

        # Load CSV rows
        try:
            headers, rows = self._load_csv(canonical_path)
        except Exception as e:
            return ToolResult.failure_result(
                self.name,
                "CSV_PARSE_ERROR",
                f"Failed to read CSV dataset: {str(e)}",
            )

        if not headers:
            return ToolResult.failure_result(
                self.name,
                "EMPTY_DATASET",
                "The CSV file is empty or contains no valid header row.",
            )

        # Dispatch operation
        try:
            if operation == "inspect_columns":
                res = self._inspect_columns(headers, rows)
            elif operation == "row_count":
                res = {
                    "total_rows": len(rows),
                    "total_columns": len(headers),
                    "columns": headers,
                }
            elif operation == "missing_values":
                res = self._missing_values(headers, rows)
            elif operation == "numeric_summary":
                col = kwargs.get("column")
                res = self._numeric_summary(headers, rows, col)
            elif operation == "filter":
                f_col = kwargs.get("filter_column") or kwargs.get("column")
                f_op = kwargs.get("filter_operator", "equals")
                f_val = kwargs.get("filter_value")
                res = self._filter(headers, rows, f_col, f_op, f_val)
            elif operation == "aggregate":
                grp_col = kwargs.get("group_by")
                tgt_col = kwargs.get("target_column") or kwargs.get("column")
                agg = kwargs.get("agg_func", "mean")
                res = self._aggregate(headers, rows, grp_col, tgt_col, agg)
            elif operation == "top_k":
                col = kwargs.get("column")
                k = int(kwargs.get("top_k_count", 5))
                asc = bool(kwargs.get("ascending", False))
                res = self._top_k(headers, rows, col, k, asc)
            else:
                return ToolResult.failure_result(
                    self.name,
                    "UNKNOWN_OPERATION",
                    f"Unsupported operation '{operation}'. Supported operations: "
                    f"inspect_columns, row_count, missing_values, numeric_summary, filter, aggregate, top_k.",
                )

            return ToolResult.success_result(
                self.name,
                result={
                    "operation": operation,
                    "dataset": canonical_path.name,
                    "analysis": res,
                },
                metadata={"total_rows": len(rows), "total_columns": len(headers)},
            )

        except ValueError as e:
            return ToolResult.failure_result(self.name, "ARGUMENT_ERROR", str(e))
        except Exception as e:
            return ToolResult.failure_result(
                self.name, "ANALYSIS_FAILED", f"Analysis error: {str(e)}"
            )

    def _load_csv(self, path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            headers = [h.strip() for h in (reader.fieldnames or []) if h]
            rows: List[Dict[str, str]] = []
            for i, row in enumerate(reader):
                if i >= MAX_ROWS_LIMIT:
                    break
                rows.append(
                    {k.strip(): (v.strip() if v else "") for k, v in row.items() if k}
                )
            return headers, rows

    def _inspect_columns(
        self, headers: List[str], rows: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        types = {}
        for h in headers:
            values = [r[h] for r in rows if r.get(h)]
            is_num = False
            if values:
                numeric_count = sum(1 for v in values[:50] if self._is_float(v))
                is_num = (numeric_count / min(len(values), 50)) >= 0.8
            types[h] = "numeric" if is_num else "string"

        preview = rows[:3]
        return {
            "columns": headers,
            "column_types": types,
            "row_count": len(rows),
            "sample_rows": preview,
        }

    def _missing_values(
        self, headers: List[str], rows: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        total = len(rows)
        report = {}
        for h in headers:
            missing = sum(
                1
                for r in rows
                if not r.get(h) or r[h].lower() in {"null", "none", "nan", "n/a", ""}
            )
            pct = round((missing / total * 100), 2) if total > 0 else 0.0
            report[h] = {"missing_count": missing, "missing_percent": pct}
        return {"row_count": total, "missing_by_column": report}

    def _numeric_summary(
        self,
        headers: List[str],
        rows: List[Dict[str, str]],
        target_column: Optional[str],
    ) -> Dict[str, Any]:
        cols = [target_column] if target_column else headers
        summaries = {}

        for col in cols:
            if col not in headers:
                raise ValueError(
                    f"Column '{col}' does not exist in dataset. Available: {headers}"
                )
            nums = []
            for r in rows:
                val = r.get(col, "")
                if self._is_float(val):
                    nums.append(float(val))

            if not nums:
                if target_column:
                    raise ValueError(
                        f"Column '{col}' has no numeric values to summarize."
                    )
                continue

            summaries[col] = {
                "count": len(nums),
                "min": min(nums),
                "max": max(nums),
                "mean": round(statistics.mean(nums), 4),
                "median": round(statistics.median(nums), 4),
                "std_dev": round(statistics.stdev(nums), 4) if len(nums) > 1 else 0.0,
            }

        return {"summaries": summaries}

    def _filter(
        self,
        headers: List[str],
        rows: List[Dict[str, str]],
        col: Optional[str],
        op: str,
        val: Any,
    ) -> Dict[str, Any]:
        if not col or col not in headers:
            raise ValueError(
                f"Filter column '{col}' is required and must exist in: {headers}"
            )
        if val is None:
            raise ValueError("Filter value is required.")

        op = op.lower()
        val_str = str(val).strip()
        is_num = self._is_float(val_str)
        val_num = float(val_str) if is_num else 0.0

        matches = []
        for r in rows:
            cell = r.get(col, "").strip()
            matched = False

            if op in {"equals", "=="}:
                matched = cell.lower() == val_str.lower()
            elif op == "!=":
                matched = cell.lower() != val_str.lower()
            elif op == "contains":
                matched = val_str.lower() in cell.lower()
            elif op in {">", "<", ">=", "<="}:
                if self._is_float(cell) and is_num:
                    c_num = float(cell)
                    if op == ">":
                        matched = c_num > val_num
                    elif op == "<":
                        matched = c_num < val_num
                    elif op == ">=":
                        matched = c_num >= val_num
                    elif op == "<=":
                        matched = c_num <= val_num
            if matched:
                matches.append(r)

        return {
            "filter_column": col,
            "operator": op,
            "filter_value": val,
            "matching_count": len(matches),
            "rows_preview": matches[:MAX_RETURN_ROWS],
            "truncated": len(matches) > MAX_RETURN_ROWS,
        }

    def _aggregate(
        self,
        headers: List[str],
        rows: List[Dict[str, str]],
        group_col: Optional[str],
        target_col: Optional[str],
        agg: str,
    ) -> Dict[str, Any]:
        if not group_col or group_col not in headers:
            raise ValueError(
                f"Group-by column '{group_col}' is required and must exist in: {headers}"
            )
        if not target_col or target_col not in headers:
            raise ValueError(
                f"Target column '{target_col}' is required and must exist in: {headers}"
            )

        agg = agg.lower()
        groups: Dict[str, List[float]] = {}
        counts: Dict[str, int] = {}

        for r in rows:
            grp = r.get(group_col, "").strip() or "Unknown"
            val = r.get(target_col, "").strip()
            counts[grp] = counts.get(grp, 0) + 1

            if self._is_float(val):
                groups.setdefault(grp, []).append(float(val))

        results = {}
        for grp, vals in groups.items():
            if not vals:
                continue
            if agg == "mean":
                results[grp] = round(statistics.mean(vals), 4)
            elif agg == "sum":
                results[grp] = round(sum(vals), 4)
            elif agg == "count":
                results[grp] = len(vals)
            elif agg == "min":
                results[grp] = min(vals)
            elif agg == "max":
                results[grp] = max(vals)
            else:
                raise ValueError(
                    f"Unsupported aggregation function '{agg}'. Supported: mean, sum, count, min, max."
                )

        return {
            "group_by": group_col,
            "target_column": target_col,
            "agg_func": agg,
            "results": results,
            "group_counts": counts,
        }

    def _top_k(
        self,
        headers: List[str],
        rows: List[Dict[str, str]],
        col: Optional[str],
        k: int,
        ascending: bool,
    ) -> Dict[str, Any]:
        if not col or col not in headers:
            raise ValueError(
                f"Numeric column '{col}' is required and must exist in: {headers}"
            )

        valid_rows = []
        for r in rows:
            val = r.get(col, "").strip()
            if self._is_float(val):
                valid_rows.append((float(val), r))

        if not valid_rows:
            raise ValueError(f"Column '{col}' does not contain numeric values to rank.")

        valid_rows.sort(key=lambda x: x[0], reverse=not ascending)
        top_entries = [item[1] for item in valid_rows[:k]]

        return {
            "ranked_column": col,
            "order": "ascending" if ascending else "descending",
            "k": k,
            "total_ranked": len(valid_rows),
            "top_records": top_entries,
        }

    @staticmethod
    def _is_float(val: str) -> bool:
        if not val:
            return False
        try:
            float(val)
            return True
        except ValueError:
            return False
