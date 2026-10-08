import pytest
from clients import ClientHealth, ClientRegistry, EnvConfig, LazyClient, UnknownClient, redact


def test_client_is_created_on_first_use_and_reused():
    calls = []

    def factory(**options):
        calls.append(options)
        return object()

    lazy = LazyClient(factory, options={"url": "x"})
    assert calls == [] and not lazy.ready
    first = lazy.get()
    assert lazy.get() is first and lazy.ready
    assert calls == [{"url": "x"}]


def test_registry_passes_configured_options():
    created = []

    def make_db(**options):
        created.append(options)
        return ("db", options["pool_size"])

    registry = ClientRegistry({"db": make_db}, EnvConfig())
    assert registry.get("db") == ("db", 10)
    assert registry.get("db") is registry.get("db")
    assert len(created) == 1
    with pytest.raises(UnknownClient):
        registry.get("search")


def test_redaction_and_health():
    assert redact("postgres://app:hunter2@db:5432/app") == "postgres://app:***@db:5432/app"
    assert redact("redis://cache:6379/0") == "redis://cache:6379/0"
    health = ClientHealth()
    health.record("db", True)
    health.record("cache", False, "timeout")
    assert not health.healthy() and health.snapshot()["cache"] == (False, "timeout")
