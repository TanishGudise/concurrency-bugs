from eventbus import EventBus


def test_publish_calls_every_subscriber():
    bus = EventBus()
    seen = []
    bus.subscribe(lambda e: seen.append(("a", e)))
    bus.subscribe(lambda e: seen.append(("b", e)))
    assert bus.publish(1) == 2
    assert sorted(seen) == [("a", 1), ("b", 1)]


def test_unsubscribed_callbacks_are_not_called():
    bus = EventBus()
    seen = []
    token = bus.subscribe(seen.append)
    bus.unsubscribe(token)
    bus.unsubscribe(token)  # unknown tokens are ignored
    assert bus.publish("x") == 0
    assert seen == []
