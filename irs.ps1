[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("help", "install", "init-db", "start", "stop", "analytics", "headless", "test", "status")]
    [string]$Command = "help",

    [Parameter(Position = 1)]
    [string]$Video = "",

    [int]$MaxFrames = 0,
    [int]$ZoneDwellSec = -1,
    [string]$DbHost = "localhost",
    [int]$DbPort = 5432,
    [string]$DbAdminUser = "postgres",
    [string]$DbAdminPassword = "1234",
    [switch]$NoBackend
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $Root "parking-backend"
$ApiDir = Join-Path $Root "parking-api"
$AppDir = Join-Path $Root "parking-app"
$AnalyticsDir = Join-Path $Root "parking-analytics"

function Write-Step($Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok($Message) {
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warn($Message) {
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Require-Command($Name, $InstallHint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is not installed or not in PATH. $InstallHint"
    }
}

function Ensure-Uv {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Ok "uv found: $((uv --version) -join ' ')"
        return
    }

    Write-Step "Installing uv"
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

    $CandidateDirs = @(
        Join-Path $env:USERPROFILE ".local\bin",
        Join-Path $env:USERPROFILE ".cargo\bin"
    )
    foreach ($Dir in $CandidateDirs) {
        if (Test-Path $Dir) {
            $env:Path = "$Dir;$env:Path"
        }
    }

    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw "uv was installed but is still not available in this terminal. Open a new terminal and run the command again."
    }
    Write-Ok "uv installed: $((uv --version) -join ' ')"
}

function Invoke-InDir($Dir, [string[]]$CommandArgs) {
    Push-Location $Dir
    try {
        if ($CommandArgs.Length -eq 1) {
            & $CommandArgs[0]
        }
        else {
            & $CommandArgs[0] @($CommandArgs[1..($CommandArgs.Length - 1)])
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed in ${Dir}: $($CommandArgs -join ' ')"
        }
    }
    finally {
        Pop-Location
    }
}

function Test-Port($Port) {
    $Conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return [bool]$Conn
}

function Stop-PortListeners([int[]]$Ports) {
    foreach ($Port in $Ports) {
        $ProcessIds = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique)

        if ($ProcessIds.Count -eq 0) {
            Write-Ok "Port $Port is free"
            continue
        }

        foreach ($ProcessId in $ProcessIds) {
            if ($ProcessId -eq $PID) {
                Write-Warn "Skipping current launcher process on port $Port"
                continue
            }

            $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
            $ProcessName = if ($Process) { $Process.ProcessName } else { "PID $ProcessId" }

            try {
                Stop-Process -Id $ProcessId -Force -ErrorAction Stop
                Write-Ok "Stopped $ProcessName (PID $ProcessId) on port $Port"
            }
            catch {
                Write-Warn "Could not stop $ProcessName (PID $ProcessId) on port ${Port}: $($_.Exception.Message)"
            }
        }
    }
}

function Wait-PortsFree([int[]]$Ports, [int]$TimeoutSec = 8) {
    $Deadline = (Get-Date).AddSeconds($TimeoutSec)
    do {
        $BusyPorts = @($Ports | Where-Object { Test-Port $_ })
        if ($BusyPorts.Count -eq 0) {
            return
        }
        Start-Sleep -Milliseconds 300
    } while ((Get-Date) -lt $Deadline)

    $StillBusy = @($Ports | Where-Object { Test-Port $_ })
    if ($StillBusy.Count -gt 0) {
        throw "Could not free app port(s): $($StillBusy -join ', '). Close those processes or run this terminal as Administrator, then try again."
    }
}

function Stop-AppPorts {
    Write-Step "Stopping existing app processes on ports 8000, 3001, 5173"
    $Ports = @(8000, 3001, 5173)
    Stop-PortListeners $Ports
    Wait-PortsFree $Ports
}

function Start-ServiceWindow($Title, $Dir, $CommandLine) {
    $EscapedDir = $Dir.Replace("'", "''")
    $EscapedCommand = $CommandLine.Replace("'", "''")
    $Args = @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        "Set-Location '$EscapedDir'; `$Host.UI.RawUI.WindowTitle = '$Title'; $EscapedCommand"
    )
    Start-Process powershell.exe -ArgumentList $Args
}

function Show-Help {
    @"
IRS Parking System Windows CLI

Usage:
  .\irs.cmd install
  .\irs.cmd init-db [-DbAdminPassword your-postgres-password]
  .\irs.cmd start
  .\irs.cmd stop
  .\irs.cmd analytics [video-file]
  .\irs.cmd headless [video-file] [-MaxFrames 300] [-ZoneDwellSec 0]
  .\irs.cmd test
  .\irs.cmd status

Commands:
  install     Install Python/Node dependencies with uv and npm.
  init-db     Create expected PostgreSQL role/database and initialize tables.
  start       Stop old app listeners, then start backend + frontend/API windows.
  stop        Stop app listeners on ports 8000, 3001, 5173.
  analytics   Run OpenCV GUI analytics: parking-analytics/main.py.
  headless    Run no-GUI analytics: parking-analytics/run_headless.py.
  test        Run analytics unit tests.
  status      Check ports 8000, 3001, 5173, 5432.

Required tools:
  Git, Node.js/npm, PostgreSQL, Python launcher or Python, uv.

Default URLs:
  Frontend:    http://127.0.0.1:5173
  Express API: http://127.0.0.1:3001
  Backend:     http://127.0.0.1:8000
  PostgreSQL:  localhost:5432
"@ | Write-Host
}

