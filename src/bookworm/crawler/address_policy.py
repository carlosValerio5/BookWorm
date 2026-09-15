import ipaddress
import socket


def resolve_host_addresses(host: str) -> list[str]:
    address_infos = socket.getaddrinfo(host, None)
    return list(dict.fromkeys(str(address_info[4][0]) for address_info in address_infos))


def is_public_address(address: str) -> bool:
    address_without_scope = address.partition("%")[0]
    return ipaddress.ip_address(address_without_scope).is_global
