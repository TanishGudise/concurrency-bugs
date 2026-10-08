from lazy import LazyClient


def test_client_is_created_on_first_use_and_reused():
    calls = []

    def factory():
        calls.append(1)
        return object()

    lazy = LazyClient(factory)
    assert calls == []
    first = lazy.get()
    assert lazy.get() is first
    assert len(calls) == 1