function Install-All {
    Write-Step "Checking required tools"
    Require-Command node "Install Node.js LTS from https://nodejs.org/"
    Require-Command npm "Install Node.js LTS from https://nodejs.org/"
    Ensure-Uv

    Write-Ok "node: $((node --version) -join ' ')"
    Write-Ok "npm: $((npm --version) -join ' ')"

    Write-Step "Installing Express API dependencies"
    Invoke-InDir $ApiDir @("npm", "install")

    Write-Step "Installing frontend dependencies"
    Invoke-InDir $AppDir @("npm", "install")

    Write-Step "Installing backend Python dependencies"
    Invoke-InDir $BackendDir @("uv", "sync")

    Write-Step "Installing analytics Python dependencies"
    Invoke-InDir $AnalyticsDir @("uv", "sync", "--dev")

    Write-Ok "Install complete"
}

function Initialize-Database {
    Write-Step "Checking PostgreSQL"
    Require-Command psql "Install PostgreSQL and add its bin folder to PATH."

    $Sql = @"
DO `$`$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'postgres') THEN
    CREATE ROLE postgres WITH LOGIN SUPERUSER PASSWORD '1234';
  ELSE
    ALTER ROLE postgres WITH LOGIN SUPERUSER PASSWORD '1234';
  END IF;
END
`$`$;

SELECT 'CREATE DATABASE parking_vkr OWNER postgres'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'parking_vkr')\gexec
"@

    $TempSql = New-TemporaryFile
    Set-Content -Path $TempSql -Value $Sql -Encoding UTF8
    $OldPgPassword = $env:PGPASSWORD
    $env:PGPASSWORD = $DbAdminPassword
    try {
        & psql -h $DbHost -p $DbPort -U $DbAdminUser -d postgres -f $TempSql
        if ($LASTEXITCODE -ne 0) {
            throw "psql failed. Make sure PostgreSQL service is running and pass the installer password with: .\irs.cmd init-db -DbAdminPassword <password>"
        }
    }
    finally {
        if ($null -eq $OldPgPassword) {
            Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
        }
        else {
            $env:PGPASSWORD = $OldPgPassword
        }
        Remove-Item $TempSql -Force -ErrorAction SilentlyContinue
    }

    Write-Step "Initializing backend tables"
    Invoke-InDir $BackendDir @("uv", "run", "python", "database.py")
    Write-Ok "Database initialized"
}

function Start-Stack {
    Stop-AppPorts

    Write-Step "Starting backend"
    Start-ServiceWindow "IRS Backend :8000" $BackendDir "uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000"

    Write-Step "Starting frontend + Express API"
    Start-ServiceWindow "IRS Frontend :5173 + API :3001" $AppDir "npm run dev -- --host 127.0.0.1"

    Write-Host ""
    Write-Host "Started service windows. Give them a few seconds, then open:" -ForegroundColor Green
    Write-Host "  http://127.0.0.1:5173"
    Write-Host ""
    Write-Host "Health checks:"
    Write-Host "  http://127.0.0.1:8000/health"
    Write-Host "  http://127.0.0.1:3001/api/health"
}

function Run-Analytics([bool]$Headless) {
    Ensure-Uv
    Push-Location $AnalyticsDir
    try {
        $env:PARKING_BACKEND_ENABLED = if ($NoBackend) { "0" } else { "1" }
        $env:PARKING_BACKEND_URL = "http://127.0.0.1:8000"
        if ($ZoneDwellSec -ge 0) {
            $env:ZONE_DWELL_SEC = [string]$ZoneDwellSec
        }
        if ($MaxFrames -gt 0) {
            $env:ANALYTICS_MAX_FRAMES = [string]$MaxFrames
        }

        $Script = if ($Headless) { "run_headless.py" } else { "main.py" }
        $Args = @("run", "python", $Script)
        if ($Video) {
            $Args += $Video
        }

        & uv @Args
        if ($LASTEXITCODE -ne 0) {
            throw "Analytics exited with code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

function Run-Tests {
    Ensure-Uv
    Invoke-InDir $AnalyticsDir @("uv", "run", "pytest", "-q")
}

function Show-Status {
    $Ports = @(
        @{ Port = 5432; Name = "PostgreSQL" },
        @{ Port = 8000; Name = "FastAPI backend" },
        @{ Port = 3001; Name = "Express API" },
        @{ Port = 5173; Name = "Vue frontend" }
    )
    foreach ($Item in $Ports) {
        $Listening = Test-Port $Item.Port
        $State = if ($Listening) { "LISTENING" } else { "not listening" }
        Write-Host ("{0,-16} : {1,5} : {2}" -f $Item.Name, $Item.Port, $State)
    }
}

switch ($Command) {
    "help" { Show-Help }
    "install" { Install-All }
    "init-db" { Initialize-Database }
    "start" { Start-Stack }
    "stop" { Stop-AppPorts }
    "analytics" { Run-Analytics $false }
    "headless" { Run-Analytics $true }
    "test" { Run-Tests }
    "status" { Show-Status }
}
