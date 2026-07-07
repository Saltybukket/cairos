# CAIROS on Windows

CAIROS supports both cmd.exe and PowerShell. The commands are different.

## Environment Variables

cmd.exe current session:

```cmd
set OPENROUTER_API_KEY=your-key
```

cmd.exe persistent:

```cmd
setx OPENROUTER_API_KEY "your-key"
REM restart terminal
```

PowerShell current session:

```powershell
$env:OPENROUTER_API_KEY="your-key"
```

PowerShell persistent:

```powershell
[Environment]::SetEnvironmentVariable("OPENROUTER_API_KEY","your-key","User")
# restart terminal
```

CAIROS can generate exact Windows setup commands:

```powershell
cairos config ai key commands OPENROUTER_API_KEY --shell powershell
cairos config ai key commands OPENROUTER_API_KEY --shell cmd
```

Persistent environment changes require a new terminal before child processes
can see them.

## Command Differences

| Intent | cmd.exe | PowerShell | Unix/WSL |
| --- | --- | --- | --- |
| list files | `dir` | `Get-ChildItem` | `ls` |
| find dirs | `dir /s /b /ad *name*` | `Get-ChildItem -Directory -Recurse` | `find` |
| remove file | `del` | `Remove-Item` | `rm` |
| remove dir | `rmdir /s /q` | `Remove-Item -Recurse -Force` | `rm -rf` |
| current env | `set NAME=value` | `$env:NAME="value"` | `export NAME="value"` |

Windows `find` is a text-search command, not GNU `find`. CAIROS directory
guidance uses `dir /s /b /ad` for cmd.exe and `Get-ChildItem` for PowerShell.

Use `cd /d path` in cmd.exe when changing drives.

## PATH

Run:

```powershell
py -m pipx ensurepath
```

Then restart the terminal. `cairos setup` and `cairos install-info` print PATH
diagnostics.
