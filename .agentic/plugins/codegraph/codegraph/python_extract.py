#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file python_extract.py
@brief Python definitions and references from Tree-sitter syntax trees.
@details One file at a time, extraction records definitions with exact
         positions and every reference together with how its name is bound
         inside that file (`local`, `import`, `builtin`, `self`, `attribute`,
         `star`, `dynamic` or `unbound`). Cross-file labels are assigned later
         by the indexer from these bindings, so an unchanged file can be reused
         while its links are recomputed. Repository code is never imported or
         executed. Extraction runs in spawned worker processes so a file that
         takes too long can be stopped by terminating its worker; Tree-sitter
         progress callbacks are deliberately unused (they crash the pinned
         binding on Python 3.11 and 3.12).
"""

# IMPORTS

from __future__ import annotations

import builtins
import collections
import hashlib
import multiprocessing
import os
import time
from dataclasses import dataclass, field
from multiprocessing import connection
from typing import Self

from codegraph import natives
from codegraph.config import Settings

# CONSTANTS

EXTRACTOR_REVISION = "python-2"
#: test-only switch: a worker sleeps instead of parsing this repository path
SLOW_FILE_HOOK = "CODEGRAPH_TEST_SLOW_FILE"
#: test-only switch: append each started worker's process ID to this file
WORKER_PIDS_HOOK = "CODEGRAPH_TEST_WORKER_PIDS"
BUILTIN_NAMES = frozenset(dir(builtins))
DEFINITIONS = ("function_definition", "class_definition")
WORKER_STARTUP_SECONDS = 120
POLL_SECONDS = 0.05

# DATA MODELS / TYPEDEFINITIONS


@dataclass
class Symbol:
    """One definition with its identity and exact range."""

    id: str
    kind: str
    name: str
    qualified_name: str
    signature: str
    parent_id: str | None
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    depth: int


@dataclass
class Reference:
    """One use of a name, with how the name is bound in its file."""

    kind: str
    spelling: str
    line: int
    column: int
    from_id: str | None
    binding: str
    local_target: str | None = None
    qualname: str | None = None


@dataclass
class FileFacts:
    """Extraction result for one file."""

    path: str
    module: str
    status: str
    reason: str | None
    symbols: list[Symbol] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)


class Cancelled(Exception):
    """Extraction was stopped on request."""


@dataclass
class _Scope:
    """A Python name scope: module, class or function."""

    kind: str
    qualified: str
    symbol_id: str
    parent: _Scope | None
    depth: int
    class_qualified: str | None = None
    names: dict = field(default_factory=dict)
    nested: list = field(default_factory=list)

# HELPER FUNCTIONS


def _collapse(text: str) -> str:
    """@brief Collapse whitespace runs to single spaces."""
    return " ".join(text.split())


def _visible(scope: _Scope) -> _Scope:
    """@brief The nearest scope a nested function sees: class bodies are skipped."""
    while scope.kind == "class" and scope.parent is not None:
        scope = scope.parent
    return scope


def _parameter_name(item):
    """@brief The identifier a parameter node binds, including `*args: T` forms."""
    for child in item.children:
        if child.type == "identifier":
            return child
        if child.type in ("list_splat_pattern", "dictionary_splat_pattern"):
            return next((c for c in child.children if c.type == "identifier"), None)
    return None


def symbol_id(path: str, scope: str, kind: str, name: str, signature: str,
              ordinal: int) -> str:
    """@brief The stable 128-bit symbol ID as 32 hexadecimal characters."""
    key = "\x1f".join([path, scope, kind, name, signature, str(ordinal)])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


class _Extractor:
    """Walks one parsed file twice per scope: bindings first, then references."""

    def __init__(self, path: str, source: bytes, module: str) -> None:
        self.path = path
        self.source = source
        self.module = module
        self.lines = source.split(b"\n")
        self.symbols: list[Symbol] = []
        self.references: list[Reference] = []
        self.key_counts: dict[tuple, int] = {}
        self.defining: set[tuple[int, int]] = set()
        self.is_package = path.rsplit("/", 1)[-1] in ("__init__.py", "__init__.pyi")

    # positions and text

    def column(self, row: int, byte_column: int) -> int:
        """@brief 1-based code-point column of a Tree-sitter byte offset."""
        line = self.lines[row] if row < len(self.lines) else b""
        return len(line[:byte_column].decode("utf-8", "replace")) + 1

    def start(self, node) -> tuple[int, int]:
        """@brief 1-based line and column where node starts."""
        row, col = node.start_point
        return row + 1, self.column(row, col)

    def end(self, node) -> tuple[int, int]:
        """@brief 1-based line and column of the node's last character."""
        row, col = node.end_point
        return row + 1, max(1, self.column(row, col) - 1)

    def text(self, node) -> str:
        """@brief Node source text without comments, whitespace collapsed."""
        pieces, cursor = [], node.start_byte
        stack = [node]
        comments = []
        while stack:
            current = stack.pop()
            if current.type == "comment":
                comments.append((current.start_byte, current.end_byte))
            else:
                stack.extend(current.children)
        for begin, finish in sorted(comments):
            pieces.append(self.source[cursor:begin])
            cursor = finish
        pieces.append(self.source[cursor:node.end_byte])
        return _collapse(b"".join(pieces).decode("utf-8", "replace"))

    # symbols

    def add_symbol(self, kind: str, name: str, scope: _Scope, signature: str,
                   start_node, end_node, depth: int) -> Symbol:
        """@brief Create a definition with its stable identity."""
        key = (self.path, scope.qualified, kind, name, signature)
        ordinal = self.key_counts.get(key, 0)
        self.key_counts[key] = ordinal + 1
        digest = symbol_id(*key, ordinal)
        start_line, start_column = self.start(start_node)
        end_line, end_column = self.end(end_node)
        symbol = Symbol(digest, kind, name, f"{scope.qualified}.{name}", signature,
                        scope.symbol_id, start_line, start_column, end_line, end_column, depth)
        self.symbols.append(symbol)
        return symbol

    def bind_variable(self, identifier, scope: _Scope, annotation: str = "") -> None:
        """@brief First binding of a simple name in a scope defines a variable."""
        name = identifier.text.decode("utf-8", "replace")
        if name in scope.names:
            return
        symbol = self.add_symbol("variable", name, scope, annotation, identifier,
                                 identifier, scope.depth + 1)
        scope.names[name] = ("local", symbol.id)
        self.defining.add(identifier.start_point)

    def bind_targets(self, node, scope: _Scope) -> None:
        """@brief Bind every plain identifier in an assignment target."""
        if node.type == "identifier":
            self.bind_variable(node, scope)
        elif node.type in ("pattern_list", "tuple_pattern", "list_pattern",
                           "list_splat_pattern", "parenthesized_expression",
                           "as_pattern_target", "expression_list"):
            for child in node.named_children:
                self.bind_targets(child, scope)

    # imports

    def absolute_module(self, node) -> str | None:
        """@brief The absolute module path of a `from` import's module part."""
        if node.type == "dotted_name":
            return node.text.decode("utf-8", "replace")
        prefix = next((c for c in node.children if c.type == "import_prefix"), None)
        level = prefix.text.count(b".") if prefix else 0
        named = next((c for c in node.children if c.type == "dotted_name"), None)
        package = self.module.split(".") if self.is_package else self.module.split(".")[:-1]
        if level - 1 > len(package):
            return None
        base = package[:len(package) - (level - 1)] if level > 1 else package
        parts = [*base, *( [named.text.decode("utf-8", "replace")] if named else [])]
        return ".".join(part for part in parts if part) or None

    def imports(self, node):
        """@brief (bound name or None, qualified target or None, binding, ref node)."""
        if node.type == "import_statement":
            for item in node.children_by_field_name("name"):
                if item.type == "aliased_import":
                    target = item.child_by_field_name("name").text.decode("utf-8", "replace")
                    alias = item.child_by_field_name("alias").text.decode("utf-8", "replace")
                    yield alias, target, "import", item, target
                else:
                    target = item.text.decode("utf-8", "replace")
                    yield target.split(".")[0], target.split(".")[0], "import", item, target
            return
        module = self.absolute_module(node.child_by_field_name("module_name"))
        if any(child.type == "wildcard_import" for child in node.children):
            spelling = f"{module}.*" if module else "*"
            yield None, None, "star", node, spelling
            return
        for item in node.children_by_field_name("name"):
            name_node = item.child_by_field_name("name") if item.type == "aliased_import" else item
            name = name_node.text.decode("utf-8", "replace")
            alias = (item.child_by_field_name("alias").text.decode("utf-8", "replace")
                     if item.type == "aliased_import" else name)
            if module is None:
                yield alias, None, "dynamic", item, name
            else:
                yield alias, f"{module}.{name}", "import", item, f"{module}.{name}"

    # pass 1: bindings

    def collect(self, node, scope: _Scope) -> None:
        """@brief Register names a statement binds, without entering nested scopes."""
        kind = node.type
        if kind == "decorated_definition":
            definition = node.child_by_field_name("definition")
            self.define(definition, node, scope)
            return
        if kind in DEFINITIONS:
            self.define(node, node, scope)
            return
        if kind == "lambda":
            return
        if kind in ("global_statement", "nonlocal_statement"):
            marker = "global" if kind == "global_statement" else "nonlocal"
            for child in node.named_children:
                if child.type == "identifier":
                    scope.names.setdefault(child.text.decode("utf-8", "replace"), (marker, None))
            return
        if kind in ("import_statement", "import_from_statement"):
            for bound, target, binding, _item, _spelling in self.imports(node):
                if bound and binding == "import" and bound not in scope.names:
                    scope.names[bound] = ("import", target)
            return
        if kind == "assignment":
            left = node.child_by_field_name("left")
            annotation = node.child_by_field_name("type")
            if left is not None and left.type == "identifier":
                self.bind_variable(left, scope, self.text(annotation) if annotation else "")
            elif left is not None:
                self.bind_targets(left, scope)
        elif kind == "augmented_assignment":
            left = node.child_by_field_name("left")
            if left is not None and left.type == "identifier":
                self.bind_variable(left, scope)
        elif kind in ("for_statement", "for_in_clause"):
            left = node.child_by_field_name("left")
            if left is not None:
                self.bind_targets(left, scope)
        elif kind == "as_pattern":
            alias = node.child_by_field_name("alias")
            if alias is not None:
                self.bind_targets(alias, scope)
        elif kind == "named_expression":
            name = node.child_by_field_name("name")
            if name is not None:
                self.bind_variable(name, scope)
        for child in node.children:
            self.collect(child, scope)

    def define(self, definition, outer_node, scope: _Scope) -> None:
        """@brief Create a function, method or class symbol and queue its scope."""
        name_node = definition.child_by_field_name("name")
        name = name_node.text.decode("utf-8", "replace")
        if definition.type == "class_definition":
            supers = definition.child_by_field_name("superclasses")
            signature = f"class {name}" + (self.text(supers) if supers else "")
            kind = "class"
        else:
            parameters = definition.child_by_field_name("parameters")
            returns = definition.child_by_field_name("return_type")
            prefix = "async def" if any(c.type == "async" for c in definition.children) else "def"
            signature = f"{prefix} {name}{self.text(parameters)}"
            if returns is not None:
                signature += f" -> {self.text(returns)}"
            kind = "method" if scope.kind == "class" else "function"
        symbol = self.add_symbol(kind, name, scope, signature, outer_node, definition,
                                 scope.depth + 1)
        self.defining.add(name_node.start_point)
        if name not in scope.names:
            scope.names[name] = ("local", symbol.id)
        scope.nested.append((definition, symbol))

    def parameters(self, definition, scope: _Scope) -> None:
        """@brief Bind a function's parameters as parameter symbols."""
        parameters = definition.child_by_field_name("parameters")
        for item in parameters.named_children if parameters is not None else []:
            name_node, annotation = None, ""
            if item.type == "identifier":
                name_node = item
            elif item.type in ("default_parameter", "typed_default_parameter"):
                name_node = item.child_by_field_name("name")
            elif item.type in ("typed_parameter", "list_splat_pattern",
                               "dictionary_splat_pattern"):
                name_node = _parameter_name(item)
            if item.type in ("typed_parameter", "typed_default_parameter"):
                type_node = item.child_by_field_name("type")
                annotation = self.text(type_node) if type_node is not None else ""
            if name_node is None:
                continue
            name = name_node.text.decode("utf-8", "replace")
            symbol = self.add_symbol("parameter", name, scope, annotation, name_node,
                                     name_node, scope.depth + 1)
            scope.names[name] = ("local", symbol.id)
            self.defining.add(name_node.start_point)

    # pass 2: references

    def resolve(self, name: str, scope: _Scope) -> tuple[str, str | None, str | None]:
        """
        @brief (binding, local target, qualified target) for a name in a scope.
        @details A `global` name resolves in the module scope and a `nonlocal`
                 name in the enclosing functions; a lambda parameter resolves
                 to binding `lambda`, which records nothing.
        """
        current: _Scope | None = scope
        while current is not None:
            entry = current.names.get(name)
            if entry is None:
                current = current.parent
                continue
            binding, value = entry
            if binding == "nonlocal":
                current = current.parent
                continue
            if binding == "global":
                module = current
                while module.parent is not None:
                    module = module.parent
                entry = module.names.get(name) if module is not current else None
                if entry is None or entry[0] in ("global", "nonlocal"):
                    break
                binding, value = entry
            return (binding, value, None) if binding in ("local", "lambda") else \
                (binding, None, value)
        if name in BUILTIN_NAMES:
            return "builtin", None, f"builtins.{name}"
        return "unbound", None, None

    def add_reference(self, kind: str, spelling: str, node, scope: _Scope, binding: str,
                      local: str | None = None, qualname: str | None = None) -> None:
        """@brief Record one reference at node's position."""
        line, column = self.start(node)
        self.references.append(Reference(kind, spelling, line, column, scope.symbol_id,
                                          binding, local, qualname))

    def dotted(self, node) -> list[str] | None:
        """@brief Identifier parts of a plain `a.b.c` chain, or None."""
        if node.type == "identifier":
            return [node.text.decode("utf-8", "replace")]
        if node.type == "attribute":
            head = self.dotted(node.child_by_field_name("object"))
            tail = node.child_by_field_name("attribute")
            if head is not None and tail is not None:
                return [*head, tail.text.decode("utf-8", "replace")]
        return None

    def chain_binding(self, parts: list[str], scope: _Scope):
        """@brief Binding for a dotted chain from how its first name is bound."""
        binding, _local, qualname = self.resolve(parts[0], scope)
        if binding == "import" and qualname:
            return "import", None, ".".join([qualname, *parts[1:]])
        if parts[0] in ("self", "cls") and len(parts) == 2 and scope.class_qualified:
            return "self", None, f"{scope.class_qualified}.{parts[1]}"
        return "attribute", None, None

    def refs(self, node, scope: _Scope) -> None:
        """@brief Record the references of one node, outside nested scopes."""
        kind = node.type
        if kind in ("comment", "string"):
            if kind == "string":
                for child in node.named_children:
                    if child.type == "interpolation":
                        self.refs(child, scope)
            return
        if kind == "lambda":
            self.lambda_refs(node, scope)
            return
        if kind == "delete_statement":
            for child in node.named_children:
                self.write_refs(child, scope)
            return
        if kind in ("for_statement", "for_in_clause", "as_pattern", "named_expression"):
            target = node.child_by_field_name(
                "alias" if kind == "as_pattern" else
                "name" if kind == "named_expression" else "left")
            self.write_refs(target, scope)
            for child in node.named_children:
                if target is None or (child.start_byte, child.end_byte) != \
                        (target.start_byte, target.end_byte):
                    self.refs(child, scope)
            return
        if kind == "decorated_definition":
            for child in node.children:
                if child.type == "decorator":
                    self.refs(child, scope)
            self.definition_refs(node.child_by_field_name("definition"), scope)
            return
        if kind in DEFINITIONS:
            self.definition_refs(node, scope)
            return
        if kind in ("import_statement", "import_from_statement"):
            for _bound, _target, binding, item, spelling in self.imports(node):
                self.add_reference("import", spelling, item, scope, binding,
                                   qualname=spelling if binding == "import" else None)
            return
        if kind == "call":
            self.call_refs(node, scope)
            return
        if kind == "attribute":
            parts = self.dotted(node)
            if parts is not None:
                binding, _local, qualname = self.chain_binding(parts, scope)
                if binding == "import":
                    self.add_reference("read", ".".join(parts), node, scope, binding,
                                       qualname=qualname)
                    return
            self.refs(node.child_by_field_name("object"), scope)
            return
        if kind == "keyword_argument":
            self.refs(node.child_by_field_name("value"), scope)
            return
        if kind in ("assignment", "augmented_assignment"):
            left = node.child_by_field_name("left")
            self.write_refs(left, scope)
            for name in ("type", "right"):
                child = node.child_by_field_name(name)
                if child is not None:
                    self.refs(child, scope)
            return
        if kind == "identifier":
            if node.start_point in self.defining:
                return
            name = node.text.decode("utf-8", "replace")
            binding, local, qualname = self.resolve(name, scope)
            if binding != "lambda":
                self.add_reference("read", name, node, scope, binding, local, qualname)
            return
        if kind in ("global_statement", "nonlocal_statement", "dotted_name"):
            return
        for child in node.named_children:
            self.refs(child, scope)

    def write_refs(self, node, scope: _Scope) -> None:
        """@brief Writes to names and attribute chains; other targets are read."""
        if node is None:
            return
        if node.type == "identifier":
            if node.start_point in self.defining:
                return
            name = node.text.decode("utf-8", "replace")
            binding, local, qualname = self.resolve(name, scope)
            if binding != "lambda":
                self.add_reference("write", name, node, scope, binding, local, qualname)
        elif node.type in ("pattern_list", "tuple_pattern", "list_pattern",
                           "list_splat_pattern", "parenthesized_expression",
                           "expression_list", "as_pattern_target"):
            for child in node.named_children:
                self.write_refs(child, scope)
        elif node.type == "attribute" and self.dotted(node) is not None:
            parts = self.dotted(node)
            binding, _local, qualname = self.chain_binding(parts, scope)
            self.add_reference("write", ".".join(parts), node, scope, binding,
                               qualname=qualname)
            if binding == "attribute" and parts[0] not in ("self", "cls"):
                root = node
                while root.type == "attribute":
                    root = root.child_by_field_name("object")
                self.refs(root, scope)
        else:
            self.refs(node, scope)

    def lambda_refs(self, node, scope: _Scope) -> None:
        """@brief A lambda's defaults in the enclosing scope, its body in its own."""
        inner = _Scope("function", scope.qualified, scope.symbol_id, _visible(scope),
                       scope.depth, scope.class_qualified)
        parameters = node.child_by_field_name("parameters")
        for item in parameters.named_children if parameters is not None else []:
            name_node = item if item.type == "identifier" else (
                item.child_by_field_name("name")
                if item.type in ("default_parameter", "typed_default_parameter")
                else _parameter_name(item))
            if name_node is not None:
                inner.names[name_node.text.decode("utf-8", "replace")] = ("lambda", None)
            value = item.child_by_field_name("value")
            if value is not None:
                self.refs(value, scope)
        body = node.child_by_field_name("body")
        if body is not None:
            self.refs(body, inner)

    def call_refs(self, node, scope: _Scope) -> None:
        """@brief A call reference for a named callee, then its arguments."""
        function = node.child_by_field_name("function")
        parts = self.dotted(function) if function is not None else None
        if parts is None and function is not None and function.type == "attribute":
            attribute = function.child_by_field_name("attribute")
            self.add_reference("call", attribute.text.decode("utf-8", "replace"), attribute,
                               scope, "attribute")
            self.refs(function.child_by_field_name("object"), scope)
        elif parts is None:
            if function is not None:
                self.refs(function, scope)
        elif len(parts) == 1:
            binding, local, qualname = self.resolve(parts[0], scope)
            self.add_reference("call", parts[0], function, scope, binding, local, qualname)
        else:
            binding, _local, qualname = self.chain_binding(parts, scope)
            self.add_reference("call", ".".join(parts), function, scope, binding,
                               qualname=qualname)
            if binding == "attribute" and parts[0] not in ("self", "cls"):
                root = function
                while root.type == "attribute":
                    root = root.child_by_field_name("object")
                self.refs(root, scope)
        arguments = node.child_by_field_name("arguments")
        if arguments is not None:
            self.refs(arguments, scope)

    def definition_refs(self, definition, scope: _Scope) -> None:
        """@brief Parts of a definition evaluated in the enclosing scope."""
        for name in ("superclasses", "return_type"):
            child = definition.child_by_field_name(name)
            if child is not None:
                self.refs(child, scope)
        parameters = definition.child_by_field_name("parameters")
        for item in parameters.named_children if parameters is not None else []:
            for field_name in ("type", "value"):
                child = item.child_by_field_name(field_name)
                if child is not None:
                    self.refs(child, scope)

    # scopes

    def run_scope(self, statements: list, scope: _Scope) -> None:
        """@brief Bindings, then references, then nested scopes."""
        for statement in statements:
            self.collect(statement, scope)
        for statement in statements:
            self.refs(statement, scope)
        for definition, symbol in scope.nested:
            is_class = definition.type == "class_definition"
            inner = _Scope(
                kind="class" if is_class else "function",
                qualified=symbol.qualified_name, symbol_id=symbol.id,
                parent=_visible(scope), depth=symbol.depth,
                class_qualified=(symbol.qualified_name if is_class else
                                 scope.qualified if scope.kind == "class" else
                                 scope.class_qualified))
            if not is_class:
                self.parameters(definition, inner)
            body = definition.child_by_field_name("body")
            self.run_scope(body.named_children if body is not None else [], inner)

