"""Controlled behavioral validation for SoftwareLifecycleEnv tasks.

The environment accepts model-written patches, so validation intentionally avoids
arbitrary unrestricted execution. Instead, it:

* parses task modules with a conservative AST allowlist
* blocks dangerous imports and dunder access
* executes only known task modules with a tiny builtins surface
* runs fixed visible and hidden deterministic checks per task
* keeps hidden regression details out of the external API surface
"""

from __future__ import annotations

import ast
import types
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Sequence, Tuple


class ValidationError(Exception):
    """Raised when task code cannot be validated safely."""


SAFE_AST_NODES = (
    ast.Module,
    ast.FunctionDef,
    ast.arguments,
    ast.arg,
    ast.Return,
    ast.Assign,
    ast.AnnAssign,
    ast.Expr,
    ast.If,
    ast.IfExp,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.In,
    ast.NotIn,
    ast.Is,
    ast.IsNot,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.USub,
    ast.UAdd,
    ast.BinOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Name,
    ast.Load,
    ast.Store,
    ast.Constant,
    ast.Call,
    ast.Attribute,
    ast.List,
    ast.Tuple,
    ast.Dict,
    ast.Set,
    ast.Subscript,
    ast.Slice,
    ast.ListComp,
    ast.comprehension,
    ast.ImportFrom,
    ast.alias,
    ast.JoinedStr,
    ast.FormattedValue,
    ast.keyword,
)

FORBIDDEN_CALLS = {
    "__import__",
    "compile",
    "delattr",
    "eval",
    "exec",
    "getattr",
    "globals",
    "input",
    "locals",
    "open",
    "setattr",
    "vars",
}


@dataclass
class ValidationCheck:
    """One deterministic check run during validation."""

    name: str
    category: str
    visibility: str
    passed: bool
    detail: str
    weight: float = 1.0


@dataclass
class ValidationReport:
    """Structured task validation summary."""

    task_id: str
    behavioral_score: float
    regression_score: float
    structure_score: float
    anti_gaming_score: float
    overall_score: float
    final_success: bool
    summary: str
    failure_messages: List[str] = field(default_factory=list)
    checks: List[ValidationCheck] = field(default_factory=list)

    @property
    def passed_checks(self) -> int:
        return sum(1 for check in self.checks if check.passed)

    @property
    def total_checks(self) -> int:
        return len(self.checks)

    @property
    def visible_checks(self) -> List[ValidationCheck]:
        return [check for check in self.checks if check.visibility == "visible"]

    @property
    def hidden_checks(self) -> List[ValidationCheck]:
        return [check for check in self.checks if check.visibility == "hidden"]

    @property
    def visible_failure_messages(self) -> List[str]:
        return [check.detail for check in self.visible_checks if not check.passed]

    @property
    def hidden_failure_messages(self) -> List[str]:
        return [check.detail for check in self.hidden_checks if not check.passed]

    @property
    def hidden_failure_count(self) -> int:
        return len(self.hidden_failure_messages)

    @property
    def integrity_failure_count(self) -> int:
        return sum(
            1
            for check in self.checks
            if check.category == "integrity" and not check.passed
        )

    def as_dict(self) -> Dict[str, Any]:
        """Return a full JSON-serializable internal view of the report."""
        return {
            "task_id": self.task_id,
            "behavioral_score": round(self.behavioral_score, 3),
            "regression_score": round(self.regression_score, 3),
            "structure_score": round(self.structure_score, 3),
            "anti_gaming_score": round(self.anti_gaming_score, 3),
            "overall_score": round(self.overall_score, 3),
            "final_success": self.final_success,
            "summary": self.summary,
            "failure_messages": list(self.failure_messages),
            "passed_checks": self.passed_checks,
            "total_checks": self.total_checks,
            "checks": [asdict(check) for check in self.checks],
        }

    def as_public_dict(self) -> Dict[str, Any]:
        """Return a sanitized view safe to expose through the API."""
        hidden_failures = self.hidden_failure_messages
        public_failures = list(self.visible_failure_messages[:3])
        if hidden_failures:
            public_failures.append(
                f"{len(hidden_failures)} hidden regression or anti-gaming check(s) still failing."
            )

        return {
            "task_id": self.task_id,
            "behavioral_score": round(self.behavioral_score, 3),
            "regression_score": round(self.regression_score, 3),
            "structure_score": round(self.structure_score, 3),
            "anti_gaming_score": round(self.anti_gaming_score, 3),
            "overall_score": round(self.overall_score, 3),
            "final_success": self.final_success,
            "summary": self.summary,
            "failure_messages": public_failures,
            "passed_checks": self.passed_checks,
            "total_checks": self.total_checks,
            "visible_passed_checks": sum(
                1 for check in self.visible_checks if check.passed
            ),
            "visible_total_checks": len(self.visible_checks),
            "hidden_failed_checks": len(hidden_failures),
            "hidden_total_checks": len(self.hidden_checks),
            "checks": [asdict(check) for check in self.visible_checks],
        }


