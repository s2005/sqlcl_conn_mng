# Notes: Folder Selection For test

## Drifts

### D-1: `parser_class` is not an `add_parser` argument

- **Spec**: `implementation_plan.md`, Phase 1, Implementation Work, third bullet ("create the `test` subparser with `parser_class=_TestSelectorParser`"); `analysis.md`, Option A.
- **Code**: `src/sqlcl_conn_mng/cli.py:198` - `parser_class` belongs to `add_subparsers`, which fixes one class for every subcommand. `add_parser` forwards its extra keywords to that class's constructor, so `add_parser(..., parser_class=...)` raises `TypeError`.
- **Difference**: the plan's way of giving only `test` a different parser class does not exist in argparse.

## Candidate solutions

### 01: One subparser class for every command, rule check opt-in per command

- **Approach**: `add_subparsers(parser_class=_TestSelectorParser)`. The class takes a `test_selector=False` keyword, and only `test` passes `test_selector=True` to `add_parser`. The parent parser from `_global_options` uses the same class, because typeshed types `parents=` with the subparser class.
- **Scope**: `cli.py` only.
- **Pros**: public argparse API only; behaviour matches the PRD; the other commands skip the check.
- **Cons**: every subparser is an instance of a class named for `test`.
- **Risk**: low.

### 02: Build the `test` parser outside `add_parser`

- **Approach**: construct `_TestSelectorParser` directly and register it in the subparsers action's private `_name_parser_map` and `_choices_actions`.
- **Scope**: `cli.py` only.
- **Pros**: only `test` uses the subclass.
- **Cons**: depends on private argparse attributes that differ across Python versions.
- **Risk**: medium.

### 03: Validate in `main` (analysis Option B)

- **Approach**: no subclass; check the rule in `main` and call the `test` parser's `error`.
- **Scope**: `cli.py`, tests.
- **Pros**: no parser subclass.
- **Cons**: `build_parser().parse_args(["test"])` no longer exits 2, which breaks REQ-2's last bullet.
- **Risk**: medium - contradicts the PRD.

### 04: Amend the spec instead of the code

- **Approach**: keep the code as in 01 and correct the plan's wording.
- **Scope**: docs only. This is the documentation side of 01, not an alternative to it.