# PUBLIC API


def module_name(path: str, roots: list[str]) -> str:
    """
    @brief Dotted module name of a file relative to its deepest import root.
    @param[in] path Repository-relative POSIX path.
    @param[in] roots Repository-relative import roots; "" is the repository root.
    @return For example `shop.orders`; `pkg/__init__.py` names `pkg`.
    """
    containing = [root for root in roots
                  if root == "" or path == root or path.startswith(root + "/")]
    root = max(containing, key=len) if containing else ""
    relative = path[len(root) + 1:] if root else path
    stem = relative.rsplit(".", 1)[0]
    parts = stem.split("/")
    if parts[-1] == "__init__" and len(parts) > 1:
        parts = parts[:-1]
    return ".".join(parts)


def import_roots(settings: Settings, manifests: list[str]) -> list[str]:
    """
    @brief Import roots: the setting, else manifest folders and their `src/`.
    @details No repository code runs; manifests are only located, not executed.
    """
    if settings.python_import_roots:
        return sorted({root.replace("\\", "/").strip("/") for root in settings.python_import_roots})
    roots: set[str] = set()
    for manifest in manifests:
        folder = manifest.rsplit("/", 1)[0] if "/" in manifest else ""
        roots.add(folder)
        src = f"{folder}/src" if folder else "src"
        if (settings.root / src).is_dir():
            roots.add(src)
    return sorted(roots) or [""]


