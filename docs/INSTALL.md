# Local build and installation

## Prerequisites

- Autodesk Revit 2027.3
- A licensed Rhino 8 installation
- Rhino.Inside.Revit source from the upstream `1.x` branch
- Python 3
- Python package `pefile`
- Visual Studio/.NET requirements used by the upstream project
- WiX Toolset 6 if a local MSI is required

## 1. Apply the managed resolver patch

From a clean upstream checkout:

```powershell
git apply patches/rhinoceros-cycles-resolver.patch
```

Build Rhino.Inside.Revit for Revit 2027 and Rhino 8 using the upstream instructions.

## 2. Prepare the isolated Cycles native graph

Example:

```powershell
py -m pip install pefile
py scripts/prepare_cycles_isolation.py `
  --rhino "C:\Program Files\Rhino 8" `
  --output "<payload>\RhinoInside.Revit\R8\CyclesIsolated"
```

The output must contain `ccycles_rir.dll`, renamed dependencies, and `manifest.json`.

## 3. Assemble the add-in payload

The payload root should contain:

```text
RhinoInside.Revit.addin
RhinoInside.Revit\
  ...
  R8\
    CyclesIsolated\
      ccycles_rir.dll
      manifest.json
      ...
```

Copy the payload to:

```text
%APPDATA%\Autodesk\Revit\Addins\2027
```

Close Revit before copying. Back up the previous add-in directory first.

## 4. Optional local MSI

Generate WiX source:

```powershell
py scripts/build_rir_custom_msi.py `
  --payload "<payload>" `
  --output "RhinoInside.Revit.Fixed.wxs" `
  --version "1.37.2027"
```

Compile with WiX 6:

```powershell
wix build RhinoInside.Revit.Fixed.wxs -arch x64 -out RhinoInside.Revit.Fixed.msi
```

Do not redistribute an MSI containing Rhino binaries unless you have confirmed that you possess the necessary redistribution rights.

## 5. First start

Start Revit. If Revit shows its unsigned add-in warning, review the local build and choose the appropriate load option. Then open a model and test **Rhino.Inside > Start**, **Rhino**, and **Grasshopper**.
