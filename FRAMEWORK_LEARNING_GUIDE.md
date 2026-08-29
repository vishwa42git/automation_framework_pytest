# Automation Framework Learning Guide - Interview Ready

**Date:** August 29, 2026  
**Topic:** Error Handling Layer Design & Framework Architecture  
**Prepared For:** Team Learning & Knowledge Transfer

---

## Table of Contents

1. [Error Handling Layer Overview](#1-error-handling-layer-overview)
2. [Stack Trace Handling](#2-stack-trace-handling)
3. [Framework Architecture Deep Dive](#3-framework-architecture-deep-dive)
4. [Hooks vs Regular Functions](#4-hooks-vs-regular-functions)
5. [Logger.py vs Logging_config.py](#5-loggerpy-vs-logging_configpy)
6. [Pytest Hooks Reference](#6-pytest-hooks-reference)

---

## 1. Error Handling Layer Overview

### 1.1 Why We Need an Error Handling Layer

Your current framework has **minimal error handling**. The `ApiClient` does:

```python
response.raise_for_status()  # Generic HTTP exception
```

**Problems:**
- No context about what failed
- Can't distinguish network vs. config vs. timeout errors
- No retry logic for flaky network
- Same handling for all error types

### 1.2 Four Pillars of Error Handling Design

#### **Pillar 1: Custom Exception Hierarchy**

Structure errors in layers (like a pyramid):

```
BaseFrameworkError (root)
├── ConfigurationError (invalid settings, missing env vars)
├── ConnectionError (network, SSH, timeout)
├── ProtocolError (NFS, CIFS, iSCSI specific failures)
├── ValidationError (assertion/data validation)
└── TestError (test setup/teardown failures)
```

**Why this matters:**
- Each exception type can be caught specifically
- Different exceptions = different handling strategies
- Logging can route errors differently

**Design Questions:**
- Should a network timeout retry automatically or fail immediately?
- Should a config error ever be retried?
- Which errors should stop the entire test suite vs. just one test?

#### **Pillar 2: Error Context & Information**

Errors need **actionable details**, not just the message:

```python
# BAD: Generic
raise ConnectionError("Connection failed")

# GOOD: Rich context
raise ConnectionError(
    message="Failed to connect to NFS server",
    host="192.168.1.100",
    port=2049,
    reason="Timeout after 30s",
    retry_attempt=2,
    is_recoverable=True
)
```

**Design Questions:**
- What info do QA engineers need to debug failures?
- Should errors include suggestion for remediation?
- Should errors track attempt counts for retries?

#### **Pillar 3: Retry & Recovery Strategies**

Different errors need different responses:

```
Network error → Retry (exponential backoff)
Config error → Fail immediately (no retry)
Timeout → Retry with longer timeout
Auth error → Fail after 1 attempt (prevent lockout)
Protocol error → Log & fail (need investigation)
```

**Design Questions:**
- How many retries before giving up?
- Should retry delay increase each time (backoff)?
- Should some errors bypass retry completely?
- Should retry logic be centralized or per-client?

#### **Pillar 4: Error Reporting & Logging**

Errors must flow through your logging system:

```
Exception raised → Logged with full context → Test result recorded → Report generated
```

**Design Questions:**
- Should errors auto-log or require explicit logging?
- What log level? (ERROR, CRITICAL, WARNING?)
- Should error context be added to log records?
- Should stack trace be included?

### 1.3 Architecture Pattern for Your Framework

```
lib/
├── exceptions.py          ← Custom exception classes
├── error_handler.py       ← Central error handling logic
└── retry_strategy.py      ← Retry/recovery rules

framework/
├── api_client.py          ← Catches & wraps exceptions
├── config.py              ← Validates config, raises ConfigError
└── decorators.py          ← @retry, @handle_error decorators

tests/
└── test_*.py              ← Uses exceptions to assert failures
```

### 1.4 Learning Path for Error Handling

**Phase 1 — Foundations (understand first)**
1. Define custom exception hierarchy
2. Design exception signature
3. Document the decision

**Phase 2 — Core Implementation**
4. Create `lib/exceptions.py` with exception classes
5. Add error context class
6. Integrate with your existing `ApiClient`

**Phase 3 — Enhancement**
7. Create retry strategies (`lib/retry_strategy.py`)
8. Add decorators for automatic retry
9. Integrate with logging

**Phase 4 — Testing**
10. Write tests that verify exceptions are raised correctly
11. Test retry logic
12. Test logging captures errors

---

## 2. Stack Trace Handling

### 2.1 Important Clarification: Two Separate Concepts

**Concept 1: pytest handling stack traces (built-in)**
```python
# pytest catches unhandled exceptions automatically
# Shows stack trace in test failure report
# This is automatic - nothing you need to do
```

**Concept 2: `exc_info=True` in logging (Python logging feature)**
```python
# This is NOT a pytest feature
# It's a Python logging feature
# Tells logging to capture and include stack trace in log file
```

### 2.2 Stack Trace Flow in Your Framework

```
┌─ REQUEST LAYER ──────────────────────────────────┐
│  api_client.py: response.raise_for_status()      │
│                    ↓ (exception raised here)      │
│            Stack trace: Line 22                   │
│                    ↓                              │
└────────────────────────────────────────────────────┘
                     ↓ (caught here)

┌─ ERROR HANDLING LAYER ───────────────────────────┐
│  lib/error_handler.py (CAPTURES & WRAPS)         │
│                                                    │
│  try:                                            │
│      response.raise_for_status()                 │
│  except requests.HTTPError as e:  ◄── Raw error │
│      ┌─ STACK TRACE #1 ──────────────────────┐  │
│      │ (from requests library)               │  │
│      │ File "api_client.py", line 22         │  │
│      │ File "requests/models.py", line ...   │  │
│      └──────────────────────────────────────┘   │
│                                                    │
│      # Wrap with context + preserve trace       │
│      raise ProtocolError(                        │
│          message="API failed",                   │
│          status_code=response.status_code,       │
│          url=url,                                │
│          original_error=str(e)                   │
│      ) from e  ◄── PRESERVES chain!             │
│                                                    │
│      ┌─ STACK TRACE #2 ──────────────────────┐  │
│      │ (framework's ProtocolError)           │  │
│      │ File "error_handler.py", line X       │  │
│      │ CAUSED BY: HTTPError [trace #1]       │  │
│      └──────────────────────────────────────┘   │
└────────────────────────────────────────────────────┘
                     ↓ (logged here)

┌─ LOGGING LAYER ──────────────────────────────────┐
│  lib/logging_config.py (CAPTURES FULL TRACE)    │
│                                                    │
│  logger.error(                                   │
│      "API call failed: %s",                      │
│      exc_info=True  ◄── Enables stack trace!   │
│  )                                               │
│                                                    │
│  Log file receives:                             │
│  ┌──────────────────────────────────────────┐  │
│  │ ERROR lib.error_handler: API call failed │  │
│  │ Traceback (most recent call last):       │  │
│  │   File "api_client.py", line 22, in ... │  │
│  │     response.raise_for_status()          │  │
│  │   File "requests/models.py", line ...    │  │
│  │     ...                                   │  │
│  │ ProtocolError: ...                       │  │
│  └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
                     ↓ (test reports here)

┌─ TEST RESULTS ───────────────────────────────────┐
│  pytest report (SHOWS TRACE TO QA)              │
│                                                    │
│  test_api_client.py::test_get_users FAILED       │
│                                                    │
│  ProtocolError: API call failed                  │
│  Traceback (most recent call last):              │
│    File "api_client.py", line 22, ...            │
│  .... <full stack trace shown>                   │
└────────────────────────────────────────────────────┘
```

### 2.3 What is `exc_info=True`?

```python
import logging

logger = logging.getLogger(__name__)

# Scenario 1: WITHOUT exc_info
try:
    result = 10 / 0
except ZeroDivisionError as e:
    logger.error("Math failed: %s", e)
    # ❌ Log shows: "Math failed: division by zero"
    # ❌ NO stack trace in log file


# Scenario 2: WITH exc_info=True
try:
    result = 10 / 0
except ZeroDivisionError as e:
    logger.error("Math failed: %s", e, exc_info=True)
    # ✅ Log shows:
    #    "Math failed: division by zero"
    #    Traceback (most recent call last):
    #      File "...", line 5, in <module>
    #        result = 10 / 0
    #    ZeroDivisionError: division by zero
```

### 2.4 Stack Trace Preservation with `from e`

This is **critical** to understand:

```python
# ❌ BAD: Stack trace chain is broken
try:
    response.raise_for_status()
except requests.HTTPError as e:
    raise ProtocolError("API failed")  # ← Old trace is LOST


# ✅ GOOD: Stack trace chain is preserved
try:
    response.raise_for_status()
except requests.HTTPError as e:
    raise ProtocolError("API failed") from e  # ← Uses 'from e'
    #                                          ↑
    #                    Preserves exception chain!
```

When you use `from e`, Python creates an **exception chain**:
- Original exception (HTTPError) with its stack trace
- New exception (ProtocolError) with its stack trace
- Both shown together in logs/reports

### 2.5 Key Takeaway About Stack Traces

Stack traces in your framework are handled by:
- ✅ **pytest** - automatically shows traces in test failure reports
- ✅ **Python logging** - with `exc_info=True` captures traces in log files
- ✅ **Exception chaining** - `from e` preserves original traces
- ❌ **NOT explicitly by you** - it's automatic infrastructure

---

## 3. Framework Architecture Deep Dive

### 3.1 Current Framework Structure

```
automation_framework_pytest/
├── framework/
│   ├── __init__.py
│   ├── api_client.py       ← Business logic (API calls)
│   └── config.py           ← Settings management
├── lib/
│   ├── __init__.py
│   ├── logger.py           ← Logger access
│   └── logging_config.py   ← Logging setup
├── tests/
│   ├── __init__.py
│   └── test_api_client.py  ← Test cases
├── conftest.py             ← pytest hooks & fixtures
├── pyproject.toml
└── README.md
```

### 3.2 Complete Execution Flow - Layer by Layer

#### **Entry Point: Running Tests**

```
$ pytest tests/test_api_client.py
```

#### **Phase 1: pytest Startup (BEFORE any test runs)**

```
┌─ STEP 1: pytest discovers conftest.py ────────────────────────┐
│ pytest loads conftest.py                                       │
│ Reads: pytest_configure() hook                                │
│ Reads: settings fixture                                        │
│ Reads: api_client fixture                                     │
│ (These are NOT called yet, just registered)                   │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ↓
┌─ STEP 2: pytest_configure() HOOK called ──────────────────────┐
│ Time: Before any test runs                                    │
│ Location: conftest.py, line 8                                 │
│                                                               │
│ def pytest_configure(config: pytest.Config):                 │
│     configure_logging(config.getoption("--log-level"))       │
│                                                               │
│ What happens:                                                │
│ ├─ calls: lib/logging_config.py → configure_logging()       │
│ │  ├─ Creates: logs/ directory                              │
│ │  ├─ Generates: logs/test_20260829_143022_12345.log        │
│ │  ├─ Sets: RotatingFileHandler                             │
│ │  ├─ Sets: LOG_FORMAT, DATE_FORMAT                         │
│ │  └─ Adds to: root logger                                  │
│ │                                                            │
│ └─ Result: Global logging system is NOW READY              │
│    (All subsequent code can use get_logger())               │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ↓
┌─ STEP 3: pytest discovers test functions ─────────────────────┐
│ pytest scans: tests/test_api_client.py                        │
│ Finds: test_get_users_from_public_api()                       │
│                                                               │
│ Analysis: This test requires:                                │
│ └─ api_client (fixture parameter)                            │
│    └─ api_client requires: settings (fixture parameter)      │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ↓
┌─ STEP 4: pytest registering fixtures ──────────────────────────┐
│ conftest.py, line 12-15:                                      │
│                                                               │
│ @pytest.fixture(scope="session")                             │
│ def settings() -> Settings:                                  │
│     return Settings.from_environment()                       │
│                                                               │
│ conftest.py, line 18-20:                                      │
│                                                               │
│ @pytest.fixture                                              │
│ def api_client(settings: Settings) -> ApiClient:             │
│     return ApiClient(settings)                               │
│                                                               │
│ Note: Fixtures are registered, NOT created yet               │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ↓
              Logging ready ✓
              Fixtures registered ✓
              Ready to create fixtures ✓
```

#### **Phase 2: First Test - Fixture Creation**

```
┌─ STEP 5: Create session-scoped fixture ────────────────────────┐
│ Time: Once per test session                                   │
│ conftest.py, line 12-15:                                      │
│                                                               │
│ @pytest.fixture(scope="session")                             │
│ def settings() -> Settings:                                  │
│     return Settings.from_environment()                       │
│                                                               │
│ Execution:                                                   │
│ ├─ calls: framework/config.py → Settings.from_environment() │
│ │  ├─ reads: API_BASE_URL env var                           │
│ │  │  └─ or default: "https://jsonplaceholder.typicode..."  │
│ │  ├─ reads: API_TIMEOUT env var                            │
│ │  │  └─ or default: 10.0                                   │
│ │  └─ returns: Settings(base_url=..., timeout=...)          │
│ │                                                            │
│ └─ Result: settings object created (stored in memory)       │
│    Reused for ALL tests in this session                     │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ↓
┌─ STEP 6: Create function-scoped fixture ──────────────────────┐
│ Time: Just before test runs (created fresh for each test)    │
│ conftest.py, line 18-20:                                      │
│                                                               │
│ @pytest.fixture                                              │
│ def api_client(settings: Settings) -> ApiClient:             │
│     return ApiClient(settings)                               │
│                                                               │
│ Execution:                                                   │
│ ├─ receives: settings object (from session fixture above)   │
│ ├─ calls: framework/api_client.py → ApiClient.__init__()   │
│ │  ├─ stores: self.settings = settings                      │
│ │  └─ creates: self.session = requests.Session()            │
│ │                                                            │
│ └─ Result: Fresh ApiClient instance for this test           │
│    (discarded after test completes)                         │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ↓
              settings fixture ✓ (ready)
              api_client fixture ✓ (ready)
              All fixtures prepared ✓
```

#### **Phase 3: Test Execution**

```
┌─ STEP 7: Test function called ────────────────────────────────┐
│ Time: Now                                                     │
│ tests/test_api_client.py, line 6:                            │
│                                                               │
│ def test_get_users_from_public_api(api_client):              │
│     # Receives: api_client fixture (fresh instance)          │
│                                                               │
│     response = api_client.get("/users")                      │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ↓
┌─ STEP 7a: Entering api_client.get() ──────────────────────────┐
│ Location: framework/api_client.py, line 26                   │
│                                                               │
│ def get(self, path: str, **kwargs: Any):                     │
│     return self.request("GET", path, **kwargs)               │
│     └─ delegates to request() method                         │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ↓
┌─ STEP 7b: Entering api_client.request() ──────────────────────┐
│ Location: framework/api_client.py, line 16-24                │
│                                                               │
│ def request(self, method: str, path: str, **kwargs):         │
│                                                               │
│ STEP 1: Build URL (line 17)                                 │
│ ├─ url = "https://jsonplaceholder.typicode.com/users"       │
│                                                               │
│ STEP 2: Set default timeout (line 18)                       │
│ ├─ kwargs["timeout"] = self.settings.timeout (10.0)         │
│                                                               │
│ STEP 3: Log request (line 19)                               │
│ ├─ get_logger(__name__)                                      │
│ │  └─ Calls: lib/logger.py → get_logger()                   │
│ │     ├─ Input: __name__ = "framework.api_client"           │
│ │     └─ Returns: logging.Logger                             │
│ │        (Already configured by pytest_configure hook)      │
│ │                                                            │
│ ├─ logger.info("Sending GET request to ...")                │
│ │  └─ Writes to: logs/test_20260829_143022_12345.log        │
│ │     Format: "[2026-08-29 14:30:22] [INFO] framework.api... │
│ │             Sending GET request to https://..."            │
│ │                                                            │
│ STEP 4: Make HTTP request (line 21)                         │
│ ├─ response = self.session.request("GET", url, ...)         │
│ │  └─ Uses: requests library (external)                     │
│ │     └─ Makes actual HTTP call to jsonplaceholder API      │
│ │     └─ Returns: requests.Response object (status=200)     │
│ │                                                            │
│ STEP 5: Log response (line 22)                              │
│ ├─ logger.info("Received 200 response from ...")            │
│ │  └─ Writes to: logs/test_20260829_143022_12345.log        │
│ │                                                            │
│ STEP 6: Check for errors (line 23)                          │
│ ├─ response.raise_for_status()                              │
│ │  └─ If status >= 400: raise HTTPError                     │
│ │  └─ If status < 400: Do nothing (method continues)        │
│ │  └─ In this case: Status 200, no error                    │
│ │                                                            │
│ STEP 7: Return response (line 24)                           │
│ └─ return response                                           │
│    └─ Back to test: response object ready for assertions     │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ↓
┌─ STEP 8: Test continues with assertions ──────────────────────┐
│ tests/test_api_client.py, lines 9-15:                        │
│                                                               │
│ assert response.status_code == 200                           │
│ ├─ Passes ✓                                                  │
│                                                               │
│ users = response.json()                                      │
│ ├─ Parses JSON: [{"id": 1, "name": "...", "email": "..."}...│
│                                                               │
│ logger.info("GET /users response body: %s", users)           │
│ ├─ Calls: lib/logger.py → get_logger(__name__)              │
│ ├─ Writes to: logs/test_20260829_143022_12345.log           │
│                                                               │
│ assert isinstance(users, list)                               │
│ ├─ Passes ✓                                                  │
│                                                               │
│ assert users                                                 │
│ ├─ Passes ✓ (list is not empty)                             │
│                                                               │
│ assert {"id", "name", "email"}.issubset(users[0])           │
│ ├─ Passes ✓ (all keys present in first item)                │
│                                                               │
│ ALL ASSERTIONS PASSED → TEST PASSED ✓                        │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ↓
┌─ STEP 9: Fixture cleanup ─────────────────────────────────────┐
│ After test completes:                                        │
│                                                               │
│ api_client fixture (scope="function"):                       │
│ └─ DISCARDED (not used for next test)                       │
│    (Next test will create a fresh api_client)               │
│                                                               │
│ settings fixture (scope="session"):                          │
│ └─ KEPT (reused for all remaining tests)                    │
│    (No need to reload environment)                          │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ↓
┌─ STEP 10: Test results ───────────────────────────────────────┐
│ pytest records:                                              │
│ tests/test_api_client.py::test_get_users_from_public_api    │
│ PASSED ✓                                                     │
│                                                               │
│ Log file contains:                                          │
│ [2026-08-29 14:30:22] [INFO] framework.api_client          │
│ Sending GET request to https://jsonplaceholder.typicode.../users
│ [2026-08-29 14:30:23] [INFO] framework.api_client          │
│ Received 200 response from https://jsonplaceholder.typicode.../users
│ [2026-08-29 14:30:23] [INFO] tests.test_api_client        │
│ GET /users response body: [{"id": 1, "name": "...", ...}, ...]
└───────────────────────────────────────────────────────────────┘
```

### 3.3 File Connection Map

```
conftest.py (ENTRY POINT - Contains Hooks & Fixtures)
    │
    ├─ IMPORTS:
    │  ├─ pytest
    │  ├─ framework.api_client.ApiClient
    │  ├─ framework.config.Settings
    │  └─ lib.logging_config.configure_logging
    │
    ├─ HOOK: pytest_configure()
    │  └─ CALLS: lib/logging_config.py → configure_logging()
    │     └─ Setup logging for entire test run
    │
    ├─ FIXTURE (scope="session"): settings()
    │  └─ CALLS: framework/config.py → Settings.from_environment()
    │     └─ Load configuration once per session
    │
    └─ FIXTURE (scope="function"): api_client(settings)
       └─ CALLS: framework/api_client.py → ApiClient(settings)
          └─ Create fresh client for each test


framework/api_client.py (BUSINESS LOGIC LAYER)
    │
    ├─ IMPORTS:
    │  ├─ framework.config.Settings
    │  └─ lib.logger.get_logger
    │
    ├─ CLASS: ApiClient
    │  ├─ __init__(settings: Settings)
    │  │  ├─ Stores: self.settings = settings
    │  │  └─ Creates: self.session = requests.Session()
    │  │
    │  ├─ METHOD: request(method, path, **kwargs)
    │  │  ├─ CALLS: get_logger(__name__)
    │  │  │  └─ Get logger for this module
    │  │  ├─ CALLS: logger.info() (twice)
    │  │  │  └─ Log request & response
    │  │  ├─ CALLS: self.session.request()
    │  │  │  └─ Make HTTP call
    │  │  └─ CALLS: response.raise_for_status()
    │  │     └─ Check for HTTP errors
    │  │
    │  └─ METHOD: get(path, **kwargs)
    │     └─ CALLS: self.request("GET", path, **kwargs)


framework/config.py (CONFIGURATION LAYER)
    │
    ├─ CLASS: Settings
    │  ├─ Attributes: base_url, timeout
    │  │
    │  └─ CLASS METHOD: from_environment()
    │     ├─ Reads: os.getenv("API_BASE_URL", ...)
    │     ├─ Reads: os.getenv("API_TIMEOUT", ...)
    │     └─ Returns: Settings object


lib/logger.py (LOGGING ACCESS LAYER)
    │
    └─ FUNCTION: get_logger(name: str)
       └─ RETURNS: logging.getLogger(name)
          (Already configured by pytest_configure)


lib/logging_config.py (LOGGING SETUP LAYER)
    │
    ├─ FUNCTION: _get_log_file()
    │  ├─ Creates: logs/ directory
    │  └─ Generates: logs/test_TIMESTAMP_PID.log
    │
    └─ FUNCTION: configure_logging(log_level)
       ├─ Gets: root logger
       ├─ Sets: log level from env var or parameter
       ├─ Creates: RotatingFileHandler
       ├─ Sets: Formatter with LOG_FORMAT
       └─ Adds handler to root logger


tests/test_api_client.py (TEST LAYER)
    │
    ├─ IMPORTS:
    │  └─ lib.logger.get_logger
    │
    └─ FUNCTION: test_get_users_from_public_api(api_client)
       ├─ RECEIVES: api_client fixture (injected by pytest)
       ├─ CALLS: api_client.get("/users")
       │  └─ Makes API call
       ├─ CALLS: get_logger(__name__)
       │  └─ Get logger for this test module
       ├─ CALLS: logger.info()
       │  └─ Log test results
       └─ ASSERTIONS: Check response, verify data
```

### 3.4 Data Flow Example: Single API Call

```
Simplified Data Flow:

conftest.py (starts)
    │
    ├─ pytest_configure()
    │  └─ configure_logging() sets up logging ✓
    │
    ├─ settings fixture created
    │  └─ Settings object ready ✓
    │
    └─ api_client fixture created
       ├─ receives settings
       └─ ApiClient object ready ✓
           │
           └─ test_get_users_from_public_api(api_client)
              │
              ├─ api_client.get("/users")
              │  │
              │  └─ api_client.request("GET", "/users")
              │     │
              │     ├─ get_logger("framework.api_client")
              │     │  └─ Returns logger (already configured)
              │     │
              │     ├─ logger.info("Sending...")
              │     │  └─ logs/test_...log ← wrote here
              │     │
              │     ├─ requests.Session.request()
              │     │  └─ HTTP call returns response (status=200)
              │     │
              │     ├─ logger.info("Received 200...")
              │     │  └─ logs/test_...log ← wrote here
              │     │
              │     ├─ response.raise_for_status()
              │     │  └─ No error (status 200)
              │     │
              │     └─ return response
              │
              ├─ assert response.status_code == 200 ✓
              ├─ users = response.json()
              ├─ logger.info("GET /users response...")
              │  └─ logs/test_...log ← wrote here
              ├─ More assertions ✓
              │
              └─ Test PASSED ✓
```

### 3.5 Layer Responsibilities Summary

| Layer | Responsibility | Files | Called By |
|-------|-----------------|-------|-----------|
| **Configuration** | Store settings | config.py | fixtures, api_client |
| **Logging Setup** | Configure logging system | logging_config.py | pytest hook |
| **Logging Access** | Provide logger objects | logger.py | all modules |
| **Business Logic** | Make API requests | api_client.py | fixtures, tests |
| **Tests** | Run test cases | test_*.py | pytest |
| **Fixtures** | Setup test data | conftest.py | tests |
| **Hooks** | pytest lifecycle | conftest.py | pytest |

---

## 4. Hooks vs Regular Functions

### 4.1 What is a "Hook"?

A **hook** is a special function that pytest calls **automatically** at specific points in the test lifecycle. You don't call them yourself.

```python
# ❌ REGULAR FUNCTION
def calculate_sum(a, b):
    return a + b

# You must call it explicitly:
result = calculate_sum(5, 3)


# ✅ HOOK FUNCTION
def pytest_configure(config):
    print("Test run starting!")
    # pytest calls this automatically
    # YOU never call pytest_configure() in your code
```

### 4.2 How to Identify a Hook

```python
# HOOKS always start with "pytest_"
pytest_configure()        ← Hook
pytest_collection()       ← Hook
pytest_runtest_setup()    ← Hook
pytest_runtest_teardown() ← Hook
pytest_sessionstart()     ← Hook
pytest_sessionfinish()    ← Hook

# Regular functions
get_logger()              ← NOT a hook
configure_logging()       ← NOT a hook
from_environment()        ← NOT a hook
```

### 4.3 Hook Timing in Your Framework

```
Timeline of a pytest run:
─────────────────────────────────────────────────────

PHASE 1: PYTEST STARTUP
├─ pytest_configure() called          ← HOOK ✅
│  └─ configure_logging() called      ← YOU call this (not a hook)
│
├─ fixtures are registered
│  ├─ @pytest.fixture(scope="session")
│  │  def settings()                  ← Regular function + decorator
│  │
│  └─ @pytest.fixture(scope="function")
│     def api_client()                ← Regular function + decorator
│
└─ test functions discovered

PHASE 2: TEST COLLECTION
├─ pytest_collection() called         ← HOOK ✅
│  └─ Tests collected into list
└─ pytest collects all test_*.py files

PHASE 3: TEST SESSION STARTS
├─ pytest_sessionstart() called       ← HOOK ✅
├─ Session fixtures created (if any)
└─ Logging is now ready to use

PHASE 4: FIRST TEST RUNS
├─ pytest_runtest_setup() called      ← HOOK ✅
├─ Session fixtures loaded (settings)
├─ Function fixtures created (api_client)
├─ test_get_users_from_public_api() runs
└─ pytest_runtest_teardown() called   ← HOOK ✅

PHASE 5: MORE TESTS RUN
└─ ... (repeat Phase 4 for each test)

PHASE 6: TEST SESSION ENDS
├─ pytest_sessionfinish() called      ← HOOK ✅
└─ Test results reported
```

### 4.4 Visual: Hooks vs Fixtures Timeline

```
Test Session Start
    │
    ├─ pytest_configure() HOOK
    │  └─ Logging setup (your code)
    │
    ├─ pytest_sessionstart() HOOK
    │  └─ Global setup
    │
    ├─ pytest_collection() HOOK
    │  └─ Find all tests
    │
    ├─ Fixtures registered
    │  └─ settings (session scope)
    │  └─ api_client (function scope)
    │
    └─ First Test Starts
       │
       ├─ pytest_runtest_setup() HOOK
       │  └─ Generic setup for any test
       │
       ├─ FIXTURES CREATED (for this test)
       │  ├─ settings (from session, already exists)
       │  └─ api_client (NEW for this test)
       │
       ├─ TEST FUNCTION RUNS
       │  ├─ Receives: api_client fixture
       │  └─ Uses it
       │
       ├─ pytest_runtest_teardown() HOOK
       │  └─ Generic teardown
       │
       └─ FIXTURE CLEANUP
          └─ api_client discarded (function scope)
             settings kept (session scope)
```

### 4.5 Key Differences: Hooks vs Regular Functions vs Fixtures

```python
# HOOKS: pytest_* functions
# ═════════════════════════════════════════════
def pytest_configure(config):
    """HOOK: Called automatically by pytest"""
    print("Test session starting!")
    # pytest calls this for you

def pytest_runtest_setup():
    """HOOK: Called before each test"""
    print("Test is about to run")
    # pytest calls this for you


# FIXTURES: @pytest.fixture decorated functions
# ═════════════════════════════════════════════
@pytest.fixture(scope="session")
def settings():
    """FIXTURE: Injected into tests when needed"""
    return Settings.from_environment()
    # pytest injects this into test parameters

@pytest.fixture
def api_client(settings):
    """FIXTURE: Injected into tests"""
    return ApiClient(settings)
    # pytest injects this into test parameters


# REGULAR FUNCTIONS: Any other function
# ═════════════════════════════════════════════
def calculate_sum(a, b):
    """REGULAR: You must call it"""
    return a + b
    # You call: result = calculate_sum(5, 3)


# THE DIFFERENCE:
Hooks:
├─ Called automatically at lifecycle points
├─ NOT injected into tests
├─ Global scope (apply to all tests)
└─ Examples: pytest_configure, pytest_runtest_setup

Fixtures:
├─ Called when needed by test functions
├─ Injected as test parameters
├─ Can have different scopes (session, function, module)
└─ Examples: settings, api_client, database connection

Regular Functions:
├─ Called explicitly by other functions
├─ NOT automatic
├─ Local scope (only where called)
└─ Examples: get_logger, configure_logging, calculate_sum
```

### 4.6 Difference Table

| Aspect | Hook (`pytest_configure`) | Fixture (`@pytest.fixture`) | Regular Function |
|--------|--------------------------|---------------------------|-----------------|
| **Calling** | pytest calls automatically | pytest injects into tests | YOU call it |
| **Naming** | Starts with `pytest_` | Any name with decorator | Any name |
| **Timing** | Specific lifecycle points | When test needs it | On demand |
| **Frequency** | Once per phase | Per test (or per session) | On demand |
| **Purpose** | Global setup/initialization | Test data/setup | Utility/logic |
| **Examples** | Logging, plugins | Database, fixtures | Logger, config |
| **In conftest** | YES | YES | Rarely |
| **Scope** | Global (all tests) | Configurable | Where called |

---

## 5. Logger.py vs Logging_config.py

### 5.1 The Difference

These are **two different responsibilities** that work together:

```
┌──────────────────────────────────────────────────────┐
│              LOGGING SYSTEM                          │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │  logging_config.py (SETUP/CONFIGURATION)      │ │
│  │                                                 │ │
│  │  Job: SETUP the logging system                │ │
│  │  ├─ Create log file                           │ │
│  │  ├─ Set log level                             │ │
│  │  ├─ Add file handler                          │ │
│  │  ├─ Set format                                │ │
│  │  └─ Configure root logger                     │ │
│  │                                                 │ │
│  │  Called ONCE at start (pytest_configure)     │ │
│  │  Never called again during test run          │ │
│  └────────────────────────────────────────────────┘ │
│                      ↓                               │
│           (Logging is now configured)               │
│                      ↓                               │
│  ┌────────────────────────────────────────────────┐ │
│  │  logger.py (ACCESS/USAGE)                      │ │
│  │                                                 │ │
│  │  Job: GET a logger for use                    │ │
│  │  ├─ Takes: name parameter                     │ │
│  │  └─ Returns: configured logger object         │ │
│  │                                                 │ │
│  │  Called MANY times (every module that needs  │ │
│  │  to log something)                            │ │
│  │                                                 │ │
│  │  Example calls:                                │ │
│  │  ├─ logger = get_logger("framework.api_client")
│  │  ├─ logger = get_logger(__name__)             │ │
│  │  └─ logger = get_logger("tests.test_api")     │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 5.2 Code Comparison

```python
# logging_config.py (Setup - called ONCE)
# ═══════════════════════════════════════════════════
import logging
from logging.handlers import RotatingFileHandler

def configure_logging(log_level: str | None = None):
    """SETUP: Configure the entire logging system."""
    
    # Step 1: Create log file
    log_file = _get_log_file()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Step 2: Get root logger
    root_logger = logging.getLogger()
    
    # Step 3: Set level
    selected_level = (log_level or os.getenv("LOG_LEVEL", "INFO")).upper()
    root_logger.setLevel(selected_level)
    
    # Step 4: Add handler (only if not already added)
    if any(getattr(handler, "name", None) == FILE_HANDLER_NAME 
           for handler in root_logger.handlers):
        return log_file
    
    # Step 5: Create handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.name = FILE_HANDLER_NAME
    
    # Step 6: Set format
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    
    # Step 7: Register with root
    root_logger.addHandler(file_handler)
    
    return log_file


# logger.py (Access - called MANY times)
# ═══════════════════════════════════════════════════
import logging

def get_logger(name: str) -> logging.Logger:
    """GET: Return a configured logger."""
    return logging.getLogger(name)
    
# That's it! Just returns a logger.
# All configuration already done by configure_logging()
```

### 5.3 Analogy: Restaurant Example

```
RESTAURANT EXAMPLE:

logging_config.py = OPENING THE RESTAURANT
├─ Build the kitchen
├─ Install ovens
├─ Stock ingredients
├─ Set up tables
└─ Do this ONCE at opening time
   (You don't rebuild the kitchen every time a customer arrives)

logger.py = ORDERING FROM THE RESTAURANT
├─ Customer walks in
├─ Says: "I need coffee"
├─ Waiter says: "Here's your coffee" (already made in the kitchen)
├─ Customer drinks it
└─ This happens MANY times per day
   (Each customer just gets what they need, doesn't rebuild kitchen)


In code:
├─ pytest_configure() = Opening time
│  └─ configure_logging()  ← Setup kitchen
│
├─ Test 1 starts
│  └─ get_logger("test1")  ← Get coffee (already configured)
│
├─ Test 2 starts
│  └─ get_logger("test2")  ← Get coffee (already configured)
│
└─ Test 3 starts
   └─ get_logger("test3")  ← Get coffee (already configured)
```

### 5.4 Where They Live and Talk to Each Other

```
conftest.py (MAIN ORCHESTRATOR)
    │
    ├─ def pytest_configure(config):
    │  └─ configure_logging()  ◄── SETUP (logging_config.py)
    │     └─ Creates & configures entire logging system
    │
    ├─ framework/api_client.py
    │  └─ get_logger(__name__)  ◄── USAGE (logger.py)
    │     └─ Returns configured logger
    │     └─ Writes to file (already configured)
    │
    └─ tests/test_api_client.py
       └─ get_logger(__name__)  ◄── USAGE (logger.py)
          └─ Returns configured logger
          └─ Writes to file (already configured)
```

### 5.5 Calling Sequence Example

```
When you write this in api_client.py:

logger = get_logger(__name__)
logger.info("Sending request...")

Here's what happens:

get_logger("framework.api_client")
    ↓
Does it need to configure logging? NO!
    ↓
Why not? Because logging_config.py already did it!
    ↓
logging_config.py was called in pytest_configure()
    ↓
Simply return the already-configured logger:
    ↓
return logging.getLogger("framework.api_client")
    ↓
Logger writes to: logs/test_20260829_...log
(The file created by logging_config.py)
```

### 5.6 Summary Table

| Aspect | logging_config.py | logger.py |
|--------|-------------------|-----------|
| **Purpose** | Setup logging system | Get logger for use |
| **When Called** | Once at pytest startup | Many times per run |
| **Called By** | pytest_configure() hook | All modules |
| **What It Does** | Creates log file, sets level, adds handler | Returns logging.Logger object |
| **Returns** | Path to log file | Logger object |
| **Used Again** | No (config is done) | Yes (every time you need logs) |
| **Frequency** | 1x per test run | 10x+ per test run |

---

## 6. Pytest Hooks Reference

### 6.1 Important: `pytest_setup` and `pytest_teardown` Don't Exist!

This is a **common mistake**:

```python
# ❌ THESE DO NOT EXIST as hooks:
def pytest_setup():        # ← NOT a pytest hook!
    pass

def pytest_teardown():     # ← NOT a pytest hook!
    pass


# ✅ CORRECT HOOK NAMES:
def pytest_runtest_setup():      # ← Real pytest hook
    pass

def pytest_runtest_teardown():   # ← Real pytest hook
    pass
```

### 6.2 All pytest Hooks (Complete List)

```
pytest hooks organized by lifecycle phase:

INITIALIZATION PHASE:
├─ pytest_configure()              ← Setup pytest config (your framework uses this!)
├─ pytest_sessionstart()            ← Start of test session
└─ pytest_collection()              ← Collect test items

PER-TEST PHASE:
├─ pytest_runtest_setup()           ← Before each test
├─ pytest_runtest_call()            ← Running the test
└─ pytest_runtest_teardown()        ← After each test

FINALIZATION PHASE:
├─ pytest_sessionfinish()           ← End of test session
└─ pytest_terminal_summary()        ← Generate report

COLLECTION PHASE:
├─ pytest_generate_tests()          ← Parametrization
├─ pytest_collection_modifyitems()  ← Modify collected tests
└─ pytest_make_collect_report()     ← Modify collection report

ASSERTION PHASE:
├─ pytest_assertrepr_compare()      ← Custom assertion messages
└─ pytest_assertion_pass()          ← Assertion passed

ERROR HANDLING:
├─ pytest_exception_interact()      ← Handle exceptions
├─ pytest_internalerror()           ← Internal pytest errors
└─ pytest_runtest_logreport()       ← Test result logging
```

### 6.3 Where These Hooks Are Defined

```
When you import pytest:

import pytest
    ↓
pytest package contains:
    ├─ Core hooks (built-in)
    │  └─ pytest_configure, pytest_runtest_setup, etc.
    │     └─ These are part of pytest itself
    │
    └─ You override them by defining them in conftest.py
       └─ pytest automatically finds and calls them
```

### 6.4 Your Current Framework Uses These Hooks

Your `conftest.py` currently uses:

```python
import pytest
from framework.api_client import ApiClient
from framework.config import Settings
from lib.logging_config import configure_logging

# ✅ HOOK #1: pytest_configure
# Built-in pytest hook
# pytest calls this automatically
def pytest_configure(config: pytest.Config) -> None:
    configure_logging(config.getoption("--log-level"))
    # This happens BEFORE any test runs


# ✅ FIXTURE #1: settings
# NOT a hook, it's a fixture
# Injected into tests when needed
@pytest.fixture(scope="session")
def settings() -> Settings:
    """Load shared test settings once for the test session."""
    return Settings.from_environment()


# ✅ FIXTURE #2: api_client
# NOT a hook, it's a fixture
# Injected into tests when needed
@pytest.fixture
def api_client(settings: Settings) -> ApiClient:
    """Provide a fresh API client for each test."""
    return ApiClient(settings)
```

**You're using:**
- 1 hook: `pytest_configure` (for setup)
- 2 fixtures: `settings` and `api_client` (for test data)

### 6.5 Common pytest Hooks You Might Use

```python
# SETUP/TEARDOWN HOOKS
def pytest_configure(config):
    """Before any test runs (global setup)"""
    print("Starting test session")
    # Good for: Logging setup, DB initialization


def pytest_sessionstart():
    """Start of test session (after configure)"""
    print("Session starting")


def pytest_runtest_setup():
    """Before each individual test"""
    print(f"Setting up: {test}")


def pytest_runtest_teardown():
    """After each individual test"""
    print(f"Tearing down: {test}")


def pytest_sessionfinish():
    """End of test session"""
    print("Session finished")


# COLLECTION HOOKS
def pytest_collection_modifyitems(items):
    """Modify collected tests before running"""
    # Good for: Adding markers, skipping tests


# REPORTING HOOKS
def pytest_terminal_summary(terminalreporter):
    """Add custom summary to test report"""
    # Good for: Custom test report formatting
```

### 6.6 Hooks vs Fixtures: Complete Comparison

```python
# HOOKS: pytest_* functions
# ═════════════════════════════════════════════
def pytest_configure(config):
    """HOOK: Called automatically by pytest"""
    print("Test session starting!")
    # pytest calls this for you

def pytest_runtest_setup():
    """HOOK: Called before each test"""
    print("Test is about to run")
    # pytest calls this for you


# FIXTURES: @pytest.fixture decorated functions
# ═════════════════════════════════════════════
@pytest.fixture(scope="session")
def settings():
    """FIXTURE: Injected into tests when needed"""
    return Settings.from_environment()
    # pytest injects this into test parameters

@pytest.fixture
def api_client(settings):
    """FIXTURE: Injected into tests"""
    return ApiClient(settings)
    # pytest injects this into test parameters


# THE DIFFERENCE:
Hooks:
├─ Called automatically at lifecycle points
├─ NOT injected into tests
├─ Global scope (apply to all tests)
└─ Examples: pytest_configure, pytest_runtest_setup

Fixtures:
├─ Called when needed by test functions
├─ Injected as test parameters
├─ Can have different scopes (session, function, module)
└─ Examples: settings, api_client, database connection
```

### 6.7 Summary Table

| Item | Is Built-In? | Called How? | Scope |
|------|-------------|-----------|-------|
| `pytest_configure()` | ✅ Yes | Auto by pytest | Global (once) |
| `pytest_runtest_setup()` | ✅ Yes | Auto by pytest | Per test |
| `pytest_runtest_teardown()` | ✅ Yes | Auto by pytest | Per test |
| `@pytest.fixture` | ✅ Yes | Injected by pytest | As defined |
| `get_logger()` | ❌ No (custom) | YOU call it | On demand |
| `configure_logging()` | ❌ No (custom) | Called by hook | On demand |
| Your own functions | ❌ No (custom) | YOU call it | On demand |

---

## Key Takeaways for Interview

### Error Handling Architecture
- ✅ Error handling should live in `lib/` layer (shared infrastructure)
- ✅ Design custom exception hierarchy first (before implementation)
- ✅ Stack traces are handled automatically by pytest + Python logging
- ✅ Use `from e` to preserve exception chains
- ✅ Use `exc_info=True` in logging to capture full stack traces to log file

### Framework Architecture
- ✅ conftest.py contains hooks and fixtures (entry point)
- ✅ Hooks are pytest built-in, automatically called (pytest_configure, etc.)
- ✅ Fixtures are test data/setup, injected into tests
- ✅ Regular functions are utilities, called explicitly
- ✅ Every module connects through imports and function calls

### Logging System
- ✅ logging_config.py sets up the logging system (called once)
- ✅ logger.py provides logger objects (called many times)
- ✅ They work together: setup + usage
- ✅ Once configured, logging is available globally

### Execution Flow
- ✅ pytest starts → pytest_configure() hook runs
- ✅ Logging configured → logger available everywhere
- ✅ Session fixtures created (settings)
- ✅ For each test: function fixtures created (api_client)
- ✅ Test runs → uses fixtures
- ✅ After test: function fixtures cleaned up
- ✅ After all tests: session fixtures cleaned up

---

## Quick Reference

### When to Use What

```
Need to setup logging system?
→ Use logging_config.py (called by hook)

Need a logger in your module?
→ Use get_logger(__name__) from logger.py

Need pytest lifecycle control?
→ Use pytest_configure() hook in conftest.py

Need to inject test data?
→ Use @pytest.fixture in conftest.py

Need to handle errors?
→ Create error_handler.py in lib/ (new architecture)
```

### Common Patterns

```
# PATTERN 1: Using logger in a module
from lib.logger import get_logger
logger = get_logger(__name__)
logger.info("Message")

# PATTERN 2: Creating a fixture
@pytest.fixture
def my_fixture():
    return setup()

# PATTERN 3: Using a fixture in a test
def test_something(my_fixture):
    assert my_fixture.something()

# PATTERN 4: Exception with context
try:
    something()
except SomeError as e:
    raise CustomError("message") from e

# PATTERN 5: Logging exception
logger.error("Failed", exc_info=True)
```

---

## Questions for Team Discussion

1. **For error handling design:**
   - What types of errors will our storage protocol framework encounter?
   - Which errors should auto-retry? How many times?
   - What context should we capture for each error type?

2. **For framework architecture:**
   - Are we happy with current layer separation?
   - Should we add more layers (connection, commands)?
   - How should error handling layer integrate?

3. **For testing:**
   - How should we test custom exceptions?
   - How do we mock external dependencies (API, network)?
   - Should we test retry logic separately?

---

## Additional Resources

- pytest documentation: https://docs.pytest.org/
- Python logging: https://docs.python.org/3/library/logging.html
- Exception chaining: https://docs.python.org/3/tutorial/errors.html#exception-chaining

---

**Document Version:** 1.0  
**Last Updated:** August 29, 2026  
**Ready for:** Team Review & Learning
