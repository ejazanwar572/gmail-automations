# Lessons Learned

## Test Suite Execution
- **Issue:** Duplicate test file names across card subdirectories (`test_run_workflow.py`, `test_sync_alerts.py`) caused pytest collection error `import file mismatch` under default prepend import mode.
- **Rule:** Run pytest with `--import-mode=importlib` and `-o pythonpath=.` (or configure via `pytest.ini`) to cleanly isolate directory modules.

## Architectural Seams & In-Process Pipelines
- **Rule:** Subprocess calls passing files between sibling scripts create state leakage and fragility. Always provide an in-process deep pipeline interface (`run_card_pipeline`) and keep script entry points purely as thin CLI wrappers.

## Mock Interception on Module Imports
- **Rule:** When decomposing monolithic files into shared modules, functions directly patched in unit tests (such as `os.replace` or `_rewrite_exact`) must be invoked in the namespace expected by the test mocks, or tests should patch the canonical module.

## Live Data Testing Smell
- **Rule:** When tests run against live directory state containing synced alerts, assertions on monthly earnings will drift as new transactions occur. Unit tests should either isolate fixtures or use assertions reflecting the invariants of the domain logic.

## Reflex UI & Radix Themes Component Rigor
- **Progress Value Type:** `rx.progress(value=...)` strictly expects an `int` (0-100). Passing a `float` raises a compile-time `TypeError`. Always cast percentage metrics with `int(round(...))` before passing to Progress.
- **Radix Color Scheme Tokens:** Component `color_scheme` properties expect named Radix palette tokens (`amber`, `gold`, `green`, `gray`, `blue`, etc.). Do not pass custom theme gray aliases like `sand` to `color_scheme`.
- **Dynamic Element Props:** Python ternary expressions (`"a" if var else "b"`) evaluate the truthiness of the Reflex `Var` AST wrapper at definition time, which always evaluates to `True`. Always use `rx.cond(var, "a", "b")` for dynamic component props.
- **Theme Configuration in Reflex 0.10+:** `App(theme=...)` is deprecated in Reflex 0.9+. Configure themes via `rx.plugins.RadixThemesPlugin(theme=rx.theme(...))` in `rxconfig.py`.

## Radix Themes Palette Selection (Modern Light Mode vs Dull Sepia)
- **Sand vs Slate:** Setting `gray_color="sand"` produces a brownish/yellow sepia tone across all neutral elements and text scales, making light mode appear washed out and old-fashioned like unbleached newsprint. For modern high-end fintech aesthetics (Apple, Stripe, Linear), always use `gray_color="slate"`.
- **Pure White Cards & Soft Elevation:** Modern light mode requires pure white card backgrounds (`#ffffff`), high-contrast charcoal text (`#0f172a`), thicker progress bars (`size="3"`), and multi-layer soft elevations (`0 1px 3px rgba(15, 23, 42, 0.03), 0 10px 24px -4px rgba(15, 23, 42, 0.05)`) over a luminous `#f8fafc` canvas with ambient top radial lighting.