def extract(path: str, source: bytes, module: str, parser) -> FileFacts:
    """
    @brief Extract definitions and references from one Python file.
    @param[in] path Repository-relative path of the file.
    @param[in] source File content.
    @param[in] module Dotted module name of the file.
    @param[in] parser A Tree-sitter parser for Python.
    @return Facts with status `complete`, `partial` (syntax errors elsewhere)
            or `failed` (undecodable or nothing extractable).
    """
    if source.startswith(b"\xef\xbb\xbf"):
        source = source[3:]
    try:
        source.decode("utf-8")
    except UnicodeDecodeError:
        return FileFacts(path, module, "failed", "encoding")
    tree = parser.parse(source)
    root = tree.root_node
    statements = [child for child in root.named_children
                  if child.type != "ERROR" and not child.has_error]
    status, reason = ("partial", "syntax") if root.has_error else ("complete", None)
    if root.has_error and not statements:
        return FileFacts(path, module, "failed", "syntax")
    work = _Extractor(path, source, module)
    digest = symbol_id(path, module, "module", module, "", 0)
    filled = [row for row, line in enumerate(work.lines) if line.rstrip(b"\r")]
    last_row = filled[-1] if filled else 0
    last_column = work.column(last_row, len(work.lines[last_row].rstrip(b"\r"))) - 1
    module_symbol = Symbol(digest, "module", module.rsplit(".", 1)[-1], module, "", None,
                           1, 1, last_row + 1, max(1, last_column), 0)
    work.symbols.append(module_symbol)
    work.run_scope(statements, _Scope("module", module, digest, None, 0))
    work.symbols.sort(key=lambda s: (s.start_line, s.start_column, s.depth))
    return FileFacts(path, module, status, reason, work.symbols, work.references)


