import pytest
from events import EventBus, ThreadedDispatcher, matches


def test_publish_calls_matching_subscribers():
    bus = EventBus()
    seen = []
    bus.subscribe("orders.*", lambda t, e: seen.append(("a", t, e)))
    bus.subscribe("orders.#", lambda t, e: seen.append(("b", t, e)))
    bus.subscribe("users.*", lambda t, e: seen.append(("c", t, e)))
    assert bus.publish("orders.created", 1) == 2
    assert sorted(seen) == [("a", "orders.created", 1), ("b", "orders.created", 1)]


def test_unsubscribed_callbacks_are_not_called():
    bus = EventBus()
    seen = []
    token = bus.subscribe("#", lambda t, e: seen.append(e))
    bus.unsubscribe(token)
    bus.unsubscribe(token)  # unknown tokens are ignored
    assert bus.publish("x", "y") == 0 and seen == []


def test_topic_patterns():
    assert matches("a.*.c", "a.b.c") and not matches("a.*.c", "a.b.b.c")
    assert matches("a.#", "a") and matches("a.#", "a.b.c")
    with pytest.raises(ValueError):
        matches("a.b*", "a.bc")


def test_threaded_dispatcher_runs_callbacks():
    dispatcher = ThreadedDispatcher(workers=2)
    bus = EventBus()
    seen = []
    bus.subscribe("jobs.*", dispatcher.wrap(lambda t, e: seen.append(e)))
    for n in range(5):
        bus.publish("jobs.done", n)
    dispatcher.drain()
    dispatcher.close()
    assert sorted(seen) == [0, 1, 2, 3, 4]
