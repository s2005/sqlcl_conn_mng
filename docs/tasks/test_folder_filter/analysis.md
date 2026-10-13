# Analysis: Folder Selection For test

## Goal

Add `--folder` to `test` so a folder of connections can be tested in one call, following the `list` style: folder or below, ANDed with `--filter` (REQ-1, REQ-2).

## Current Behavior

- `test` is built at `src/sqlcl_conn_mng/cli.py:237-242` with `_add_selector` (`:42-57`): a required argparse mutually exclusive group of `--name`, `--filter` (dest `name_filter`) and `--all` (dest `select_all`). `show`, `delete` and `move` use the same helper.
- `list` (`:138-144`, `:430-441`) has an optional `--folder` (dest `folder`) and an optional `--filter`; both are applied in sequence, so they combine as AND. Folder matching is `_in_folder` (`:307-309`): exact folder or any path below it.
- `_cmd_test` (`:703-708`) calls `_select_names` (`:346-351`), which calls `_select_connections` (`:317-327`): `--name` looks up one connection, otherwise every connection, narrowed by `name_filter` unless `select_all`. A batch then refuses duplicated names (`_reject_duplicate_names`, `:330-343`), requires a non-empty match (`_require_matches`, `:360-362`, message from `_describe_selection`, `:354-357`) and runs `_run_batch` (`:365-402`).
- `_run_batch` with `--name` emits `folder=getattr(args, "folder", None)` (`:372`); for `move` that is the destination folder.
- Tests: `tests/test_cli.py:395-416` (`SELECTOR_COMMANDS`, `test_selector_requires_exactly_one`) asserts the exactly-one rule for `test`, `show`, `delete`, `move` through `build_parser().parse_args`. `:522-529` covers the empty selection for `test`, `show`, `move`. `:635-645` covers the `list` AND rule.

## Feasibility

Straightforward. The selection pipeline already supports narrowing; it needs one more narrowing step and a different argparse shape for `test` only. The one non-trivial point is that argparse cannot express "`--folder` and `--filter` may combine but neither may combine with `--name` or `--all`" with mutually exclusive groups alone, so the rule needs a post-parse check that still exits 2 (REQ-2).

## Approach

### Option A: Parser subclass that validates after parsing (recommended)

`test` gets its own selector helper: an optional mutually exclusive group `--name` / `--all`, plus `--filter` and `--folder` (dest `select_folder`) outside it. The `test` subparser is created with `parser_class=` a small `argparse.ArgumentParser` subclass whose `parse_known_args` checks the rule and calls `self.error(...)` (exit 2). `_SubParsersAction` calls the subparser's `parse_known_args`, so the check runs from `build_parser().parse_args` and from `main` alike.

| Advantages | Disadvantages |
| ---------- | ------------- |
| Usage errors stay exit 2 and are raised by the parser, matching every other usage error | One more small class in `cli.py` |
| `parse_args`-level tests keep working for `test` | Relies on argparse calling the subparser's `parse_known_args`, which it has done for every supported Python |
| No change to `main` or to the other commands | |

### Option B: Validate in `main` after parsing

Attach a validator with `set_defaults` and call it from `main` with `parser.commands[args.command].error(...)`.

| Advantages | Disadvantages |
| ---------- | ------------- |
| No parser subclass | `build_parser().parse_args(["test"])` no longer exits 2, so the existing selector test and any caller of `build_parser` see a different contract |
| | Validation lives away from the option definitions |

### Option C: Separate argparse group trickery

Put `--folder` into the existing group and add `--filter` twice. Not workable: argparse forbids a dest/option in two groups, and a single group cannot allow the folder/filter pair.

Recommended: Option A.

## Implementation Notes

