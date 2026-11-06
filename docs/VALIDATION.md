# Validation checklist

Use a disposable test model or a backed-up production model.

## Static checks

- The payload contains the expected Rhino.Inside add-in manifest.
- `CyclesIsolated/ccycles_rir.dll` exists.
- `CyclesIsolated/manifest.json` lists the isolated dependency graph.
- The managed Rhino.Inside assembly contains the resolver patch.
- Hashes of files extracted from an MSI match the staged payload.

## Installation checks

1. Close Revit.
2. Install the payload.
3. Confirm the add-in exists below `%APPDATA%\Autodesk\Revit\Addins\2027`.
4. Start Revit and confirm the Rhino.Inside ribbon loads.
5. Open a model.
6. Click **Start**.
7. Open Rhino.
8. Open Grasshopper.
9. Keep Revit running for at least 30 seconds after Grasshopper finishes loading.

## Windows event checks

Review the Application event log after the test. There should be no new event for `Revit.exe` from:

- Application Error
- .NET Runtime
- Windows Error Reporting

Specifically check for errors mentioning `ccycles`, `OpenImageIO`, `OpenVDB`, `DllNotFoundException`, `EntryPointNotFoundException`, or `0x8007007F`.

## Rollback

Close Revit, remove the test payload, and restore the backed-up add-in directory. If an MSI was used, uninstall it before restoring the backup.
