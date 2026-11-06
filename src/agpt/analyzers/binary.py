"""Bounded PE import and ELF DT_NEEDED inspection (read-only, no execution)."""
from __future__ import annotations

import struct
from pathlib import Path

MAX_HEADER_READ = 2 * 1024 * 1024
MAX_PE_SECTIONS = 96
MAX_PE_IMPORTS = 512
MAX_DEPENDENCY_NAME = 260
MAX_DYNAMIC_ENTRIES = 4096

MACHINE_NAMES = {
    0x014C: "x86", 0x8664: "x86_64", 0x01C0: "arm",
    0x01C4: "armv7", 0xAA64: "arm64", 0x0200: "ia64",
}
ELF_MACHINE_NAMES = {3: "x86", 40: "arm", 62: "x86_64", 183: "arm64", 243: "riscv"}

class BoundedReader:
    def __init__(self, path: str | Path, budget: int = MAX_HEADER_READ):
        self.path = Path(path)
        self.size = self.path.stat().st_size
        self.budget = budget
        self.bytes_read = 0
        self._stream = self.path.open("rb")

    def close(self) -> None:
        self._stream.close()

    def read(self, offset: int, size: int) -> bytes:
        if offset < 0 or size < 0 or size > self.budget:
            raise ValueError("invalid or oversized read")
        if offset > self.size or size > self.size - offset:
            raise ValueError("read outside file bounds")
        if self.bytes_read + size > self.budget:
            raise ValueError("binary analysis read budget exceeded")
        self._stream.seek(offset)
        value = self._stream.read(size)
        self.bytes_read += len(value)
        if len(value) != size:
            raise ValueError("short read")
        return value

def _c_string(reader: BoundedReader, offset: int, limit: int = MAX_DEPENDENCY_NAME) -> str:
    if offset < 0 or offset >= reader.size:
        return ""
    raw = reader.read(offset, min(limit, reader.size - offset))
    return raw.split(b"\0", 1)[0].decode("utf-8", errors="replace").strip()