- **Distinct dest (REQ-1, REQ-7).** The selector is stored as `select_folder`, not `folder`. `_select_connections` reads it with `getattr(args, "select_folder", None)`, so `move` (whose `args.folder` is the destination) can never be narrowed by its destination, and `_run_batch`'s `folder=` field for `move --name` is unaffected.
- **Selection (REQ-1, REQ-2).** In `_select_connections`, after the `--name` branch and unless `select_all`: narrow by `_in_folder(c, select_folder)` when given, then by `_matches(c.name, name_filter)` when given. Order and sort are unchanged (`store.connections()` order, as today).
- **Rule check (REQ-2).** Error when no selector is given; when `--name` or `--all` is given together with `--folder` or `--filter`. The `--name`/`--all` pair stays in an argparse mutually exclusive group, so argparse already rejects it. Message style follows argparse, e.g. `argument --folder: not allowed with argument --name`.
- **Description (REQ-3).** `_describe_selection` returns `--all`, or the given parts joined by a space: `--folder '/dev'`, `--filter 'x_*'`, or both in that order. With only `--filter` the text is unchanged (`--filter 'nomatch*'`), so the existing message tests hold.
- **Batch (REQ-4).** `_cmd_test` already treats any non-`--name` selection as a batch; no change beyond the selection.
- **Help text.** `test --help` describes `--folder` as "Every connection in this folder or below; combines with --filter as AND." and the usage line shows the rule.
- **Root folder (REQ-8).** `_in_folder` is not touched. For `--folder /` it builds `wanted = "/"`, so it matches connections whose folder is `/` and never a subfolder (`startswith("//")`). `test --folder /` inherits this through the shared helper.
- **Git Bash.** `--folder /dev` needs `MSYS_NO_PATHCONV=1` in Git Bash, as for `list`; docs examples carry the prefix (REQ-6).

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A shared helper change alters `show`, `delete` or `move` (REQ-7) | `test` gets its own selector helper; `_add_selector` is untouched; existing selector tests for the three commands stay in `SELECTOR_COMMANDS` |
| `move`'s destination `--folder` is read as a selector | Distinct dest `select_folder`, read with `getattr`; a regression test runs `move --filter ... --folder /x` and asserts every match is moved |
| `--folder /` selects only root-level connections, which differs from the "this folder or below" help wording | Kept on purpose (REQ-8, decision Q7) so existing `list --folder /` callers see no change; tests pin it for `list` and `test`; a root-and-below option is a follow-up task |
| A folder batch starts SQLcl for many connections | Same as `--all` today; documented per-connection cost in `SKILL.md` already applies |

## Test Strategy

Unit tests in `tests/test_cli.py`, all with `subprocess.run` mocked and the `fake_home` fixture (`dev_local` in `/dev/local`, `Prod One` in `/prod`, `root_conn` at `/`):

- Parser: `test` accepts `--folder`, `--folder` + `--filter`, `--filter`, `--all`, `--name`; rejects with exit 2 no selector and each forbidden pair, through `parse_args` and through `main` (REQ-2, AC-3). `test` moves out of the shared `SELECTOR_COMMANDS` exactly-one test into its own test; `show`, `delete`, `move` stay (REQ-7, AC-8).
- Selection: `test --folder /dev` runs SQLcl for `dev_local` only (not `Prod One` or `root_conn`) and the selected names equal `list --folder /dev --format json` names (AC-1); `--folder /dev --filter 'root_*'` matches nothing and `--folder /dev --filter 'dev_*'` matches `dev_local` (AC-2).
- Empty match: `--folder /nope` and `--folder /dev --filter 'x*'` exit 1, no SQLcl run, message names the selectors; JSON envelope carries it (AC-4).
- Batch: table lines and summary, JSON batch envelope, a failing connection gives exit 1, a store with two connections named `dev_local` in `/dev/local` (built from `dup_home` by adding the second id to that folder in `folders.json`) is refused for `--folder /dev` (AC-5).
- Root folder: `list --folder /` returns only `root_conn`; `test --folder /` runs SQLcl for `root_conn` only (REQ-8, AC-9).
- Regression: `move --filter '*_*' --folder /x` still passes `/x` to every move (AC-8).

No integration test is added: folder selection happens before SQLcl starts and the per-connection SQLcl call is the one the existing integration tests already cover.
