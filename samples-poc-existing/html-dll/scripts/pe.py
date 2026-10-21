"""Just enough stdlib PE parsing for the build and the checks."""
import struct

IMAGE_FILE_DLL = 0x2000


def _headers(pe):
    # Returns (coff offset, optional header offset, section list).
    assert pe[:2] == b"MZ", "no MZ magic"
    e_lfanew = struct.unpack_from("<I", pe, 0x3C)[0]
    assert pe[e_lfanew:e_lfanew + 4] == b"PE\0\0", "no PE signature"
    coff = e_lfanew + 4
    n_sections, opt_size = struct.unpack_from("<H", pe, coff + 2)[0], struct.unpack_from("<H", pe, coff + 16)[0]
    opt = coff + 20
    sections = []
    for i in range(n_sections):
        vsize, va, raw_size, raw_ptr = struct.unpack_from("<IIII", pe, opt + opt_size + i * 40 + 8)
        sections.append((va, vsize, raw_ptr, raw_size))
    return coff, opt, sections


def section_end(pe):
    """File offset where the last section's raw data ends: everything after it is overlay."""
    _, _, sections = _headers(pe)
    return max(raw_ptr + raw_size for _, _, raw_ptr, raw_size in sections if raw_ptr)


def is_dll(pe):
    coff, _, _ = _headers(pe)
    return bool(struct.unpack_from("<H", pe, coff + 18)[0] & IMAGE_FILE_DLL)


def export_names(pe):
    """Names in the export directory (PE32+ layout, as mingw-w64 emits)."""
    _, opt, sections = _headers(pe)

    def off(rva):
        for va, vsize, raw_ptr, _ in sections:
            if va <= rva < va + vsize:
                return rva - va + raw_ptr
        raise ValueError(f"RVA {rva:#x} not in any section")

    export_rva = struct.unpack_from("<I", pe, opt + 112)[0]  # DataDirectory[0] of the PE32+ optional header
    if not export_rva:
        return []
    n_names, _, names_rva = struct.unpack_from("<III", pe, off(export_rva) + 24)
    names = []
    for i in range(n_names):
        p = off(struct.unpack_from("<I", pe, off(names_rva) + 4 * i)[0])
        names.append(pe[p:pe.index(b"\0", p)].decode())
    return names
