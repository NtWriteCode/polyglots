#!/usr/bin/env python3
"""Builds editdata.mso: the ActiveMime container a Word MHT keeps its VBA project in.

Outside in: ActiveMime header -> zlib -> OLE2 compound file -> Macros/ storage
(MS-OVBA: PROJECT, PROJECTwm, VBA/dir, VBA/_VBA_PROJECT, VBA/ThisDocument). Stdlib only.
"""
import struct
import zlib

MODULE = "ThisDocument"

# What Word writes in front of a document module's code. olevba hides these lines.
MODULE_HEADER = """\
Attribute VB_Name = "ThisDocument"
Attribute VB_Base = "1Normal.ThisDocument"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = True
Attribute VB_Customizable = True
"""

PROJECT = """\
ID="{3E2D7C44-9D61-4B5A-8F0E-2C1B6A7D9E10}"
Document=ThisDocument/&H00000000
Name="Project"
HelpContextID="0"
VersionCompatible32="393222000"

[Host Extender Info]
&H00000001={3832D640-CF90-11CF-8E43-00A0C911005A};VBE;&H00000000

[Workspace]
ThisDocument=0, 0, 0, 0, C
"""

STDOLE = b"*\\G{00020430-0000-0000-C000-000000000046}#2.0#0#C:\\Windows\\System32\\stdole2.tlb#OLE Automation"
WORD = (b"*\\G{00020905-0000-0000-C000-000000000046}#8.7#0#C:\\Program Files\\Microsoft Office\\Root\\Office16"
        b"\\MSWORD.OLB#Microsoft Word 16.0 Object Library")


def crlf(text):
    return text.replace("\n", "\r\n").encode()


def u16(text):
    return text.encode("utf-16-le")


def rec(rid, payload):
    # MS-OVBA dir record: Id, Size, payload.
    return struct.pack("<HI", rid, len(payload)) + payload


def ovba_compress(data):
    """MS-OVBA CompressedContainer with literal tokens only: a 0x00 flag byte per 8 bytes of data.
    One chunk holds up to 3640 bytes; our streams are far smaller."""
    assert len(data) <= 3640
    body = b"".join(b"\0" + data[i:i + 8] for i in range(0, len(data), 8))
    return b"\x01" + struct.pack("<H", 0xB000 | (len(body) - 1)) + body


def reference(name, libid):
    # REFERENCENAME + REFERENCEREGISTERED (MS-OVBA 2.3.4.2.2).
    return (rec(0x0016, name) + rec(0x003E, u16(name.decode()))
            + rec(0x000D, struct.pack("<I", len(libid)) + libid + b"\0" * 6))


def dir_stream():
    # MS-OVBA 2.3.4.2: project info, references, one module record.
    return b"".join([
        rec(0x0001, struct.pack("<I", 1)),          # SYSKIND: 32-bit Windows
        rec(0x0002, struct.pack("<I", 0x409)),      # LCID
        rec(0x0014, struct.pack("<I", 0x409)),      # LCIDINVOKE
        rec(0x0003, struct.pack("<H", 1252)),       # CODEPAGE
        rec(0x0004, b"Project"),                    # NAME
        rec(0x0005, b"") + rec(0x0040, b""),        # DOCSTRING
        rec(0x0006, b"") + rec(0x003D, b""),        # HELPFILEPATH
        rec(0x0007, struct.pack("<I", 0)),          # HELPCONTEXT
        rec(0x0008, struct.pack("<I", 0)),          # LIBFLAGS
        struct.pack("<HIIH", 0x0009, 4, 0x61E0B65A, 0),  # VERSION
        rec(0x000C, b"") + rec(0x003C, b""),        # CONSTANTS
        reference(b"stdole", STDOLE),
        reference(b"Word", WORD),
        rec(0x000F, struct.pack("<H", 1)),          # MODULES: count
        rec(0x0013, struct.pack("<H", 0xFFFF)),     # COOKIE
        rec(0x0019, MODULE.encode()) + rec(0x0047, u16(MODULE)),  # MODULENAME
        rec(0x001A, MODULE.encode()) + rec(0x0032, u16(MODULE)),  # MODULESTREAMNAME
        rec(0x001C, b"") + rec(0x0048, b""),        # MODULEDOCSTRING
        rec(0x0031, struct.pack("<I", 0)),          # MODULEOFFSET: source starts at 0
        rec(0x001E, struct.pack("<I", 0)),          # MODULEHELPCONTEXT
        rec(0x002C, struct.pack("<H", 0xFFFF)),     # MODULECOOKIE
        rec(0x0022, b""),                           # MODULETYPE: document module
        rec(0x002B, b""),                           # end of module
        rec(0x0010, b""),                           # end of dir
    ])


