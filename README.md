# Rhino.Inside.Revit 2027 Cycles isolation fix

Community workaround for a native-library collision observed when **Rhino.Inside.Revit runs Rhino 8 inside Autodesk Revit 2027.3**.

## What this resolves

On affected installations, Revit can close while starting Rhino or Grasshopper. The failure appears in RhinoCycles/cycles as a native load error such as:

- `DllNotFoundException` or error `0x8007007F`;
- failure to load `ccycles.dll`;
- “The specified procedure could not be found”;
- Revit exits shortly after **Rhino.Inside > Start**, **Rhino**, or **Grasshopper**.

## Root cause

Revit and RhinoCycles can load native DLLs with identical base names but incompatible exports, especially OpenImageIO/OpenVDB dependencies. Windows may reuse a module already loaded by Revit instead of the Rhino version expected by `ccycles.dll`.

## Fix strategy

This repository contains a source-level workaround that:

1. discovers the complete native dependency graph starting at Rhino 8's `ccycles.dll`;
2. copies the graph into an isolated directory;
3. assigns private, same-length filenames to the copied dependencies;
4. rewrites PE import names so Windows cannot bind them to Revit's already-loaded modules;
5. installs a .NET `NativeLibrary.SetDllImportResolver` for every `csycles` assembly load context.

## Validated environment

- Windows 11 x64
- Autodesk Revit 2027.3
- Rhino 8.36.26296.17001
- Rhino.Inside.Revit community build 1.37.0
- Rhino and Grasshopper opened inside Revit and remained stable with no new Application Error/.NET Runtime crash event.

This is a narrow compatibility workaround, not an official McNeel or Autodesk release.

## Repository contents

- `patches/rhinoceros-cycles-resolver.patch` — managed resolver patch for the upstream Rhino.Inside.Revit source.
- `scripts/prepare_cycles_isolation.py` — copies the installed RhinoCycles native graph and patches PE import names.
- `scripts/build_rir_custom_msi.py` — generates WiX v4/v6 source for a locally prepared payload.
- `docs/INSTALL.md` — build and deployment workflow.
- `docs/VALIDATION.md` — verification checklist.

## Important licensing note

No Rhino, Autodesk, RhinoCycles or Rhino.Inside binaries are distributed here. Build the payload locally from software you are licensed to use. The locally validated MSI is intentionally not attached because it contains files from an installed Rhino distribution.

The upstream Rhino.Inside.Revit source is available under the MIT License:  
https://github.com/mcneel/rhino.inside-revit

## Safety

- Close Revit before replacing add-in files.
- Back up the existing Revit add-in directory.
- Do not install a payload built from a different Rhino build without rebuilding the isolated dependency graph.
- A valid Rhino installation and license are still required.

## Trademarks

Rhino and Grasshopper are trademarks of Robert McNeel & Associates. Revit and Autodesk are trademarks of Autodesk, Inc. This community project is not affiliated with or endorsed by either company.

## License

The original material in this repository is provided under the MIT License. Upstream and third-party components remain under their respective licenses.
