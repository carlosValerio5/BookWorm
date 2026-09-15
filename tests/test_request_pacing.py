from bookworm.crawler.request_pacing import HostPacer


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def build_pacer(clock: FakeClock, min_seconds_between_requests: float = 3.0) -> HostPacer:
    return HostPacer(
        min_seconds_between_requests=min_seconds_between_requests,
        clock=clock.monotonic,
        sleep=clock.sleep,
    )


def test_first_request_to_a_host_does_not_wait() -> None:
    clock = FakeClock()

    build_pacer(clock).wait_for_host("api.openverse.org")

    assert clock.sleeps == []


def test_second_request_waits_for_the_remaining_gap() -> None:
    clock = FakeClock()
    pacer = build_pacer(clock)

    pacer.wait_for_host("api.openverse.org")
    clock.now += 1.0
    pacer.wait_for_host("api.openverse.org")

    assert clock.sleeps == [2.0]


def test_hosts_are_paced_independently() -> None:
    clock = FakeClock()
    pacer = build_pacer(clock)

    pacer.wait_for_host("api.openverse.org")
    pacer.wait_for_host("live.staticflickr.com")

    assert clock.sleeps == []


def test_no_wait_when_the_gap_already_passed() -> None:
    clock = FakeClock()
    pacer = build_pacer(clock)

    pacer.wait_for_host("api.openverse.org")
    clock.now += 5.0
    pacer.wait_for_host("api.openverse.org")

    assert clock.sleeps == []
