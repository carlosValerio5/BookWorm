import pytest

from bookworm.crawler.address_policy import is_public_address, resolve_host_addresses


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "::1", "fe80::1%en0"])
def test_non_public_addresses_are_rejected(address: str) -> None:
    assert is_public_address(address) is False


def test_public_address_is_accepted() -> None:
    assert is_public_address("93.184.216.34") is True


def test_ip_literal_resolves_to_itself_once() -> None:
    assert resolve_host_addresses("127.0.0.1") == ["127.0.0.1"]
