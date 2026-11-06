#!/usr/bin/env python3
"""Generate a WiX v4/v6 source file for the validated Rhino.Inside payload."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET


NS = "http://wixtoolset.org/schemas/v4/wxs"
ET.register_namespace("", NS)


def tag(name: str) -> str:
    return f"{{{NS}}}{name}"


def stable_id(prefix: str, value: str) -> str:
    return prefix + hashlib.sha1(value.encode("utf-8")).hexdigest()[:24]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", default="1.37.2027")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = args.payload.resolve()
    files = sorted(path for path in payload.rglob("*") if path.is_file())
    if not files:
        raise RuntimeError(f"Payload is empty: {payload}")

    root = ET.Element(tag("Wix"))
    package = ET.SubElement(
        root,
        tag("Package"),
        {
            "Name": "Rhino.Inside Revit 2027.3 + Rhino 8 - Cycles Isolation Fix",
            "Manufacturer": "SynaptCity / Rhino.Inside Community Fix",
            "Version": args.version,
            "Language": "1046",
            "UpgradeCode": "{26B31A08-9CF4-58A3-86EA-553E50AB4997}",
            "Scope": "perUser",
            "InstallerVersion": "500",
            "Compressed": "yes",
        },
    )
    ET.SubElement(
        package,
        tag("MajorUpgrade"),
        {"DowngradeErrorMessage": "Já existe uma versão mais recente desta correção instalada."},
    )
    ET.SubElement(package, tag("MediaTemplate"), {"EmbedCab": "yes", "CompressionLevel": "high"})
    ET.SubElement(package, tag("Property"), {"Id": "ARPNOMODIFY", "Value": "1"})
    ET.SubElement(
        package,
        tag("Property"),
        {
            "Id": "ARPCOMMENTS",
            "Value": "Correção isolada para conflito ccycles/OpenImageIO/OpenVDB entre Revit 2027.3 e Rhino 8.36.",
        },
    )

    appdata = ET.SubElement(package, tag("StandardDirectory"), {"Id": "AppDataFolder"})
    autodesk = ET.SubElement(appdata, tag("Directory"), {"Id": "D_AUTODESK", "Name": "Autodesk"})
    revit = ET.SubElement(autodesk, tag("Directory"), {"Id": "D_REVIT", "Name": "Revit"})
    addins = ET.SubElement(revit, tag("Directory"), {"Id": "D_ADDINS", "Name": "Addins"})
    install = ET.SubElement(addins, tag("Directory"), {"Id": "INSTALLFOLDER", "Name": "2027"})

    directories: dict[Path, ET.Element] = {Path("."): install}
    component_ids: list[str] = []

    for file_path in files:
        relative = file_path.relative_to(payload)
        parent = relative.parent
        current = Path(".")
        for part in parent.parts:
            child = current / part
            if child not in directories:
                directories[child] = ET.SubElement(
                    directories[current],
                    tag("Directory"),
                    {"Id": stable_id("D_", child.as_posix()), "Name": part},
                )
            current = child

        logical = relative.as_posix()
        component_id = stable_id("C_", logical)
        component_ids.append(component_id)
        component = ET.SubElement(
            directories[parent if parent != Path("") else Path(".")],
            tag("Component"),
            {"Id": component_id, "Guid": "*"},
        )
        ET.SubElement(
            component,
            tag("File"),
            {
                "Id": stable_id("F_", logical),
                "Source": str(file_path),
                "KeyPath": "yes",
                "Checksum": "yes",
            },
        )

    feature = ET.SubElement(
        package,
        tag("Feature"),
        {"Id": "Complete", "Title": "Rhino.Inside Revit 2027.3 corrigido", "Level": "1"},
    )
    for component_id in component_ids:
        ET.SubElement(feature, tag("ComponentRef"), {"Id": component_id})

    ET.indent(root, space="  ")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(args.output, encoding="utf-8", xml_declaration=True)
    print(f"Generated {args.output} with {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
