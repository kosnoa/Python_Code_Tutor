import ast
import builtins
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


def _get_name(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    return None


def _add_target_names(target: ast.AST, names: Set[str]) -> None:
    if isinstance(target, ast.Name):
        names.add(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            _add_target_names(elt, names)
    elif isinstance(target, ast.ExceptHandler):
        if target.name:
            names.add(target.name)
    elif isinstance(target, ast.Starred):
        _add_target_names(target.value, names)


@dataclass
class RuntimeIssue:
    type: str
    line: Optional[int]
    snippet: Optional[str]
    why: str
    severity: str = "warning"


class UndefinedNameVisitor(ast.NodeVisitor):
    """Simple static heuristic for likely undefined variables."""

    def __init__(self, source: str):
        self.source = source
        self.scopes: List[Set[str]] = [set()]
        self.issues: List[RuntimeIssue] = []
        runtime_builtins = set()
        runtime_builtins.update(dir(builtins))
        if isinstance(__builtins__, dict):
            runtime_builtins.update(__builtins__.keys())
        else:
            runtime_builtins.update(dir(__builtins__))
        self.builtins = runtime_builtins
        self._seen: Set[Tuple[str, Optional[int]]] = set()

    def _push_scope(self) -> None:
        self.scopes.append(set())

    def _pop_scope(self) -> None:
        if len(self.scopes) > 1:
            self.scopes.pop()

    def _is_defined(self, name: str) -> bool:
        return any(name in scope for scope in reversed(self.scopes))

    def _define(self, name: str) -> None:
        if name and not name.startswith("_"):
            self.scopes[-1].add(name)
        elif name:
            # Keep underscore-prefixed names visible as local symbols.
            self.scopes[-1].add(name)

    def _report_undefined(self, node: ast.Name) -> None:
        if node.id in self.builtins or node.id in {"None", "True", "False"}:
            return
        if self._is_defined(node.id):
            return
        key = (node.id, node.lineno)
        if key in self._seen:
            return
        self._seen.add(key)
        self.issues.append(
            RuntimeIssue(
                type="Potential issue",
                line=node.lineno,
                snippet=ast.get_source_segment(self.source, node),
                why=f"Variable '{node.id}' might not be defined before it is used.",
            )
        )

    def visit_Name(self, node: ast.Name) -> Any:
        if isinstance(node.ctx, ast.Load):
            self._report_undefined(node)
        return self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self._define(name)
        return self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        for alias in node.names:
            if alias.name == "*":
                # Conservative skip; wildcard imports are too hard to resolve statically.
                continue
            name = alias.asname or alias.name
            self._define(name)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self._define(node.name)
        self._push_scope()
        for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
            if arg.arg:
                self._define(arg.arg)
        if node.args.vararg and node.args.vararg.arg:
            self._define(node.args.vararg.arg)
        if node.args.kwarg and node.args.kwarg.arg:
            self._define(node.args.kwarg.arg)
        for deco in node.decorator_list:
            self.visit(deco)
        self._add_function_body(node)
        self._pop_scope()
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        return self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self._define(node.name)
        self._push_scope()
        for base in node.bases:
            self.visit(base)
        for deco in node.decorator_list:
            self.visit(deco)
        self._add_function_body(node)
        self._pop_scope()
        return node

    def visit_For(self, node: ast.For) -> Any:
        self.visit(node.iter)
        _add_target_names(node.target, self.scopes[-1])
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)
        return node

    def visit_While(self, node: ast.While) -> Any:
        self.visit(node.test)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)
        return node

    def visit_With(self, node: ast.With) -> Any:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                _add_target_names(item.optional_vars, self.scopes[-1])
        for stmt in node.body:
            self.visit(stmt)
        return node

    def visit_Assign(self, node: ast.Assign) -> Any:
        for target in node.targets:
            _add_target_names(target, self.scopes[-1])
        self.visit(node.value)
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        _add_target_names(node.target, self.scopes[-1])
        self.visit(node.annotation)
        if node.value:
            self.visit(node.value)
        return node

    def visit_AugAssign(self, node: ast.AugAssign) -> Any:
        _add_target_names(node.target, self.scopes[-1])
        self.visit(node.value)
        return node

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> Any:
        self._push_scope()
        if node.name:
            self._define(node.name)
        for h in node.body:
            self.visit(h)
        self._pop_scope()
        return node

    def _add_function_body(self, node: Any) -> None:
        for stmt in getattr(node, "body", []):
            self.visit(stmt)


