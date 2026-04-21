# Coding Conventions

**Analysis Date:** 2026-04-20

## Naming Patterns

**Files:**
- Python modules use `snake_case.py`.
- Test files use `test_*.py` in `tiptop/tests/`.
- Config profiles use descriptive lowercase names with underscores, for example `urinal_cleaning_v1.yml`.

**Functions:**
- `snake_case` for normal functions and async functions alike.
- Entry functions are commonly named `entrypoint()`.
- Helper functions often use a leading underscore for local/private intent, for example `_detect()`, `_segment()`, `_warn_once()`.

**Variables:**
- `snake_case` for locals and parameters.
- Module constants use `UPPER_SNAKE_CASE`, for example `REQUIRED_CUTAMP_VERSION`, `_DEFAULT_GEMINI_MODEL`.
- Private-ish module state often uses `_cached_*` or `_EMITTED_WARNINGS`.

**Types / Classes / Dataclasses:**
- `PascalCase` for classes and dataclasses like `Observation`, `ProcessedScene`, `TiptopPlanningServer`.
- Type aliases/protocols also use `PascalCase`, for example `DepthEstimator`, `Camera`.

## Code Style

**Formatting:**
- The dominant style is Black-like Python formatting with 4-space indentation.
- `tiptop/pyproject.toml` sets Ruff line length to 120.
- Strings are a mix of single and double quotes, with no single enforced quote style apparent.
- Type annotations are used heavily across core modules.

**Linting:**
- Ruff is configured in `tiptop/pyproject.toml`.
- There is no repo-local evidence of a stricter, centralized formatter config beyond Ruff and normal Python tooling.

## Import Organization

**Order:**
1. Standard library imports
2. Third-party package imports
3. Internal `tiptop.*` imports

**Grouping:**
- Imports are separated by blank lines between major groups.
- Multi-item internal imports are often grouped in parentheses for readability.

**Path Strategy:**
- Inside `tiptop/`, imports are package-qualified (`from tiptop.perception...`).
- Cross-repo dependencies to `sam3/` are usually imported dynamically after ensuring the repo root is added to `sys.path`.

## Error Handling

**Patterns:**
- Raise `ValueError` / `RuntimeError` directly for invalid config, unavailable dependencies, or invalid runtime state.
- For expected planning failure, return a result tuple with `failure_reason` instead of throwing, as in `tiptop/tiptop/planning.py`.
- Top-level runners log exceptions and still preserve artifacts where possible.

**Error Types:**
- Custom exceptions are used sparingly, for example `ServerHealthCheckError` and `UserExitException`.
- Health/integration failures generally fail fast before expensive execution begins.

## Logging

**Framework:**
- Standard `logging` module everywhere.
- Logging is configured centrally in `tiptop/tiptop/utils.py`.

**Patterns:**
- Modules define `_log = logging.getLogger(__name__)`.
- Info-level logging is used liberally for stage transitions and external service calls.
- Warning-level logging is used for degraded/fallback behavior, especially in planning and backend selection.
- Per-run file logging is added at runtime for traceability.

## Comments

**When to Comment:**
- Comments mainly explain system intent, geometry conventions, or why a fallback/workaround exists.
- Obvious line-by-line comments are mostly avoided.
- Runtime guidance comments are common in YAML config and docs-facing code.

**Docstrings:**
- Most public functions and many internal helpers have docstrings.
- Module docstrings are commonly used for entry scripts and adapters.

**TODO Comments:**
- TODOs are present but not heavily structured, for example `# TODO: async version of this?` in `tiptop/tiptop/perception_wrapper.py`.

## Function Design

**Size:**
- Small helpers are common, but many orchestration functions are intentionally large because they span a full robotics workflow.
- Complex flows are usually decomposed into nested helpers or adjacent module utilities rather than deeply object-oriented abstractions.

**Parameters:**
- Simple helpers take explicit positional args.
- More complex flows often use dataclasses (`Observation`, `ProcessedScene`) or config globals rather than huge parameter objects.

**Return Values:**
- Structured dict returns are common in perception code.
- Tuples are used when success/failure metadata matters, for example planning returns `(plan, elapsed, failure_reason)`.
- Early returns are used for config/backend branches and no-op conditions.

## Module Design

**Exports:**
- Modules usually expose a few direct functions/classes without barrel files.
- CLI exposure is wired through `[project.scripts]` in `tiptop/pyproject.toml`.

**Pattern Bias:**
- Functional, module-oriented Python rather than service classes everywhere.
- Dataclasses are used for cross-step state bundles.
- Caches and small global state are acceptable when they reduce repeated expensive setup.

---

*Convention analysis: 2026-04-20*
*Update when patterns change*