def parse_pe_imports(path: str | Path) -> dict:
    """Return PE machine/timestamp/import DLL names; malformed files fail closed."""
    reader = BoundedReader(path)
    try:
        dos = reader.read(0, 0x40)
        if dos[:2] != b"MZ":
            raise ValueError("missing MZ signature")
        pe_offset = struct.unpack_from("<I", dos, 0x3C)[0]
        if pe_offset < 0x40 or pe_offset > min(reader.size - 24, 16 * 1024 * 1024):
            raise ValueError("invalid PE header offset")
        coff = reader.read(pe_offset, 24)
        if coff[:4] != b"PE\0\0":
            raise ValueError("missing PE signature")
        machine, section_count, timestamp, _, _, optional_size, _ = struct.unpack_from("<HHIIIHH", coff, 4)
        if section_count > MAX_PE_SECTIONS:
            raise ValueError("PE section count exceeds safety limit")
        if optional_size < 96 or optional_size > 4096:
            raise ValueError("invalid PE optional header size")
        optional = reader.read(pe_offset + 24, optional_size)
        magic = struct.unpack_from("<H", optional, 0)[0]
        if magic == 0x10B:
            directory_base, count_offset, bits = 96, 92, 32
        elif magic == 0x20B:
            directory_base, count_offset, bits = 112, 108, 64
        else:
            raise ValueError("unsupported PE optional header magic")
        directory_count = struct.unpack_from("<I", optional, count_offset)[0]
        import_rva = import_size = 0
        if directory_count > 1 and optional_size >= directory_base + 16:
            import_rva, import_size = struct.unpack_from("<II", optional, directory_base + 8)

        section_offset = pe_offset + 24 + optional_size
        raw_sections = reader.read(section_offset, section_count * 40)
        sections = []
        for index in range(section_count):
            off = index * 40
            virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from("<IIII", raw_sections, off + 8)
            sections.append((virtual_address, max(virtual_size, raw_size), raw_size, raw_pointer))

        def rva_to_offset(rva: int) -> int:
            for virtual_address, span, raw_size, raw_pointer in sections:
                if virtual_address <= rva < virtual_address + span:
                    delta = rva - virtual_address
                    if delta >= raw_size:
                        raise ValueError("RVA points to unbacked virtual section data")
                    result = raw_pointer + delta
                    if result >= reader.size:
                        raise ValueError("RVA maps outside file")
                    return result
            raise ValueError("RVA does not map to a PE section")

        imports: list[str] = []
        if import_rva and import_size:
            import_offset = rva_to_offset(import_rva)
            descriptor_count = min(MAX_PE_IMPORTS, import_size // 20)
            for index in range(descriptor_count):
                descriptor = reader.read(import_offset + index * 20, 20)
                original_thunk, stamp, forwarder, name_rva, first_thunk = struct.unpack("<IIIII", descriptor)
                if not any((original_thunk, stamp, forwarder, name_rva, first_thunk)):
                    break
                if name_rva:
                    name = _c_string(reader, rva_to_offset(name_rva))
                    if name and name not in imports:
                        imports.append(name)
        return {
            "format": "PE", "bits": bits, "machine": MACHINE_NAMES.get(machine, f"unknown_0x{machine:04x}"),
            "timestamp": timestamp, "import_dlls": imports,
            "imports_truncated": bool(import_rva and import_size and len(imports) >= MAX_PE_IMPORTS),
        }
    finally:
        reader.close()

def parse_elf_needed(path: str | Path) -> dict:
    """Return ELF class, machine and DT_NEEDED names from PT_DYNAMIC."""
    reader = BoundedReader(path)
    try:
        header = reader.read(0, min(64, reader.size))
        if len(header) < 52 or header[:4] != b"\x7fELF":
            raise ValueError("missing or truncated ELF header")
        elf_class, data_encoding = header[4], header[5]
        endian = "<" if data_encoding == 1 else ">" if data_encoding == 2 else None
        if endian is None:
            raise ValueError("unsupported ELF byte order")
        if elf_class == 2:
            bits, phoff = 64, struct.unpack_from(endian + "Q", header, 32)[0]
            phentsize, phnum = struct.unpack_from(endian + "HH", header, 54)
            expected_phentsize, dyn_fmt, dyn_size = 56, endian + "qQ", 16
        elif elf_class == 1:
            bits, phoff = 32, struct.unpack_from(endian + "I", header, 28)[0]
            phentsize, phnum = struct.unpack_from(endian + "HH", header, 42)
            expected_phentsize, dyn_fmt, dyn_size = 32, endian + "iI", 8
        else:
            raise ValueError("unsupported ELF class")
        if phnum > 128 or phentsize < expected_phentsize or phoff + phentsize * phnum > reader.size:
            raise ValueError("invalid ELF program header table")

        loads: list[tuple[int, int, int, int]] = []
        dynamic: tuple[int, int] | None = None
        for i in range(phnum):
            raw = reader.read(phoff + i * phentsize, expected_phentsize)
            if bits == 64:
                p_type, p_flags, p_offset, p_vaddr, _, p_filesz, _, _ = struct.unpack(endian + "IIQQQQQQ", raw)
            else:
                p_type, p_offset, p_vaddr, _, p_filesz, _, p_flags, _ = struct.unpack(endian + "IIIIIIII", raw)
            if p_type == 1:
                loads.append((p_vaddr, p_vaddr + p_filesz, p_offset, p_filesz))
            elif p_type == 2:
                dynamic = (p_offset, p_filesz)

        machine_id = struct.unpack_from(endian + "H", header, 18)[0]
        machine = ELF_MACHINE_NAMES.get(machine_id, f"unknown_{machine_id}")
        if dynamic is None:
            return {"format": "ELF", "bits": bits, "machine": machine, "needed": [], "has_dynamic_section": False}

        dyn_offset, dyn_length = dynamic
        if dyn_length > 1024 * 1024 or dyn_offset + dyn_length > reader.size:
            raise ValueError("ELF dynamic section exceeds safety bounds")
        entries = []
        strtab_va = strtab_size = None
        dynamic_limit = min(dyn_length - dyn_size + 1, dyn_size * MAX_DYNAMIC_ENTRIES)
        for offset in range(0, max(0, dynamic_limit), dyn_size):
            tag, value = struct.unpack(dyn_fmt, reader.read(dyn_offset + offset, dyn_size))
            if tag == 0:
                break
            entries.append((tag, value))
            if tag == 5:
                strtab_va = value
            elif tag == 10:
                strtab_size = value

        needed_offsets = [value for tag, value in entries if tag == 1]
        needed: list[str] = []
        if needed_offsets:
            if strtab_va is None or strtab_size is None or strtab_size > 4 * 1024 * 1024:
                raise ValueError("ELF DT_NEEDED exists without a bounded DT_STRTAB")
            strtab_offset = None
            for start, end, file_offset, file_size in loads:
                if start <= strtab_va < end:
                    delta = strtab_va - start
                    if delta < file_size:
                        strtab_offset = file_offset + delta
                    break
            if strtab_offset is None:
                raise ValueError("ELF DT_STRTAB does not map to a PT_LOAD segment")
            for index in needed_offsets[:1024]:
                if index >= strtab_size:
                    continue
                name = _c_string(reader, strtab_offset + index, min(MAX_DEPENDENCY_NAME, strtab_size - index))
                if name and name not in needed:
                    needed.append(name)
        return {"format": "ELF", "bits": bits, "machine": machine,
                "needed": needed, "has_dynamic_section": True}
    finally:
        reader.close()

def collect_binary_evidence(root: str | Path, records) -> list:
    """Analyze a bounded number of recognized executables and emit dependency evidence."""
    from agpt.models import Evidence

    evidence = []
    candidates = [r for r in records if r.kind in {"windows_binary", "elf_binary"}][:64]
    for record in candidates:
        path = Path(root) / record.path
        try:
            result = parse_pe_imports(path) if record.kind == "windows_binary" else parse_elf_needed(path)
            deps = result.get("import_dlls", result.get("needed", []))
            evidence.append(Evidence("binary_metadata", result["format"], record.path,
                                     f'{result["bits"]}-bit {result["machine"]}; {len(deps)} direct dependencies', 2))
            for dep in deps:
                evidence.append(Evidence("binary_dependency", dep, record.path,
                                         "PE import table" if result["format"] == "PE" else "ELF DT_NEEDED", 2))
        except (OSError, ValueError, struct.error) as exc:
            evidence.append(Evidence("analysis_warning", "binary_metadata_unavailable", record.path,
                                     f"{type(exc).__name__}: {exc}", 0))
    return evidence