def _worker_main(conn) -> None:
    """@brief Extraction worker: load the parser, then answer jobs until told to stop."""
    try:
        parser = natives.new_parser()
    except Exception as exc:  # noqa: BLE001 - reported to the parent, not raised
        conn.send(("error", f"{type(exc).__name__}: {exc}"))
        return
    conn.send(("ready", None))
    slow = os.environ.get(SLOW_FILE_HOOK)
    while True:
        try:
            job = conn.recv()
        except EOFError:
            return
        if job is None:
            return
        path, source, module = job
        if slow and path == slow:
            time.sleep(3600)
        conn.send(extract(path, source, module, parser))


class ExtractorPool:
    """Spawned extraction workers with a per-file time limit."""

    def __init__(self, workers: int = 1, timeout: float = 10) -> None:
        """
        @brief Prepare a pool; workers start on first use.
        @param[in] workers Maximum concurrent worker processes.
        @param[in] timeout Seconds one file may take before its worker is replaced.
        """
        self.size = max(1, workers)
        self.timeout = timeout
        self.context = multiprocessing.get_context("spawn")
        self.workers: list[tuple] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def _start(self) -> tuple:
        """@brief Start one worker and wait until its parser is loaded."""
        parent, child = self.context.Pipe()
        process = self.context.Process(target=_worker_main, args=(child,), daemon=True)
        process.start()
        child.close()
        record = os.environ.get(WORKER_PIDS_HOOK)
        if record:
            with open(record, "a", encoding="utf-8") as handle:
                handle.write(f"{process.pid}\n")
        if not parent.poll(WORKER_STARTUP_SECONDS):
            process.kill()
            raise RuntimeError("extraction worker did not start")
        state, detail = parent.recv()
        if state != "ready":
            process.join()
            raise RuntimeError(f"extraction worker could not load the parser: {detail}")
        worker = (process, parent)
        self.workers.append(worker)
        return worker

    def _stop(self, worker: tuple) -> None:
        """@brief Terminate one worker and forget it."""
        process, conn = worker
        process.kill()
        process.join(5)
        conn.close()
        if worker in self.workers:
            self.workers.remove(worker)

    def close(self) -> None:
        """@brief Stop every worker."""
        for worker in list(self.workers):
            self._stop(worker)

    def extract_all(self, jobs, should_stop=None):
        """
        @brief Extract (path, source, module) jobs, yielding FileFacts as they finish.
        @param[in] jobs Iterable of (path, bytes, module).
        @param[in] should_stop Optional callable; True cancels extraction.
        @exception Cancelled when should_stop returns True.
        """
        pending = collections.deque(jobs)
        idle: list[tuple] = []
        busy: dict = {}
        while pending or busy:
            if should_stop is not None and should_stop():
                self.close()
                raise Cancelled()
            while pending and (idle or len(self.workers) < self.size):
                worker = idle.pop() if idle else self._start()
                job = pending.popleft()
                worker[1].send(job)
                busy[worker[1]] = (worker, job, time.monotonic() + self.timeout)
            for conn in connection.wait(list(busy), timeout=POLL_SECONDS):
                worker, job, _deadline = busy.pop(conn)
                try:
                    facts = conn.recv()
                except (EOFError, OSError):
                    self._stop(worker)
                    yield FileFacts(job[0], job[2], "failed", "parser-crash")
                    continue
                idle.append(worker)
                yield facts
            now = time.monotonic()
            for conn, (worker, job, deadline) in list(busy.items()):
                if now >= deadline:
                    busy.pop(conn)
                    self._stop(worker)
                    yield FileFacts(job[0], job[2], "failed", "parse-timeout")

# END OF FILE