class SafePythonRuntime:
    """Minimal safe loader for known in-memory task modules."""

    def __init__(self, files: Dict[str, str]):
        self._sources = {
            self._path_to_module_name(path): content
            for path, content in files.items()
            if path.endswith(".py") and path.startswith("src/")
        }
        self._modules: Dict[str, types.ModuleType] = {}
        self._loading: set[str] = set()
        self._packages = self._collect_packages(self._sources.keys())
        self._safe_builtins = {
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "enumerate": enumerate,
            "float": float,
            "int": int,
            "len": len,
            "list": list,
            "max": max,
            "min": min,
            "range": range,
            "round": round,
            "set": set,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "zip": zip,
            "__import__": self._custom_import,
        }

    @staticmethod
    def _path_to_module_name(path: str) -> str:
        return path[:-3].replace("/", ".")

    @staticmethod
    def _collect_packages(module_names: Iterable[str]) -> set[str]:
        packages: set[str] = set()
        for module_name in module_names:
            parts = module_name.split(".")
            for index in range(1, len(parts)):
                packages.add(".".join(parts[:index]))
        return packages

    def _ensure_package(self, package_name: str) -> types.ModuleType:
        existing = self._modules.get(package_name)
        if existing is not None:
            return existing

        module = types.ModuleType(package_name)
        module.__dict__["__path__"] = []
        module.__dict__["__package__"] = (
            package_name.rsplit(".", 1)[0] if "." in package_name else ""
        )
        self._modules[package_name] = module

        if "." in package_name:
            parent_name, child_name = package_name.rsplit(".", 1)
            parent = self._ensure_package(parent_name)
            setattr(parent, child_name, module)

        return module

    def _custom_import(
        self,
        name: str,
        globals_: Dict[str, Any] | None = None,
        locals_: Dict[str, Any] | None = None,
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> types.ModuleType:
        if level != 0:
            raise ImportError("Relative imports are not allowed in task validation.")

        if name in self._sources:
            module = self.load(name)
        elif name in self._packages:
            module = self._ensure_package(name)
        else:
            raise ImportError(f"Import blocked during validation: {name}")

        if fromlist:
            return module

        top_level = name.split(".", 1)[0]
        return self._ensure_package(top_level)

    def _validate_ast(self, module_name: str, source: str) -> ast.Module:
        try:
            tree = ast.parse(source, filename=module_name)
        except SyntaxError as exc:
            raise ValidationError(f"{module_name}: syntax error: {exc.msg}") from exc

        allowed_imports = set(self._sources.keys())
        for node in ast.walk(tree):
            if not isinstance(node, SAFE_AST_NODES):
                raise ValidationError(
                    f"{module_name}: unsupported syntax {type(node).__name__}"
                )
            if isinstance(node, ast.ImportFrom):
                if node.level != 0 or node.module not in allowed_imports:
                    raise ValidationError(f"{module_name}: blocked import {node.module!r}")
            if isinstance(node, ast.Name) and node.id.startswith("__"):
                raise ValidationError(f"{module_name}: dunder access is blocked")
            if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                raise ValidationError(f"{module_name}: dunder attribute access is blocked")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALLS:
                    raise ValidationError(f"{module_name}: forbidden call {node.func.id}")
        return tree

    def load(self, module_name: str) -> types.ModuleType:
        existing = self._modules.get(module_name)
        if existing is not None and module_name not in self._loading:
            return existing

        if module_name in self._loading:
            raise ValidationError(f"Circular import detected while loading {module_name}")

        if module_name not in self._sources:
            raise ValidationError(
                f"Unknown module requested during validation: {module_name}"
            )

        if "." in module_name:
            parent_name, child_name = module_name.rsplit(".", 1)
            parent = self._ensure_package(parent_name)
        else:
            parent = None
            child_name = module_name

        module = types.ModuleType(module_name)
        module.__dict__.update(
            {
                "__builtins__": self._safe_builtins,
                "__name__": module_name,
                "__package__": (
                    module_name.rsplit(".", 1)[0] if "." in module_name else ""
                ),
            }
        )
        self._modules[module_name] = module
        if parent is not None:
            setattr(parent, child_name, module)

        self._loading.add(module_name)
        try:
            tree = self._validate_ast(module_name, self._sources[module_name])
            code = compile(tree, module_name, "exec")
            exec(code, module.__dict__)
        except Exception as exc:  # pragma: no cover - deterministic error path
            raise ValidationError(f"{module_name}: {exc}") from exc
        finally:
            self._loading.discard(module_name)

        return module

    def resolve_function(
        self, module_name: str, function_name: str
    ) -> Callable[..., Any]:
        module = self.load(module_name)
        function = module.__dict__.get(function_name)
        if not callable(function):
            raise ValidationError(f"{module_name}.{function_name} is not callable")
        return function


def _ratio(
    checks: Sequence[ValidationCheck],
    *,
    category: str | None = None,
    visibility: str | None = None,
) -> float:
    scoped = [
        check
        for check in checks
        if (category is None or check.category == category)
        and (visibility is None or check.visibility == visibility)
    ]
    if not scoped:
        return 0.0
    total = sum(check.weight for check in scoped)
    passed = sum(check.weight for check in scoped if check.passed)
    return passed / total if total else 0.0


def _get_function_def(source: str, function_name: str) -> ast.FunctionDef | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return node
    return None


def _source_has_function(source: str, function_name: str) -> bool:
    return _get_function_def(source, function_name) is not None


def _function_uses_parameters(source: str, function_name: str) -> bool:
    function_def = _get_function_def(source, function_name)
    if function_def is None:
        return False
    parameter_names = {arg.arg for arg in function_def.args.args}
    if not parameter_names:
        return True
    for node in ast.walk(function_def):
        if isinstance(node, ast.Name) and node.id in parameter_names and isinstance(node.ctx, ast.Load):
            return True
    return False


def _function_returns_constant_only(source: str, function_name: str) -> bool:
    function_def = _get_function_def(source, function_name)
    if function_def is None:
        return False
    returns = [node for node in ast.walk(function_def) if isinstance(node, ast.Return)]
    if not returns:
        return False
    return all(
        isinstance(node.value, ast.Constant)
        for node in returns
        if node.value is not None
    )


def _source_contains_literal(source: str, literal: str) -> bool:
    return literal in source


def _source_contains_any_literal(source: str, literals: Iterable[str]) -> bool:
    return any(literal in source for literal in literals)


def _function_compares_parameter_to_literals(
    source: str,
    function_name: str,
    literal_values: Iterable[object],
) -> bool:
    function_def = _get_function_def(source, function_name)
    if function_def is None:
        return False

    parameter_names = {arg.arg for arg in function_def.args.args}
    target_values = set(literal_values)
    for node in ast.walk(function_def):
        if not isinstance(node, ast.Compare):
            continue

        compare_nodes = [node.left, *node.comparators]
        names = {
            value.id
            for value in compare_nodes
            if isinstance(value, ast.Name)
        }
        constants = {
            value.value
            for value in compare_nodes
            if isinstance(value, ast.Constant)
        }
        if names & parameter_names and constants & target_values:
            return True
    return False


def _looks_like_two_decimal_money_format(source: str) -> bool:
    if ".2f" in source:
        return True
    if "AMOUNT_DECIMAL_PLACES" in source and "dollars:." in source:
        return True
    return ("% 100" in source or "%100" in source) and ":02d" in source


def _run_function_checks(
    runtime: SafePythonRuntime,
    module_name: str,
    function_name: str,
    cases: Sequence[Tuple[str, Tuple[Any, ...], Any, str]],
    *,
    category: str,
    visibility: str,
) -> List[ValidationCheck]:
    checks: List[ValidationCheck] = []
    try:
        function = runtime.resolve_function(module_name, function_name)
    except ValidationError as exc:
        return [
            ValidationCheck(
                name=f"{function_name}_callable",
                category=category,
                visibility=visibility,
                passed=False,
                detail=str(exc),
            )
        ]

    for case_name, args, expected, detail_prefix in cases:
        try:
            actual = function(*args)
            passed = actual == expected
            detail = (
                f"{detail_prefix} expected {expected!r}, observed {actual!r}"
                if not passed
                else f"{detail_prefix} matched {expected!r}"
            )
        except Exception as exc:  # pragma: no cover - deterministic failure path
            passed = False
            detail = f"{detail_prefix} raised {type(exc).__name__}: {exc}"
        checks.append(
            ValidationCheck(
                name=case_name,
                category=category,
                visibility=visibility,
                passed=passed,
                detail=detail,
            )
        )
    return checks


def _build_summary(task_id: str, checks: List[ValidationCheck]) -> Tuple[str, List[str]]:
    failures = [check.detail for check in checks if not check.passed]
    if not failures:
        return f"{task_id}: all deterministic validation checks passed.", []
    visible_failures = [
        check.detail
        for check in checks
        if not check.passed and check.visibility == "visible"
    ]
    if visible_failures:
        head = visible_failures[0]
        remaining = len(failures) - 1
        if remaining > 0:
            return f"{task_id}: {head} (+{remaining} more issue(s))", failures
        return f"{task_id}: {head}", failures
    return (
        f"{task_id}: visible checks passed, but hidden regression or anti-gaming checks still fail.",
        failures,
    )


def _generic_check(
    name: str,
    passed: bool,
    detail: str,
    *,
    category: str,
    visibility: str = "hidden",
) -> ValidationCheck:
    return ValidationCheck(
        name=name,
        category=category,
        visibility=visibility,
        passed=passed,
        detail=detail,
    )


def _finalize_report(task: dict, checks: List[ValidationCheck]) -> ValidationReport:
    task_id = task["task_id"]
    behavioral = _ratio(checks, category="behavior")
    regression = _ratio(checks, category="regression")
    structure = _ratio(checks, category="structure")
    anti_gaming = _ratio(checks, category="integrity")

    if task_id == "task_hard_maintenance":
        overall = (
            0.05 * behavioral
            + 0.10 * regression
            + 0.25 * structure
            + 0.60 * anti_gaming
        )
        success = (
            behavioral == 1.0
            and regression == 1.0
            and structure >= 0.99
            and anti_gaming == 1.0
        )
    else:
        overall = (
            0.20 * behavioral
            + 0.45 * regression
            + 0.15 * structure
            + 0.20 * anti_gaming
        )
        success = (
            behavioral == 1.0
            and regression == 1.0
            and structure >= 0.67
            and anti_gaming == 1.0
        )

    summary, failures = _build_summary(task_id, checks)
    return ValidationReport(
        task_id=task_id,
        behavioral_score=behavioral,
        regression_score=regression,
        structure_score=structure,
        anti_gaming_score=anti_gaming,
        overall_score=overall,
        final_success=success,
        summary=summary,
        failure_messages=failures,
        checks=checks,
    )


def _validate_easy(task: dict, files: Dict[str, str]) -> ValidationReport:
    runtime = SafePythonRuntime(files)
    checks = _run_function_checks(
        runtime,
        "src.release_preview.router",
        "build_preview_url",
        [
            (
                "preview_url_primary",
                ("feature/Auth_Reset", "WEB-401"),
                "https://preview.internal.example/web-401-auth-reset",
                "Visible preview URL case",
            ),
            (
                "preview_url_hotfix",
                (" hotfix / Billing__retry ", "OPS-9"),
                "https://preview.internal.example/ops-9-billing-retry",
                "Visible hotfix preview URL case",
            ),
            (
                "preview_url_release",
                ("release/May_Cutover", "REL-77"),
                "https://preview.internal.example/rel-77-may-cutover",
                "Visible release preview URL case",
            ),
        ],
        category="behavior",
        visibility="visible",
    )
    checks.extend(
        _run_function_checks(
            runtime,
            "src.release_preview.router",
            "build_preview_url",
            [
                (
                    "preview_url_hidden_api_client",
                    ("bugfix///API__Client", "CORE-11"),
                    "https://preview.internal.example/core-11-api-client",
                    "Hidden bugfix branch case",
                ),
                (
                    "preview_url_hidden_mixed_separators",
                    ("feature / data_SYNC / nightly", "PLAT-204"),
                    "https://preview.internal.example/plat-204-data-sync-nightly",
                    "Hidden mixed-separator case",
                ),
                (
                    "preview_url_hidden_release_numeric",
                    ("release/Sprint_24", "REL-24"),
                    "https://preview.internal.example/rel-24-sprint-24",
                    "Hidden release numeric case",
                ),
                (
                    "preview_url_hidden_blank_branch",
                    ("", "OPS-1"),
                    "https://preview.internal.example/ops-1",
                    "Hidden blank-branch case",
                ),
            ],
            category="regression",
            visibility="hidden",
        )
    )

    source = files.get("src/release_preview/slug_builder.py", "")
    router_source = files.get("src/release_preview/router.py", "")
    settings_source = files.get("src/release_preview/settings.py", "")
    checks.extend(
        [
            _generic_check(
                "preview_slug_function_exists",
                _source_has_function(source, "build_preview_slug"),
                "build_preview_slug must remain defined in src/release_preview/slug_builder.py",
                category="structure",
            ),
            _generic_check(
                "preview_router_function_exists",
                _source_has_function(router_source, "build_preview_url"),
                "build_preview_url must remain defined in src/release_preview/router.py",
                category="structure",
            ),
            _generic_check(
                "preview_router_imports_slug_builder",
                "from src.release_preview.slug_builder import build_preview_slug" in router_source,
                "build_preview_url should continue to delegate slug generation to src/release_preview/slug_builder.py",
                category="structure",
            ),
            _generic_check(
                "preview_router_uses_settings_domain",
                "PREVIEW_DOMAIN" in router_source and "PREVIEW_DOMAIN = 'preview.internal.example'" in settings_source,
                "build_preview_url should use PREVIEW_DOMAIN from settings",
                category="structure",
            ),
            _generic_check(
                "preview_slug_imports_settings",
                "from src.release_preview.settings import PREVIEW_SEPARATOR, RESERVED_BRANCH_PREFIXES"
                in source,
                "build_preview_slug should continue to import preview-routing settings",
                category="structure",
            ),
            _generic_check(
                "preview_slug_uses_input_parameters",
                _function_uses_parameters(source, "build_preview_slug"),
                "build_preview_slug must derive its output from the incoming branch_name and ticket_id parameters",
                category="integrity",
            ),
            _generic_check(
                "preview_slug_not_constant",
                not _function_returns_constant_only(source, "build_preview_slug"),
                "build_preview_slug should not collapse into a constant return value",
                category="integrity",
            ),
            _generic_check(
                "preview_slug_not_hardcoded_visible_answer",
                not _source_contains_literal(source, "web-401-auth-reset"),
                "build_preview_slug should not hardcode the visible preview slug answer",
                category="integrity",
            ),
            _generic_check(
                "preview_slug_uses_config_separator",
                "PREVIEW_SEPARATOR" in source and "PREVIEW_SEPARATOR = '-'" in settings_source,
                "build_preview_slug should respect PREVIEW_SEPARATOR from settings",
                category="integrity",
            ),
            _generic_check(
                "preview_slug_no_underscore_join",
                "'_'.join" not in source and '"_".join' not in source,
                "build_preview_slug should no longer join preview slug pieces with '_'",
                category="integrity",
            ),
            _generic_check(
                "preview_slug_uses_reserved_prefixes",
                "RESERVED_BRANCH_PREFIXES" in source and "RESERVED_BRANCH_PREFIXES" in settings_source,
                "build_preview_slug should use RESERVED_BRANCH_PREFIXES from settings",
                category="integrity",
            ),
            _generic_check(
                "preview_slug_no_visible_literals",
                not _source_contains_any_literal(source, {"WEB-401", "Auth_Reset", "Billing__retry"}),
                "build_preview_slug should not embed visible branch or ticket literals from the prompt",
                category="integrity",
            ),
        ]
    )
    return _finalize_report(task, checks)


def _validate_medium(task: dict, files: Dict[str, str]) -> ValidationReport:
    runtime = SafePythonRuntime(files)
    checks = _run_function_checks(
        runtime,
        "src.helpers.currency",
        "format_cents",
        [
            ("currency_formats_fractional", (1205,), "$12.05", "Visible helper case"),
        ],
        category="behavior",
        visibility="visible",
    )
    checks.extend(
        _run_function_checks(
            runtime,
            "src.api.invoice_endpoint",
            "serialize_invoice_response",
            [
                (
                    "invoice_endpoint_primary",
                    (
                        {
                            "customer": "  Acme Corp  ",
                            "amount_due_cents": 1205,
                            "line_items": ["support", "monitoring"],
                            "status": "past_due",
                        },
                    ),
                    {
                        "invoice": {
                            "customer": "Acme Corp",
                            "amount_due": "$12.05",
                            "line_items": ["monitoring", "support"],
                            "status": "PAST_DUE",
                        },
                        "generated_by": "billing-admin-api",
                    },
                    "Visible endpoint response",
                ),
            ],
            category="behavior",
            visibility="visible",
        )
    )
    checks.extend(
        _run_function_checks(
            runtime,
            "src.helpers.currency",
            "format_cents",
            [
                ("currency_hidden_small_amount", (5,), "$0.05", "Hidden cents-padding case"),
                ("currency_hidden_whole_dollars", (2500,), "$25.00", "Hidden whole-dollar case"),
                ("currency_hidden_one_dollar_one_cent", (101,), "$1.01", "Hidden precision case"),
            ],
            category="regression",
            visibility="hidden",
        )
    )
    checks.extend(
        _run_function_checks(
            runtime,
            "src.api.invoice_endpoint",
            "serialize_invoice_response",
            [
                (
                    "invoice_endpoint_hidden_small_total",
                    (
                        {
                            "customer": "Northwind",
                            "amount_due_cents": 99,
                            "line_items": ["alerts", "backup"],
                            "status": "open",
                        },
                    ),
                    {
                        "invoice": {
                            "customer": "Northwind",
                            "amount_due": "$0.99",
                            "line_items": ["alerts", "backup"],
                            "status": "OPEN",
                        },
                        "generated_by": "billing-admin-api",
                    },
                    "Hidden small-total endpoint case",
                ),
                (
                    "invoice_endpoint_hidden_zero_total",
                    (
                        {
                            "customer": "  Contoso ",
                            "amount_due_cents": 0,
                            "line_items": ["triage"],
                            "status": "closed",
                        },
                    ),
                    {
                        "invoice": {
                            "customer": "Contoso",
                            "amount_due": "$0.00",
                            "line_items": ["triage"],
                            "status": "CLOSED",
                        },
                        "generated_by": "billing-admin-api",
                    },
                    "Hidden zero-total endpoint case",
                ),
            ],
            category="regression",
            visibility="hidden",
        )
    )

    helper_source = files.get("src/helpers/currency.py", "")
    presenter_source = files.get("src/presenters/invoice_presenter.py", "")
    endpoint_source = files.get("src/api/invoice_endpoint.py", "")
    api_config_source = files.get("src/config/api_formatting.py", "")
    dashboard_config_source = files.get("src/config/dashboard_formatting.py", "")
    checks.extend(
        [
            _generic_check(
                "helper_function_exists",
                _source_has_function(helper_source, "format_cents"),
                "format_cents must remain defined in src/helpers/currency.py",
                category="structure",
            ),
            _generic_check(
                "helper_uses_api_formatting_config",
                "src.config.api_formatting" in helper_source
                and "AMOUNT_DECIMAL_PLACES" in helper_source
                and "CURRENCY_SYMBOL" in helper_source,
                "format_cents should depend on src/config/api_formatting.py for API payload formatting",
                category="structure",
            ),
            _generic_check(
                "endpoint_imports_presenter",
                "from src.presenters.invoice_presenter import present_invoice" in endpoint_source,
                "Endpoint serialization should continue to depend on src/presenters/invoice_presenter.py",
                category="structure",
            ),
            _generic_check(
                "presenter_imports_helper",
                "from src.helpers.currency import format_cents" in presenter_source,
                "Presenter should continue to depend on src/helpers/currency.py",
                category="structure",
            ),
            _generic_check(
                "endpoint_calls_presenter",
                "present_invoice(" in endpoint_source,
                "serialize_invoice_response should call present_invoice to build the invoice payload",
                category="structure",
            ),
            _generic_check(
                "presenter_calls_helper",
                "format_cents(" in presenter_source,
                "Presenter should call format_cents for amount formatting",
                category="structure",
            ),
            _generic_check(
                "helper_not_dashboard_rounding",
                "src.config.dashboard_formatting" not in helper_source
                and "SUMMARY_ROUNDING_MODE" not in helper_source
                and "SUMMARY_ROUNDING_MODE = 'whole_dollars'" in dashboard_config_source,
                "format_cents should not use dashboard-only whole-dollar rounding for API payloads",
                category="integrity",
            ),
            _generic_check(
                "helper_uses_input_parameter",
                _function_uses_parameters(helper_source, "format_cents"),
                "format_cents must derive its output from the incoming cents value",
                category="integrity",
            ),
            _generic_check(
                "helper_not_constant",
                not _function_returns_constant_only(helper_source, "format_cents"),
                "format_cents should not collapse into a constant return value",
                category="integrity",
            ),
            _generic_check(
                "helper_not_hardcoded_visible_amount",
                not _source_contains_literal(helper_source, "$12.05")
                and not _source_contains_literal(presenter_source, "$12.05"),
                "The visible amount_due example should not be hardcoded into helper or presenter logic",
                category="integrity",
            ),
            _generic_check(
                "helper_uses_real_two_decimal_formatting",
                _looks_like_two_decimal_money_format(helper_source)
                and "AMOUNT_DECIMAL_PLACES = 2" in api_config_source,
                "format_cents should use the API config's two-decimal money-formatting strategy instead of whole-dollar rounding",
                category="integrity",
            ),
            _generic_check(
                "helper_not_branching_on_visible_case",
                not _function_compares_parameter_to_literals(
                    helper_source,
                    "format_cents",
                    {1205},
                ),
                "format_cents should not branch on the visible cents value 1205",
                category="integrity",
            ),
            _generic_check(
                "helper_no_visible_invoice_literals",
                not _source_contains_any_literal(
                    helper_source + presenter_source + endpoint_source,
                    {"1205", "Acme Corp", "past_due"},
                ),
                "Helper, presenter, and endpoint should not embed visible invoice-specific literals from the task prompt",
                category="integrity",
            ),
        ]
    )
    return _finalize_report(task, checks)


def _validate_hard(task: dict, files: Dict[str, str]) -> ValidationReport:
    runtime = SafePythonRuntime(files)
    checks = _run_function_checks(
        runtime,
        "src.api.customer_payload",
        "build_customer_payload",
        [
            (
                "customer_payload_primary",
                (
                    {
                        "first_name": "  maya",
                        "last_name": "SINGH  ",
                        "account_tier": "ENTERPRISE",
                        "status": "ACTIVE",
                    },
                ),
                {
                    "display_name": "Maya Singh",
                    "account_tier": "enterprise",
                    "status": "active",
                },
                "Visible customer payload case",
            ),
            (
                "customer_payload_partial",
                (
                    {
                        "first_name": "  maya",
                        "last_name": "",
                        "account_tier": "SMB",
                        "status": "TRIAL",
                    },
                ),
                {
                    "display_name": "Maya",
                    "account_tier": "smb",
                    "status": "trial",
                },
                "Visible customer blank-last-name case",
            ),
        ],
        category="behavior",
        visibility="visible",
    )
    checks.extend(
        _run_function_checks(
            runtime,
            "src.exports.vendor_rows",
            "build_vendor_row",
            [
                (
                    "vendor_row_primary",
                    (
                        {
                            "contact_first": "ops",
                            "contact_last": "TEAM",
                            "vendor_code": "v-14",
                            "active": True,
                        },
                    ),
                    {
                        "display_name": "Ops Team",
                        "vendor_code": "V-14",
                        "active": "yes",
                    },
                    "Visible vendor row case",
                ),
                (
                    "vendor_row_partial",
                    (
                        {
                            "contact_first": "",
                            "contact_last": "support",
                            "vendor_code": "help-2",
                            "active": False,
                        },
                    ),
                    {
                        "display_name": "Support",
                        "vendor_code": "HELP-2",
                        "active": "no",
                    },
                    "Visible vendor blank-first-name case",
                ),
            ],
            category="behavior",
            visibility="visible",
        )
    )
    checks.extend(
        _run_function_checks(
            runtime,
            "src.api.customer_payload",
            "build_customer_payload",
            [
                (
                    "customer_payload_hidden_spacing",
                    (
                        {
                            "first_name": "",
                            "last_name": " support  ",
                            "account_tier": "ENTERPRISE",
                            "status": "ACTIVE",
                        },
                    ),
                    {
                        "display_name": "Support",
                        "account_tier": "enterprise",
                        "status": "active",
                    },
                    "Hidden customer spacing case",
                ),
                (
                    "customer_payload_hidden_compound",
                    (
                        {
                            "first_name": "qa",
                            "last_name": "  lead ",
                            "account_tier": "MIDMARKET",
                            "status": "PAUSED",
                        },
                    ),
                    {
                        "display_name": "Qa Lead",
                        "account_tier": "midmarket",
                        "status": "paused",
                    },
                    "Hidden customer compound-name case",
                ),
            ],
            category="regression",
            visibility="hidden",
        )
    )
    checks.extend(
        _run_function_checks(
            runtime,
            "src.exports.vendor_rows",
            "build_vendor_row",
            [
                (
                    "vendor_row_hidden_spacing",
                    (
                        {
                            "contact_first": "  account",
                            "contact_last": " lead  ",
                            "vendor_code": "acct-7",
                            "active": True,
                        },
                    ),
                    {
                        "display_name": "Account Lead",
                        "vendor_code": "ACCT-7",
                        "active": "yes",
                    },
                    "Hidden vendor spacing case",
                ),
                (
                    "vendor_row_hidden_blank_last",
                    (
                        {
                            "contact_first": "multi",
                            "contact_last": "",
                            "vendor_code": "multi-3",
                            "active": False,
                        },
                    ),
                    {
                        "display_name": "Multi",
                        "vendor_code": "MULTI-3",
                        "active": "no",
                    },
                    "Hidden vendor blank-last-name case",
                ),
            ],
            category="regression",
            visibility="hidden",
        )
    )

    shared_source = files.get("src/shared/display_name.py", "")
    customer_source = files.get("src/api/customer_payload.py", "")
    vendor_source = files.get("src/exports/vendor_rows.py", "")
    checks.extend(
        [
            _generic_check(
                "shared_helper_exists",
                _source_has_function(shared_source, "normalize_display_name"),
                "src/shared/display_name.py must define normalize_display_name",
                category="structure",
            ),
            _generic_check(
                "customer_imports_shared",
                "from src.shared.display_name import normalize_display_name" in customer_source,
                "Customer payload builder should import normalize_display_name from shared.py",
                category="structure",
            ),
            _generic_check(
                "vendor_imports_shared",
                "from src.shared.display_name import normalize_display_name" in vendor_source,
                "Vendor export builder should import normalize_display_name from shared.py",
                category="structure",
            ),
            _generic_check(
                "customer_calls_shared",
                "normalize_display_name(" in customer_source,
                "Customer payload builder should delegate cleanup to normalize_display_name",
                category="structure",
            ),
            _generic_check(
                "vendor_calls_shared",
                "normalize_display_name(" in vendor_source,
                "Vendor export builder should delegate cleanup to normalize_display_name",
                category="structure",
            ),
            _generic_check(
                "customer_duplicate_cleanup_removed",
                ".strip().title()" not in customer_source,
                "Customer payload builder should no longer duplicate cleanup logic inline",
                category="integrity",
            ),
            _generic_check(
                "vendor_duplicate_cleanup_removed",
                ".strip().title()" not in vendor_source,
                "Vendor export builder should no longer duplicate cleanup logic inline",
                category="integrity",
            ),
            _generic_check(
                "shared_helper_uses_input_parameter",
                _function_uses_parameters(shared_source, "normalize_display_name"),
                "normalize_display_name must derive its output from the incoming parts parameter",
                category="integrity",
            ),
            _generic_check(
                "shared_helper_not_constant",
                not _function_returns_constant_only(shared_source, "normalize_display_name"),
                "normalize_display_name should not collapse into a constant return value",
                category="integrity",
            ),
            _generic_check(
                "shared_helper_contains_cleanup_logic",
                ".strip().title()" in shared_source and "if part and part.strip()" in shared_source,
                "normalize_display_name should own the title-case and blank-part cleanup logic",
                category="integrity",
            ),
        ]
    )
    return _finalize_report(task, checks)


def validate_task(task: dict, files: Dict[str, str]) -> ValidationReport:
    """Run deterministic validation for a task's current in-memory files."""
    task_id = task["task_id"]
    if task_id == "task_easy_testing":
        return _validate_easy(task, files)
    if task_id == "task_medium_debugging":
        return _validate_medium(task, files)
    if task_id == "task_hard_maintenance":
        return _validate_hard(task, files)
    raise ValueError(f"Unknown task_id for validation: {task_id}")
