<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# CodeGraph plugin

CodeGraph is an optional AEGIS add-on that indexes Python source into a local
SQLite database and answers bounded navigation questions about it: where a
symbol is defined, what a file declares, who calls a function, and what
refers to a symbol. AEGIS reaches it through the `know_graph` commands
described in `.agentic/CLI.md`; the plugin can also be run on its own.

It runs on the same Python as AEGIS (3.11 to 3.14) and needs nothing from the
network: the Tree-sitter parser and its Python grammar are vendored in
`vendor/`. Indexing is supported on Windows x64 and Linux x86_64 with glibc
2.17 or newer. On any other platform the queries still read an existing
database, and `know_graph` reports that this Python cannot index
(`indexing_supported = false` in JSON).

Support is `tested` for the environments listed in `MANIFEST.json` under
`tested` - Windows x64 with Python 3.11, 3.12 and 3.14, and Linux x86_64 with
Python 3.12 - and `untested` for any other Python whose vendored binding
loads; `know_graph` shows which applies.

## Install

1. Copy this folder, without `tests/`, to `.agentic/plugins/codegraph/` in
   the repository, and commit it. It is add-on payload: replace it wholesale
   to upgrade and do not edit it in place. A core AEGIS upgrade keeps it.
2. Ignore the database folder in Git, in `.gitignore`. If the file has the
   common Python rule `*.py[cod]`, it also hides the Windows natives (`.pyd`);
   add the negation line so they are committed:

   ```text
   .agentic/knowledge/codegraph/
   !.agentic/plugins/codegraph/vendor/**/*.pyd
   ```

3. Enable it in `.agentic/aegis.toml`, and make sure `[layout]` names the
   source (and optionally test) folders to index:

   ```toml
   [codegraph]
   enabled = true
   ```

4. Build the first index, then query:

   ```text
   python .agentic/aegis.py know_graph_index
   python .agentic/aegis.py know_graph_find OrderRepository
   ```

To uninstall, delete `.agentic/plugins/codegraph/` and
`.agentic/knowledge/codegraph/`, and remove the `[codegraph]` table and the
ignore line.

## Configuration

The AEGIS core validates `enabled`, `database`, the result and output limits
and the three time limits; `.agentic/CLI.md` describes them. The plugin owns
the indexing scope:

| Key | Default | Meaning |
|---|---|---|
| `include` | `[]` | Extra paths or globs to index besides `[layout] source` and `tests`. |
| `exclude` | `[]` | Paths or globs never indexed; wins over everything else. |
| `include_untracked` | `true` | In a Git repository, also index untracked files that are not ignored. |
| `index_tests` | `true` | Index files matching `[layout] tests`. |
| `python_import_roots` | `[]` | Folders that import names start from, such as `src`. When empty: each folder holding a `pyproject.toml` or `setup.cfg`, plus its `src/`, else the repository root. |
| `max_file_bytes` | `1048576` | Larger files are inventoried as `too-large` and not parsed. |
| `parse_timeout_seconds` | `10` | Seconds one file may take to parse before its worker is replaced and the file is recorded as failed. |

Paths use the AEGIS `[layout]` rules: an entry ending in `/` is a folder, an
entry with `*`, `?` or `[` is a case-sensitive glob, anything else is an exact
path or folder name. The installed `.agentic/` folder is never indexed, nor
is any path with a folder named `.git`, `node_modules`, `__pycache__`, `.venv`,
`venv`, `.tox`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `dist`, `build`
or `.eggs`, or ending in `.egg-info` - including a source package that happens
to use one of those names; `include` does not bring them back.

## What the answers mean

Every reference carries a label:

| Label | Meaning |
|---|---|
| `direct-syntax` | An import statement that names an indexed module or symbol. |
| `lexical-binding` | A name bound through Python's scoping rules: a local or parameter, a module-level definition, or an imported name that resolves to an indexed symbol. |
| `candidate` | An attribute such as `self.save()` or `obj.save()`, or an unbound name, matched by name only; up to five ranked guesses, never a confirmed call. |
| `unresolved` | A name the index cannot bind, such as a star or dynamic import, or a missing member of an indexed module. |
| `external` | A built-in, or an import from outside the indexed modules such as the standard library. |

Answers cite the files they come from. Read the cited source before acting on
an answer, and treat `candidate` and `unresolved` as leads, not facts.

## Standalone use

The entry point accepts the same operations AEGIS uses plus `scope`, which
previews what would be indexed without writing anything:

```text
python -I -B -X utf8 .agentic/plugins/codegraph/codegraph.py scope --root .
python -I -B -X utf8 .agentic/plugins/codegraph/codegraph.py index --root .
python -I -B -X utf8 .agentic/plugins/codegraph/codegraph.py find --root . --json -- Order
```

`-I -B` keep the run isolated from the user's site packages and stop Python
from writing bytecode beside the plugin.

## Vendored parsers

`vendor/` holds unmodified files from the wheels pinned in
`requirements.lock`: `tree_sitter/__init__.py` with one `_binding` extension
per supported Python version and platform, and `tree_sitter_python/__init__.py`
with its two stable-ABI `_binding` extensions. `natives.py` picks the matching
binding by the running interpreter's extension suffixes, so one folder serves
every supported Python. `NOTICES.txt` carries their MIT licences.

To change a parser version, as a deliberate developer task:

1. Update the pins, wheel names, sizes and SHA-256 hashes in
   `requirements.lock` from PyPI, for `win_amd64` and `manylinux` x86_64 and
   every supported CPython version.
2. Download those wheels into a scratch folder and confirm each hash, for
   example with `python -m pip download --no-deps --only-binary=:all:
   --require-hashes -r requirements.lock` per platform and version, or by
   comparing `hashlib.sha256` of each file.
3. Replace `vendor/` with the files listed above, extracted from the
   verified wheels; the `__init__.py` files must be identical across wheels.
4. Update `parsers` in `MANIFEST.json` and the licence texts in `NOTICES.txt`.
5. Run the test suite on every Python version and platform in
   `MANIFEST.json`'s `tested` list, and adjust that list to what passed.

A new grammar version can change what is extracted: raise `EXTRACTOR_REVISION`
in `codegraph/python_extract.py` when it does, so `know_graph_check` reports
existing databases stale and the next index re-extracts every file.

## Known issue: Tree-sitter progress callbacks

Tree-sitter's `progress_callback` parse option crashes the Python 3.11 and
3.12 builds of the pinned binding. CodeGraph never uses it: each file is
parsed in a spawned worker process that is killed and replaced when it
exceeds `parse_timeout_seconds`, which also bounds a parser that hangs or
crashes.

## Tests

```text
python -m pytest -q 05_Software/aegis/plugins/codegraph/tests
```

The suite builds small repositories in temporary folders, runs the entry
point with the interpreter flags AEGIS uses, and needs Git on `PATH` for the
Git cases.