def cfb(streams):
    """Minimal OLE2 compound file. streams: {"Macros/VBA/dir": bytes, ...}; storages are implied.
    Every stream is small (< 4096 bytes) and lives in the mini stream, so the FAT only
    covers the FAT sector itself, the directory, the mini FAT and the mini stream."""
    END, FREE, FATSECT, NOSID = 0xFFFFFFFE, 0xFFFFFFFF, 0xFFFFFFFD, 0xFFFFFFFF

    root = {"name": "Root Entry", "type": 5, "kids": {}}
    for path, data in streams.items():
        assert 0 < len(data) < 4096, path
        node = root
        *dirs, leaf = path.split("/")
        for d in dirs:
            node = node["kids"].setdefault(d, {"name": d, "type": 1, "kids": {}})
        node["kids"][leaf] = {"name": leaf, "type": 2, "data": data}

    # Flatten the tree. Siblings are chained through sid_right in CFB sort order
    # (shorter name first, then case-insensitive): a valid, if unbalanced, red-black tree.
    entries = []

    def add(node):
        node["sid"] = len(entries)
        entries.append(node)
        kids = sorted(node.get("kids", {}).values(), key=lambda k: (len(k["name"]), k["name"].upper()))
        for kid in kids:
            add(kid)
        for a, b in zip(kids, kids[1:]):
            a["right"] = b["sid"]
        node["child"] = kids[0]["sid"] if kids else NOSID

    add(root)

    # Mini stream: each stream padded to 64-byte mini sectors, chained in the mini FAT.
    mini, minifat = bytearray(), []
    for e in entries:
        if e["type"] == 2:
            n = -(-len(e["data"]) // 64)
            e["start"], e["size"] = len(minifat), len(e["data"])
            minifat += list(range(len(minifat) + 1, len(minifat) + n)) + [END]
            mini += e["data"].ljust(n * 64, b"\0")
    minifat += [FREE] * (-len(minifat) % 128)

    def sectors(data):
        return bytes(data).ljust(-(-len(data) // 512) * 512, b"\0")

    minifat_data = struct.pack("<%dI" % len(minifat), *minifat)
    mini_data = sectors(mini)
    n_dir = -(-len(entries) * 128 // 512)
    n_minifat = len(minifat_data) // 512
    # Sector map: 0 = FAT, then directory, mini FAT, mini stream.
    root["start"], root["size"] = 1 + n_dir + n_minifat, len(mini)
    fat = [FATSECT]
    for n in (n_dir, n_minifat, len(mini_data) // 512):
        fat += list(range(len(fat) + 1, len(fat) + n)) + [END]
    assert len(fat) <= 128, "one FAT sector is enough here"
    fat_data = struct.pack("<128I", *fat, *[FREE] * (128 - len(fat)))

    def direntry(e):
        name = u16(e["name"]) + b"\0\0"
        return struct.pack("<64sHBBIII16sIQQIII", name, len(name), e["type"], 1,
                           NOSID, e.get("right", NOSID), e.get("child", NOSID), b"\0" * 16,
                           0, 0, 0, e.get("start", 0), e.get("size", 0), 0)

    dir_data = sectors(b"".join(direntry(e) for e in entries))

    header = struct.pack("<8s16sHHHHH6sIIIIIIIII", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", b"\0" * 16,
                         0x3E, 3, 0xFFFE, 9, 6, b"\0" * 6,
                         0, 1, 1, 0, 4096, 1 + n_dir, n_minifat, END, 0)
    header += struct.pack("<109I", 0, *[FREE] * 108)
    return header + fat_data + dir_data + minifat_data + mini_data


def activemime(ole):
    # Header per github.com/idiom/activemime-format. zlib data starts at 0x32,
    # the offset olevba tries first.
    z = zlib.compress(ole)
    hdr = b"".join([
        b"ActiveMime\0\0", b"\x01\xf0", struct.pack("<I", 4), b"\xff" * 4, b"\x00\x00\x06\xf0",
        struct.pack("<I", len(z)),
        struct.pack("<III", 4, 4, 0),
        struct.pack("<I", 2),           # 2: no plain-text VBA strings after the zlib block
        struct.pack("<I", len(ole)),
    ])
    assert len(hdr) == 0x32
    return hdr + z


def editdata_mso(macro):
    return activemime(cfb({
        "Macros/PROJECT": crlf(PROJECT),
        "Macros/PROJECTwm": MODULE.encode() + b"\0" + u16(MODULE) + b"\0\0" + b"\0\0",
        "Macros/VBA/_VBA_PROJECT": b"\xcc\x61\xff\xff\x00\x00\x00",
        "Macros/VBA/dir": ovba_compress(dir_stream()),
        "Macros/VBA/" + MODULE: ovba_compress(crlf(MODULE_HEADER + macro)),
    }))
