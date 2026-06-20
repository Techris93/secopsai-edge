from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_network


class ScanSafetyError(ValueError):
    """Raised when a scan target violates MVP safety controls."""


@dataclass(frozen=True, slots=True)
class ScanSafetyPolicy:
    allow_public_targets: bool = False
    max_hosts: int = 4096
    min_prefix_v4: int = 20


def validate_target_cidr(cidr: str, policy: ScanSafetyPolicy | None = None) -> str:
    policy = policy or ScanSafetyPolicy()
    try:
        network = ip_network(cidr, strict=False)
    except ValueError as exc:
        raise ScanSafetyError(f"Invalid CIDR target: {cidr}") from exc

    if network.version != 4:
        raise ScanSafetyError("Only IPv4 CIDR targets are supported in the MVP.")

    if not policy.allow_public_targets and not network.is_private:
        raise ScanSafetyError("Public IP ranges are rejected by default.")

    if network.prefixlen < policy.min_prefix_v4:
        raise ScanSafetyError(
            f"CIDR {network} is too broad. Use /{policy.min_prefix_v4} or narrower."
        )

    if network.num_addresses > policy.max_hosts:
        raise ScanSafetyError(
            f"CIDR {network} has {network.num_addresses} addresses; limit is {policy.max_hosts}."
        )

    return str(network)
