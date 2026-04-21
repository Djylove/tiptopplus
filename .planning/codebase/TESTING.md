# Testing Patterns

**Analysis Date:** 2026-04-20

## Test Framework

**Runner:**
- pytest
- Config lives in `tiptop/pyproject.toml`

**Assertion Library:**
- pytest built-in assertions
- Matchers are plain Python `assert` statements plus `pytest.raises` where needed

**Run Commands:**
```bash
cd /home/user/tiptop/tiptop && pytest tests/ -v                # Run default test suite
cd /home/user/tiptop/tiptop && pixi run test-integration       # Run integration-marked tests
cd /home/user/tiptop/tiptop && pytest tests/test_tiptop_h5.py -v
cd /home/user/tiptop/tiptop && pytest tests/test_d435_fast_fs_m2t2_demo.py -v
```

## Test File Organization

**Location:**
- Tests live in a dedicated `tiptop/tests/` tree rather than beside source files.

**Naming:**
- `test_*.py` naming throughout.
- Current files include:
  - `tiptop/tests/test_d435_fast_fs_m2t2_demo.py`
  - `tiptop/tests/test_tiptop_h5.py`
  - `tiptop/tests/test_urinal_localization.py`
  - `tiptop/tests/test_urinal_validation.py`
  - `tiptop/tests/test_urinal_zones.py`

**Structure:**
```text
tiptop/tests/
├── conftest.py
├── test_d435_fast_fs_m2t2_demo.py
├── test_tiptop_h5.py
├── test_urinal_localization.py
├── test_urinal_validation.py
└── test_urinal_zones.py
```

## Test Structure

**Suite Organization:**
- Most tests are plain function-based pytest tests.
- Parametrization is used for scene sweeps, for example in `tiptop/tests/test_tiptop_h5.py`.
- Tests usually follow arrange/act/assert informally without explicit comments.

**Patterns:**
- Focused helper/unit tests exist for visualization and target-mask logic in `test_d435_fast_fs_m2t2_demo.py`.
- Integration-style tests directly call real application entry functions rather than testing thin wrappers.
- Shared fixture setup is centralized in `tiptop/tests/conftest.py`.

## Mocking

**Framework:**
- There is little visible framework-heavy mocking in the current suite.
- A common pattern is passing fake callables or synthetic numpy arrays into pure helpers rather than monkeypatching large subsystems.

**Patterns:**
- `test_d435_fast_fs_m2t2_demo.py` passes fake SAM3 candidate detectors directly into helper functions.
- Tests favor deterministic local data over runtime service mocking.

**What to Mock / Stub:**
- External service responses should be replaced with injected fake callables where possible.
- Camera frames, masks, intrinsics, and point sets are represented as small synthetic numpy arrays.

**What NOT to Mock:**
- Pure geometry/selection helpers are tested directly.
- Offline H5 integration intentionally exercises real pipeline code with packaged assets.

## Fixtures and Factories

**Test Data:**
- Shared asset bootstrap lives in `tiptop/tests/conftest.py`.
- H5 integration assets are downloaded from Google Drive on demand and cached locally.
- Small unit tests create inline numpy arrays instead of using large fixture files.

**Location:**
- Session fixtures: `tiptop/tests/conftest.py`
- Downloaded assets: `tiptop/tests/assets/`

## Coverage

**Requirements:**
- No explicit numeric coverage target was found.
- Coverage appears to be pragmatic and scenario-driven rather than enforced by CI gates.

**Configuration:**
- The repo defines an `integration` pytest marker in `tiptop/pyproject.toml`.
- There is no visible separate coverage config file.

## Test Types

**Unit Tests:**
- Strongest current unit coverage is around the D435/Fast-FoundationStereo/M2T2 demo helper logic.
- The urinal subsystem also has focused logic tests.

**Integration Tests:**
- `tiptop/tests/test_tiptop_h5.py` is the main integration path, exercising offline TiPToP planning from H5 observations.
- This path expects live-compatible planning dependencies and packaged H5 assets.

**Hardware / Service Validation:**
- Many important validations are documented as manual bring-up flows in `tiptop/docs/development-build.md` and `tiptop/docs/troubleshooting.md`, not formal automated tests.

## Common Patterns

**Async / Deferred Systems:**
- Rather than deeply async-testing coroutines in isolation, the suite often calls sync wrappers or high-level entrypoints.

**Error / Fallback Testing:**
- The demo helper tests cover fallback selection logic, ROI fallbacks, and mask-choice heuristics.
- Planning fallback behavior exists in code, but no direct dedicated regression test for it was found.

**Snapshot Testing:**
- Not used.

## Test Coverage Gaps

**Notably weak or absent:**
- No dedicated tests were found for `tiptop/tiptop/perception/sam3.py`.
- No dedicated tests were found for `tiptop/tiptop/perception/foundation_stereo.py` or `tiptop/tiptop/perception/m2t2.py` client behavior.
- No tests were found for the websocket server in `tiptop/tiptop/tiptop_websocket_server.py`.
- Real hardware health checks and multi-repo service composition still rely heavily on manual validation.

---

*Testing analysis: 2026-04-20*
*Update when test patterns change*
