#!/usr/bin/env python3
"""List nearby Even G2 arms and their addresses for local flashing."""

import argparse
import asyncio
import sys

from bleak import BleakScanner
from bleak.exc import BleakError

from g2flash import G2_NAME_RE, SCAN_TIMEOUT


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(f"Scanning for Even G2 arms for {SCAN_TIMEOUT} seconds...", file=sys.stderr)
    try:
        devices = asyncio.run(
            BleakScanner.discover(timeout=SCAN_TIMEOUT, return_adv=True)
        )
    except (BleakError, OSError) as error:
        print(f"Bluetooth scan failed ({error}).", file=sys.stderr)
        return 1

    arms: list[tuple[str, str]] = []
    for device, advertisement in devices.values():
        name = advertisement.local_name or device.name or ""
        if G2_NAME_RE.search(name):
            arms.append((name, device.address))
    if not arms:
        print("No Even G2 arms found.", file=sys.stderr)
        return 1

    for name, address in sorted(arms):
        print(f"{name}  {address}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
