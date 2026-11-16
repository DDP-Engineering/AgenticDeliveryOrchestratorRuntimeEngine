# Component: Test infrastructure

## Purpose and source ownership

`04_Software/tests/conftest.py` owns isolated homes and password-hashing fixtures.
`tests/fixture_data.py` caches immutable example configuration text per worker;
the Jobs and Tickets fixture builders write independent copies. The development
dependency and pytest worker defaults live in `04_Software/pyproject.toml` and
its lock file. These helpers are not installed in the application wheel.

## Fixture and authentication boundaries

Each test keeps its own `tmp_path` and `ADORE_HOME`. Neither applications nor
databases, profiles, sessions or credentials are cached across tests.

For tests whose collection already imports `adore.web.store`, an autouse fixture
temporarily replaces only `_HASHER` with a worker-scoped Argon2 `PasswordHasher`
using `time_cost=1`, `memory_cost=1024` KiB and `parallelism=1`. Real hashing,
salt generation, mismatch/corruption exceptions and application authorization
remain active. Pure core tests need not import optional web dependencies just
to execute this fixture. Tests importing the store later can use its unchanged
production hasher instead.

The `real_password_hashing` marker and `--real-password-hashing` option leave the
production hasher untouched. All authentication-module tests carry the marker.
Pytest restores monkeypatches after each case, including after failures.
The application has no test-mode setting or reduced production hashing defaults.
The disposable browser server uses the same inexpensive real Argon2 parameters
before creating fixture accounts. Verification, salts, password changes and
authentication failures stay real; production-cost contracts remain in Python.

## Parallel execution

Pytest uses two xdist workers and `loadfile` scheduling. Each worker collects the
same suite and runs whole assigned files serially, with its own fixtures and
module state. Files may execute concurrently. Thread/process lifecycle assertions
and their bounded waits remain intact; worker grouping does not replace them.

Use `-n 0` for a serial targeted selection, or an explicit worker count to change
parallelism. No Windows/Linux full-suite equivalence is inferred from targeted
verification. Commands and fixture conventions are maintained in
[Code style](../01_Documentation/Code_Style.md#tests-and-component-documentation).

## Platform and browser fixtures

Azure request-file mode assertions apply on POSIX; Windows does not expose ACLs
as POSIX permission bits. Simulated POSIX launchers quote their interpreter path,
including when the fixture itself runs on Windows. Settings metadata expectations
include all four implemented forge adapters.

Manually driven worker fixtures refresh their scoped heartbeats before asserting
capacity reasons. Process-startup time must not silently turn a capacity scenario
into a stale-worker scenario; production heartbeat freshness stays unchanged.

Browser tests use the Chromium revision pinned by the frontend lock file. Install
that revision separately on each host with `npx playwright install chromium`.
For WSL browser runs, `TMPDIR=/dev/shm npx playwright test` can keep disposable
fixture homes and browser scratch in Linux memory, avoiding virtual-disk flush
contention. The environment override applies only to that test command; sources,
compiled assets and test reports remain on the native source filesystem.
The simulated server refreshes worker heartbeats once per second while checking
its durable command queue every 25 ms, avoiding needless heartbeat writes.
Audit and enrollment scenarios restore account preferences in an `afterEach` hook
with its own cleanup budget. Complete wizard journeys have a 60-second test limit;
multi-locale audit journeys use explicit limits. The complete serial browser run
has a 90-minute bound; individual assertion/action limits remain unchanged. Locate synthetic ticket
rows by their evidence rather than relying on server order after client sorting.
Statistics desktop geometry uses a 1440-pixel viewport so native Windows/Linux
font metrics fit the intended single row; narrow-layout checks remain separate.
