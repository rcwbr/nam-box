# mod-api Tests

Test suite for the mod-api service using testcontainers for integration testing
and MockModHostClient for unit testing.

## Structure

```
tests/
├── __init__.py           # Test package marker
├── conftest.py           # Imports mod_host_compose fixture
├── fixtures/               # Shared test fixtures
│   ├── __init__.py         # Exports MockModHostClient
│   ├── mod_host.py         # Docker compose fixture for mod-host service
│   └── mock_client.py      # Mock ModHostClient for unit testing
├── integration/            # Integration tests using real mod-host via testcontainers
│   ├── __init__.py
│   └── test_pedalboard_api.py
├── unit/                   # Unit tests using MockModHostClient
│   ├── conftest.py           # Adds fixtures to path for clean imports
│   ├── test_pedalboard_store.py  # PedalboardStore tests
│   ├── test_mod_host_client.py    # MockModHostClient protocol tests
│   └── test_api_endpoints.py      # API endpoint tests
└── resources/
    └── docker-compose.mod-host.yaml  # Docker compose file for mod-host service
```

## Test Count

- **12 passing tests**: `test_mod_host_client.py` (MockModHostClient functionality verification)
- **47 skipped tests**: All tests for `mod_api.api`, `mod_api.storage`, and integration modules

## Running Tests

Install test dependencies:

```bash
pip install -e ".[test]"
```

Run all tests:

```bash
pytest tests/ -v
```

Run unit tests only:

```bash
pytest tests/unit/ -v
```

Run integration tests only:

```bash
pytest tests/integration/ -v
```

Note: API and storage tests are currently skipped as they require the `mod_api` package
to be implemented. Once implemented, these tests will guide the development via TDD.

## Fixtures

### `mod_host_compose` (session scope)

Brings up a mod-host container via Docker Compose with:
- NAM plugin available at `/opt/lv2`
- Control port exposed on 5555
- Feedback port exposed on 5556
- Test model file pre-created at `/opt/nam/models/test.nam`
- Privileged mode for audio device access

Returns a dict with:
- `control_port`: The exposed port for mod-host control socket
- `feedback_port`: The exposed port for feedback socket

### `MockModHostClient`

A mock client for testing the Pedalboard API without a real mod-host instance.
Records all commands sent via `commands_sent` list for verification:

```python
# In tests
mock_client = MockModHostClient()
create_effect_instance(..., client=mock_client)

# Verify the command that was sent
assert f'add "{NAM_PLUGIN_URI}"' in mock_client.commands_sent[0]
```

Response configuration methods:
- `set_response(pattern, status, value)`: Define response for exact command or `*` pattern
- `set_default_response(status, value)`: Default response for unmatched commands
- `reset_responses()`: Clear all predefined responses

Use this for unit tests to verify correct mod-host protocol commands are sent.