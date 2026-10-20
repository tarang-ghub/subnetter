#!/usr/bin/env python3
"""
ipcalc.py - Find the class, network range, host range and broadcast
address for a Class A, B or C IPv4 address with a netmask.

Usage examples:
    python ipcalc.py 192.168.1.37 255.255.255.0
    python ipcalc.py 10.20.30.40 255.255.0.0
    python ipcalc.py 172.16.5.9 /20
    python ipcalc.py 192.168.1.37/26
"""

import argparse
import ipaddress
import sys


def ip_class(ip: ipaddress.IPv4Address) -> str:
    first = int(str(ip).split(".")[0])
    if first < 128:
        return "A"
    if first < 192:
        return "B"
    if first < 224:
        return "C"
    if first < 240:
        return "D"
    return "E"


def default_prefix(cls: str) -> int:
    return {"A": 8, "B": 16, "C": 24}[cls]


def parse_args():
    p = argparse.ArgumentParser(
        description="Calculate network details for a Class A, B or C IPv4 address."
    )
    p.add_argument(
        "ip",
        help="IPv4 address, optionally with CIDR suffix (e.g. 192.168.1.10 or 192.168.1.10/24)",
    )
    p.add_argument(
        "netmask",
        nargs="?",
        help="Netmask: dotted (255.255.255.0) or CIDR (/24 or 24). "
        "If omitted, the class default mask is used.",
    )
    return p.parse_args()


def main():
    args = parse_args()

    # Split "ip/prefix" form if given
    ip_part, _, cidr_part = args.ip.partition("/")

    try:
        ip = ipaddress.IPv4Address(ip_part)
    except ipaddress.AddressValueError:
        sys.exit(f"Error: '{ip_part}' is not a valid IPv4 address.")

    cls = ip_class(ip)
    if cls not in ("A", "B", "C"):
        sys.exit(
            f"Error: {ip} is a Class {cls} address "
            f"({'multicast' if cls == 'D' else 'reserved'}); "
            "only Class A, B and C are supported."
        )

    # Decide on the mask: CIDR in the address > netmask argument > class default
    mask_str = args.netmask or cidr_part
    if not mask_str:
        mask_str = str(default_prefix(cls))
        used_default = True
    else:
        used_default = False

    mask_str = mask_str.lstrip("/")

    try:
        net = ipaddress.IPv4Network(f"{ip}/{mask_str}", strict=False)
    except (ipaddress.NetmaskValueError, ValueError):
        sys.exit(
            f"Error: '{mask_str}' is not a valid netmask "
            "(use e.g. 255.255.255.0 or /24; mask bits must be contiguous)."
        )

    network = net.network_address
    broadcast = net.broadcast_address
    total = net.num_addresses

    # Host range (usable addresses)
    if net.prefixlen == 32:
        first_host = last_host = network
        usable = 1
    elif net.prefixlen == 31:  # point-to-point link (RFC 3021)
        first_host, last_host = network, broadcast
        usable = 2
    else:
        first_host = network + 1
        last_host = broadcast - 1
        usable = total - 2

    default_p = default_prefix(cls)
    note = ""
    if net.prefixlen > default_p:
        note = f"subnetted ({net.prefixlen - default_p} subnet bits borrowed)"
    elif net.prefixlen < default_p:
        note = "supernetted (mask is shorter than the class default)"

    print(f"IP Address      : {ip}")
    print(f"Class           : {cls}{' (default mask used)' if used_default else ''}")
    print(f"Netmask         : {net.netmask}  (/{net.prefixlen})")
    print(f"Wildcard mask   : {net.hostmask}")
    if note:
        print(f"Note            : {note}")
    print("-" * 44)
    print(f"Network address : {network}")
    print(f"Broadcast addr  : {broadcast}")
    print(f"First host IP   : {first_host}")
    print(f"Last host IP    : {last_host}")
    print(f"Network range   : {network} - {broadcast}")
    print(f"Host range      : {first_host} - {last_host}")
    print(f"Total addresses : {total}")
    print(f"Usable hosts    : {usable}")
    print(f"Address type    : {'private' if ip.is_private else 'public'}")


if __name__ == "__main__":
    main()
