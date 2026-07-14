#!/usr/bin/env python3
"""Build the strict capture probe and reject input-capable PE imports."""

from __future__ import annotations

import os
import struct
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Set


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "src-tauri" / "Cargo.toml"
PROBE_NAME = "strict_capture_probe"
BANNED_IMPORTS = {
    "Post" + "MessageA",
    "Post" + "MessageW",
    "Send" + "Input",
    "Set" + "ForegroundWindow",
    "Set" + "Focus",
    "Set" + "CursorPos",
    "mouse" + "_event",
    "keybd" + "_event",
    "Shell" + "ExecuteW",
}


def read_c_string(data: bytes, offset: int) -> str:
    end = data.find(b"\0", offset)
    if offset < 0 or end < 0:
        raise RuntimeError("invalid PE string offset")
    return data[offset:end].decode("ascii", "replace")


def rva_to_offset(rva: int, sections: Iterable[tuple[int, int, int, int]]) -> int:
    for virtual_address, virtual_size, raw_size, raw_offset in sections:
        span = max(virtual_size, raw_size)
        if virtual_address <= rva < virtual_address + span:
            return raw_offset + rva - virtual_address
    raise RuntimeError("PE RVA does not map to a section: 0x{:x}".format(rva))


def imported_symbols(path: Path) -> Set[str]:
    data = path.read_bytes()
    if data[:2] != b"MZ" or len(data) < 0x40:
        raise RuntimeError("probe binary is not a PE executable")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise RuntimeError("probe binary has an invalid PE signature")
    file_header = pe_offset + 4
    section_count = struct.unpack_from("<H", data, file_header + 2)[0]
    optional_size = struct.unpack_from("<H", data, file_header + 16)[0]
    optional_header = file_header + 20
    magic = struct.unpack_from("<H", data, optional_header)[0]
    if magic == 0x20B:
        directory_offset = optional_header + 112
        thunk_size = 8
        ordinal_mask = 1 << 63
    elif magic == 0x10B:
        directory_offset = optional_header + 96
        thunk_size = 4
        ordinal_mask = 1 << 31
    else:
        raise RuntimeError("probe binary has an unsupported PE optional header")
    import_rva, _ = struct.unpack_from("<II", data, directory_offset + 8)
    if import_rva == 0:
        return set()
    sections = []
    section_offset = optional_header + optional_size
    for index in range(section_count):
        offset = section_offset + index * 40
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from("<IIII", data, offset + 8)
        sections.append((virtual_address, virtual_size, raw_size, raw_offset))

    imports: Set[str] = set()
    descriptor_offset = rva_to_offset(import_rva, sections)
    while True:
        original_thunk, _, _, name_rva, first_thunk = struct.unpack_from(
            "<IIIII", data, descriptor_offset
        )
        if not any((original_thunk, name_rva, first_thunk)):
            break
        dll_name = read_c_string(data, rva_to_offset(name_rva, sections))
        thunk_rva = original_thunk or first_thunk
        thunk_offset = rva_to_offset(thunk_rva, sections)
        while True:
            if thunk_size == 8:
                thunk_value = struct.unpack_from("<Q", data, thunk_offset)[0]
            else:
                thunk_value = struct.unpack_from("<I", data, thunk_offset)[0]
            if thunk_value == 0:
                break
            if not thunk_value & ordinal_mask:
                symbol_offset = rva_to_offset(thunk_value, sections) + 2
                imports.add("{}!{}".format(dll_name.lower(), read_c_string(data, symbol_offset)))
            thunk_offset += thunk_size
        descriptor_offset += 20
    return imports


def run(command: list[str]) -> None:
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("command failed: {}\n{}".format(" ".join(command), completed.stdout))


def main() -> int:
    if os.name != "nt":
        print("strict capture probe PE import test skipped outside Windows")
        return 0
    test_command = ["cargo", "test", "--manifest-path", str(MANIFEST), "--bin", PROBE_NAME]
    build_command = ["cargo", "build", "--manifest-path", str(MANIFEST), "--bin", PROBE_NAME]
    run(test_command)
    run(build_command)
    binary = ROOT / "src-tauri" / "target" / "debug" / "{}.exe".format(PROBE_NAME)
    if not binary.is_file():
        raise RuntimeError("probe binary is missing after cargo build: {}".format(binary))
    imports = imported_symbols(binary)
    imported_names = {item.rsplit("!", 1)[-1] for item in imports}
    forbidden = sorted(BANNED_IMPORTS & imported_names)
    if forbidden:
        raise RuntimeError("strict capture probe imports forbidden APIs: {}".format(", ".join(forbidden)))
    print("probeBinary={}".format(binary))
    print("peImports={}".format(len(imports)))
    print("forbiddenInputImports=0")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("strict capture probe binary test failed: {}".format(exc), file=sys.stderr)
        sys.exit(1)
