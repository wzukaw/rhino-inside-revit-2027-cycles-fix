#!/usr/bin/env python3
"""Build an isolated native dependency set for Rhino Cycles on Windows.

Revit and Rhino ship incompatible DLLs with identical base names (notably
OpenImageIO and OpenVDB).  The Windows loader may reuse Revit's already-loaded
copy when RhinoCycles loads ccycles.dll.  This script copies the complete
Rhino Cycles native dependency graph and rewrites internal import names so the
loader cannot bind those imports to Revit's modules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rhino", type=Path, required=True, help="Rhino 8 install root")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pefile-path", type=Path)
    return parser.parse_args()


def import_pefile(extra_path: Path | None):
    if extra_path:
        sys.path.insert(0, str(extra_path))
    import pefile  # type: ignore

    return pefile


def index_dlls(roots: list[Path]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file():
                result.setdefault(path.name.lower(), path)
    return result


def imports_for(pefile, path: Path) -> list[str]:
    pe = pefile.PE(str(path), fast_load=True)
    directories = [pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]]
    delay_key = "IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"
    if delay_key in pefile.DIRECTORY_ENTRY:
        directories.append(pefile.DIRECTORY_ENTRY[delay_key])
    pe.parse_data_directories(directories=directories)
    names = [entry.dll.decode("ascii") for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", [])]
    names.extend(entry.dll.decode("ascii") for entry in getattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT", []))
    pe.close()
    return names


def dependency_graph(pefile, index: dict[str, Path], start: Path) -> dict[str, Path]:
    graph: dict[str, Path] = {}
    pending = [start]
    while pending:
        path = pending.pop()
        key = path.name.lower()
        if key in graph:
            continue
        graph[key] = path
        for imported in imports_for(pefile, path):
            dependency = index.get(imported.lower())
            if dependency and dependency.name.lower() not in graph:
                pending.append(dependency)
    return graph


def isolated_name(name: str) -> str:
    # PE import names are patched in place, so the replacement must have the
    # exact same byte length.  Changing the first character is sufficient to
    # create a private module namespace for this deployment.
    first = "z" if name[0].lower() != "z" else "q"
    return first + name[1:]


def patch_import_names(pefile, source: Path, destination: Path, mapping: dict[str, str]) -> None:
    shutil.copy2(source, destination)
    pe = pefile.PE(str(destination), fast_load=False)
    entries = list(getattr(pe, "DIRECTORY_ENTRY_IMPORT", []))
    entries.extend(getattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT", []))
    data = bytearray(destination.read_bytes())
    changes = 0
    for entry in entries:
        old = entry.dll.decode("ascii")
        new = mapping.get(old.lower())
        if not new:
            continue
        if len(old.encode("ascii")) != len(new.encode("ascii")):
            raise ValueError(f"Import replacement length mismatch: {old!r} -> {new!r}")
        name_rva = getattr(entry.struct, "Name", None)
        if name_rva is None:
            name_rva = getattr(entry.struct, "szName", None)
        if name_rva is None:
            raise ValueError(f"Cannot locate import name RVA for {old!r} in {source}")
        offset = pe.get_offset_from_rva(name_rva)
        data[offset : offset + len(old)] = new.encode("ascii")
        changes += 1
    pe.close()
    destination.write_bytes(data)
    if source.name.lower() != "ccycles.dll" and changes == 0:
        # Leaf libraries are expected and do not require rewritten imports.
        return


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    pefile = import_pefile(args.pefile_path)
    roots = [args.rhino / "Plug-ins", args.rhino / "System"]
    index = index_dlls(roots)
    start = index.get("ccycles.dll")
    if not start:
        raise FileNotFoundError("ccycles.dll was not found below the Rhino installation")

    graph = dependency_graph(pefile, index, start)
    dependencies = {name: path for name, path in graph.items() if name != "ccycles.dll"}
    mapping = {name: isolated_name(path.name) for name, path in dependencies.items()}

    args.output.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "rhino_root": str(args.rhino.resolve()),
        "source_ccycles": str(start),
        "imports": mapping,
        "files": [],
    }

    destination = args.output / "ccycles_rir.dll"
    patch_import_names(pefile, start, destination, mapping)
    manifest["files"].append({"name": destination.name, "sha256": sha256(destination)})

    for name, source in sorted(dependencies.items()):
        destination = args.output / mapping[name]
        patch_import_names(pefile, source, destination, mapping)
        manifest["files"].append(
            {"name": destination.name, "source": str(source), "sha256": sha256(destination)}
        )

    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + os.linesep,
        encoding="utf-8",
    )
    print(f"Prepared {len(graph)} isolated Cycles modules in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