class RuntimePatternVisitor(ast.NodeVisitor):
    """Heuristics for obvious runtime pitfalls."""

    def __init__(self, source: str):
        self.source = source
        self.issues: List[RuntimeIssue] = []

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            if self._is_constant_zero(node.right):
                self.issues.append(
                    RuntimeIssue(
                        type="ZeroDivisionError",
                        line=node.lineno,
                        snippet=ast.get_source_segment(self.source, node),
                        why="This expression can divide by zero.",
                    )
                )
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> Any:
        if isinstance(node.iter, ast.Constant) and isinstance(node.iter.value, int):
            self.issues.append(
                RuntimeIssue(
                    type="TypeError",
                    line=node.iter.lineno,
                    snippet=ast.get_source_segment(self.source, node.iter),
                    why="You are trying to iterate over an int, which is not iterable.",
                )
            )
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> Any:
        # Beginner-friendly nudge for 'is None' vs '==' mistakes.
        if len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
            comp_rhs = node.comparators[0]
            if isinstance(comp_rhs, ast.Constant) and comp_rhs.value is None:
                self.issues.append(
                    RuntimeIssue(
                        type="BestPractice",
                        line=node.lineno,
                        snippet=ast.get_source_segment(self.source, node),
                        why="Use `is None` / `is not None` for None checks.",
                        severity="info",
                    )
                )
        self.generic_visit(node)

    @staticmethod
    def _is_constant_zero(node: ast.AST) -> bool:
        return isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and node.value == 0


class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.loop_depth = 0
        self.max_loop_depth = 0
        self.has_nested_data = False
        self.has_recursion = False
        self.function_name: Optional[str] = None

    def visit_For(self, node: ast.For) -> Any:
        self.loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self.loop_depth)
        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_While(self, node: ast.While) -> Any:
        self.loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self.loop_depth)
        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        previous = self.function_name
        self.function_name = node.name
        self._check_recursion(node)
        self.generic_visit(node)
        self.function_name = previous

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self.visit_FunctionDef(node)

    def _check_recursion(self, node: ast.AST) -> None:
        fn = self.function_name
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id == fn:
                self.has_recursion = True


def run_static_checks(source: str) -> Dict[str, Any]:
    tree = ast.parse(source)
    issues: List[RuntimeIssue] = []

    undefined_checker = UndefinedNameVisitor(source)
    undefined_checker.visit(tree)
    issues.extend(undefined_checker.issues)

    runtime_checker = RuntimePatternVisitor(source)
    runtime_checker.visit(tree)
    issues.extend(runtime_checker.issues)

    complexity_checker = ComplexityVisitor()
    complexity_checker.visit(tree)
    complexity = {
        "time": _derive_time_complexity(complexity_checker),
        "space": _derive_space_complexity(complexity_checker),
    }

    return {
        "issues": [
            {
                "type": issue.type,
                "line": issue.line,
                "snippet": issue.snippet,
                "why": issue.why,
                "severity": issue.severity,
            }
            for issue in issues
        ],
        "complexity": complexity,
        "recursion": complexity_checker.has_recursion,
        "max_loop_depth": complexity_checker.max_loop_depth,
    }


def _derive_time_complexity(complexity_checker: ComplexityVisitor) -> str:
    if complexity_checker.has_recursion:
        return "Depends on recursion depth; often O(2^n) for naive recursion"
    if complexity_checker.max_loop_depth == 0:
        return "Roughly O(n)"
    if complexity_checker.max_loop_depth == 1:
        return "Roughly O(n)"
    if complexity_checker.max_loop_depth == 2:
        return "Approximately O(n^2)"
    return "Approximately O(n^k), k > 2"


def _derive_space_complexity(complexity_checker: ComplexityVisitor) -> str:
    if complexity_checker.has_recursion:
        return "O(recursion depth)"
    return "O(1) to O(n) typical for this file"
