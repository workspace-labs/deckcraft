"""Read a TrueType font's names and flags, and wrap it as EOT for embedding in a .pptx.

PowerPoint only uses an embedded font stored as Embedded OpenType (.fntdata);
a raw TTF is ignored (proven in PowerPoint for Mac, 2026-10-21). EOT here is
version 2.1, uncompressed, not obfuscated: a header followed by the TTF bytes.
"""
import struct


def _tables(b):
    n = struct.unpack(">H", b[4:6])[0]
    out = {}
    for i in range(n):
        tag, _, off, ln = struct.unpack(">4sIII", b[12 + 16 * i:28 + 16 * i])
        out[tag.decode("latin-1")] = (off, ln)
    return out


def _name(b, t, nid):
    off, _ = t["name"]
    _, count, so = struct.unpack(">HHH", b[off:off + 6])
    for i in range(count):
        pid, _, lid, n, ln, o = struct.unpack(">6H", b[off + 6 + 12 * i:off + 18 + 12 * i])
        if pid == 3 and lid == 0x409 and n == nid:
            return b[off + so + o:off + so + o + ln].decode("utf-16-be")
    return ""


def read(b):
    """Names and flags of a TTF: family (name ID 1), style (ID 2), weight, fsType and more."""
    if b[:4] not in (b"\x00\x01\x00\x00", b"true"):
        raise ValueError("not a TrueType font")
    t = _tables(b)
    os2, head = t["OS/2"][0], t["head"][0]
    return {
        "family": _name(b, t, 1), "style": _name(b, t, 2), "version": _name(b, t, 5), "full": _name(b, t, 4),
        "weight": struct.unpack(">H", b[os2 + 4:os2 + 6])[0],
        "fstype": struct.unpack(">H", b[os2 + 8:os2 + 10])[0],
        "panose": b[os2 + 32:os2 + 42],
        "unicode": struct.unpack(">4I", b[os2 + 42:os2 + 58]),
        "codepage": struct.unpack(">2I", b[os2 + 78:os2 + 86]),
        "italic": 1 if struct.unpack(">H", b[os2 + 62:os2 + 64])[0] & 1 else 0,
        "checksum": struct.unpack(">I", b[head + 8:head + 12])[0],
    }


def eot(b):
    """The font wrapped as an EOT 2.1 file."""
    f = read(b)

    def s(text):
        e = text.encode("utf-16-le")
        return struct.pack("<HH", 0, len(e)) + e  # padding, size, string

    names = s(f["family"]) + s(f["style"]) + s(f["version"]) + s(f["full"]) + s("")
    fixed = (struct.pack("<III", len(b), 0x00020001, 0) + f["panose"] +
             struct.pack("<BBIHH", 1, f["italic"], f["weight"], f["fstype"], 0x504C) +
             struct.pack("<4I", *f["unicode"]) + struct.pack("<2I", *f["codepage"]) +
             struct.pack("<I", f["checksum"]) + struct.pack("<4I", 0, 0, 0, 0))
    total = 4 + len(fixed) + len(names) + len(b)
    return struct.pack("<I", total) + fixed + names + b
