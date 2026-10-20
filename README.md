# ipcalc

A small Python command-line tool that takes a **Class A, B or C IPv4 address** and a **netmask**, and works out:

- the address class
- the network address
- the broadcast address
- the first and last usable host IPs
- the full network range and host range
- the number of total and usable addresses

It uses only Python's standard library, so there is nothing to install.

## Usage

```bash
python ipcalc.py 192.168.1.37 255.255.255.0     # dotted netmask
python ipcalc.py 172.16.5.9 /20                 # CIDR netmask
python ipcalc.py 192.168.1.37/26                # CIDR attached to the IP
python ipcalc.py 10.20.30.40                    # no mask: class default is used
```

On Linux/macOS you can also run it directly after `chmod +x ipcalc.py`:

```bash
./ipcalc.py 192.168.1.37 255.255.255.0
```

### Example output

```
IP Address      : 192.168.1.37
Class           : C
Netmask         : 255.255.255.0  (/24)
Wildcard mask   : 0.0.0.255
--------------------------------------------
Network address : 192.168.1.0
Broadcast addr  : 192.168.1.255
First host IP   : 192.168.1.1
Last host IP    : 192.168.1.254
Network range   : 192.168.1.0 - 192.168.1.255
Host range      : 192.168.1.1 - 192.168.1.254
Total addresses : 256
Usable hosts    : 254
Address type    : private
```

## Requirements

Python 3.6 or newer. No third-party packages.

---

## How the code was created

The program was built in a few deliberate steps.

**1. Define what the tool must do.**
The goal was a CLI that, given an IP address and netmask, reports the host range, broadcast address and network range, restricted to Class A, B and C addresses.

**2. Decide on the inputs.**
People write netmasks in different ways, so the tool accepts three forms: dotted (`255.255.255.0`), CIDR (`/24` or `24`), and CIDR attached to the address (`192.168.1.37/26`). If no mask is given, it falls back to the default mask for the address's class.

**3. Choose the building blocks.**
- `argparse` handles the command-line arguments and the `--help` text.
- The standard `ipaddress` module does the binary arithmetic and validation. It is well tested and avoids hand-written bit manipulation, which is easy to get wrong.

**4. Split the logic into small functions.**
- `ip_class()` works out the class from the first octet.
- `default_prefix()` returns the default prefix length for a class.
- `parse_args()` defines the command-line interface.
- `main()` ties everything together: it validates the input, builds the network, calculates the results and prints them.

**5. Add validation and clear errors.**
The tool rejects invalid IP addresses, Class D (multicast) and Class E (reserved) addresses, and masks whose bits are not contiguous (for example `255.0.255.0`). Each case exits with a readable message instead of a Python traceback.

**6. Handle edge cases.**
/31 and /32 networks need special treatment (explained below), so they have their own branches.

**7. Add the entry-point guard and shebang.**
`if __name__ == "__main__": main()` lets the file be imported without running, and `#!/usr/bin/env python3` lets it be run directly on Unix-like systems.

**8. Test with sample inputs.**
The script was run against a Class C address with a dotted mask, a Class B address with a CIDR mask, a Class A address with no mask, a multicast address, and an invalid mask, to confirm both the results and the error handling.

---

## The logic behind it

### 1. Finding the class

The class is decided by the **first octet** of the address:

| Class | First octet range | Default mask | Default prefix |
|-------|-------------------|--------------|----------------|
| A     | 1 - 127           | 255.0.0.0    | /8             |
| B     | 128 - 191         | 255.255.0.0  | /16            |
| C     | 192 - 223         | 255.255.255.0| /24            |
| D     | 224 - 239         | (multicast)  | not supported  |
| E     | 240 - 255         | (reserved)   | not supported  |

In binary, the leading bits of the first octet identify the class: `0` for A, `10` for B, `110` for C. The code simply compares the first octet against these ranges.

### 2. Understanding the netmask

A netmask is 32 bits: a run of `1`s followed by a run of `0`s.

- The `1` bits mark the **network** portion of the address.
- The `0` bits mark the **host** portion.

`255.255.255.0` is `11111111.11111111.11111111.00000000`, which is 24 ones, so it is written `/24`. The tool checks that the mask is valid (all ones first, then all zeros), because something like `255.0.255.0` does not describe a real network.

The **wildcard mask** is the bitwise inverse of the netmask (`0.0.0.255` for `/24`). It marks the host bits.

### 3. Network address = IP AND netmask

The network address is found by applying a bitwise **AND** between the IP and the mask. This keeps the network bits and zeroes the host bits.

Example: `192.168.1.37` with `255.255.255.192` (/26)

```
IP       192.168.1.37   = 11000000.10101000.00000001.00100101
Mask     255.255.255.192= 11111111.11111111.11111111.11000000
                          ---------------------------------- AND
Network  192.168.1.0    = 11000000.10101000.00000001.00000000
```

In the code, `ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)` performs this step. `strict=False` allows a host address to be passed in, and the module clears the host bits to give the network address.

### 4. Broadcast address = network address OR wildcard mask

The broadcast address is the network address with **all host bits set to 1**. This is a bitwise **OR** of the network address with the wildcard mask.

```
Network   192.168.1.0  = 11000000.10101000.00000001.00000000
Wildcard  0.0.0.63     = 00000000.00000000.00000000.00111111
                         ---------------------------------- OR
Broadcast 192.168.1.63 = 11000000.10101000.00000001.00111111
```

### 5. Host range

The first and last addresses in a network are reserved: the first is the network address and the last is the broadcast address. Usable hosts sit in between.

- **First host** = network address + 1
- **Last host** = broadcast address - 1

For the /26 example above: first host `192.168.1.1`, last host `192.168.1.62`.

### 6. Counting hosts

If `h` is the number of host bits (`32 - prefix length`):

- **Total addresses** = 2^h
- **Usable hosts** = 2^h - 2 (subtracting the network and broadcast addresses)

For /26, `h = 6`, so there are 64 total addresses and 62 usable hosts. For /24, `h = 8`, giving 256 total and 254 usable.

### 7. Special cases

- **/32** is a single host. There is no separate network or broadcast address, so the host range is just that one address.
- **/31** is a point-to-point link (RFC 3021). Both addresses are usable, so the usual "minus 2" rule is not applied.

### 8. Subnetting and supernetting

The tool compares the prefix length you supplied with the class default:

- A longer prefix than the default means the network is **subnetted** (host bits were borrowed to create subnets). The number of borrowed bits is shown.
- A shorter prefix than the default means it is **supernetted**.

For example, a Class B address (default /16) with `/20` has 4 subnet bits borrowed.

### 9. Private or public

The `ipaddress` module's `is_private` property tells you whether the address falls in a reserved private range (such as `10.0.0.0/8`, `172.16.0.0/12` or `192.168.0.0/16`).

---

## Project structure

```
ipcalc/
├── ipcalc.py    # the program
└── README.md    # this file
```

## Possible improvements

- Split a network into equal subnets for a requested number of hosts or subnets (VLSM).
- Print the binary form of the address, mask and network.
- Add IPv6 support.
- Add unit tests for the helper functions.

## License
