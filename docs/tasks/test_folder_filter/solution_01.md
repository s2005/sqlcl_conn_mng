# Solution 01: One Subparser Class, Opt-In Rule Check

## Chosen approach

`add_subparsers(parser_class=_TestSelectorParser)` makes every subcommand parser a `_TestSelectorParser`. The selector rule runs only when the parser was built with `test_selector=True`, which only the `test` command passes (`src/sqlcl_conn_mng/cli.py:304`). `_global_options` builds its parent parser with the same class so mypy accepts `parents=[...]` (`cli.py:133-135`).

## Why not the others

- **02** works only through private argparse attributes (`_name_parser_map`, `_choices_actions`), which can change between Python versions. Solution 01 uses public API only.
- **03** breaks REQ-2: usage errors must be raised during argument parsing, so `build_parser().parse_args(["test"])` exits 2.
- **04** is not an alternative. It records solution 01 in the plan.

## Drifts resolved

D-1.

## Files changed

- `src/sqlcl_conn_mng/cli.py` (commit 8dc1ded)

## Implementation outline

1. `_TestSelectorParser.__init__` takes `test_selector: bool = False` and stores it.
2. `parse_known_args` returns early unless `test_selector` is set, then applies the REQ-2 rule with `self.error` (exit 2).
3. `build_parser` passes `parser_class=_TestSelectorParser` to `add_subparsers`, and `test_selector=True` to the `test` `add_parser` call.

## Verification

- `test_test_selector_rules` and `test_test_selector_rules_through_main` pass (exit 2 from `parse_args` and `main`).
- `test_selector_requires_exactly_one` passes unchanged for `show`, `delete`, `move`.
- `make check` and `make unit` are clean.
