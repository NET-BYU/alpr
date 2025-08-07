param(
    [Parameter(Mandatory=$false, Position=0)]
    [ValidateSet("setup", "run", "install", "clean", "autorun")]
    [string]$Action = "run"
)

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Setup-Environment {
    Write-Info "Setting up ALPR environment..."
    
    # Check if Python is available
    try {
        $version = python --version 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Python not found"
        }
        Write-Info "Found Python: $version"
    }
    catch {
        Write-Error "Python not found! Please install Python first."
        exit 1
    }
    
    # Create virtual environment
    Write-Info "Creating virtual environment..."
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment"
        exit 1
    }
    
    # Activate and install requirements
    Write-Info "Activating virtual environment..."
    & ".\.venv\Scripts\Activate.ps1"
    
    Write-Info "Installing requirements..."
    python -m pip install --upgrade pip
    python -m pip install -r req.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install requirements"
        exit 1
    }
    
    Write-Info "Setup completed successfully!"
}

function Run-Server {
    Write-Info "Starting ALPR server..."
    Set-Location -Path $PSScriptRoot
    
    # Check if virtual environment exists
    if (-not (Test-Path ".venv")) {
        Write-Error "Virtual environment not found. Run setup first: .\server.ps1 setup"
        pause
        exit 1
    }
    
    # Activate environment
    & ".\.venv\Scripts\Activate.ps1"
    
    # Check if server file exists
    if (-not (Test-Path "alpr_integrated_server.py")) {
        Write-Error "alpr_integrated_server.py not found"
        exit 1
    }
    
    Write-Info "Server starting at http://localhost:5000"
    Write-Info "Dashboard at http://localhost:5000/dashboard"
    python alpr_integrated_server.py
}

function Install-Autorun {
    Write-Info "Installing autorun task..."
    
    $scriptPath = Join-Path (Get-Location) "server.ps1"
    $taskName = "ALPR_Server_Autostart"
    
    # Remove existing task if it exists
    try {
        Get-ScheduledTask -TaskName $taskName -ErrorAction Stop | Out-Null
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Info "Removed existing task"
    }
    catch {
        Write-Info "No existing task found"
    }
    
    # Create new task
    $action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`" autorun"
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User "netlab"
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    $principal = New-ScheduledTaskPrincipal -UserId "netlab" -LogonType Interactive
    
    try {
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "ALPR Server Autostart" | Out-Null
        Write-Info "Autorun task installed successfully!"
        Write-Info "Server will start automatically when user 'netlab' logs on"
    }
    catch {
        Write-Error "Failed to install autorun task: $_"
        Write-Info "Try running as Administrator"
        exit 1
    }
}

function Clean-Data {
    Write-Info "Cleaning data files..."
    
    $filesToRemove = @(
        "event.log",
        "alpr_raw_data.jsonl", 
        "alpr_parsed_data.jsonl", 
        "alpr_vin_lookup.json"
    )
    
    foreach ($file in $filesToRemove) {
        if (Test-Path $file) {
            Remove-Item $file -Force
            Write-Info "Removed: $file"
        } else {
            Write-Info "Not found: $file"
        }
    }
    
    Write-Info "Clean completed"
}

function Start-Autorun {
    Write-Info "Starting ALPR server in autorun mode..."
    
    # Wait for system to boot
    Start-Sleep -Seconds 30
    
    # Run the server
    Run-Server
}

# Main execution
Write-Info "ALPR Server Management Script"
Write-Info "Action: $Action"
Write-Info ""

switch ($Action) {
    "setup" {
        Setup-Environment
    }
    "run" {
        Run-Server
    }
    "install" {
        Install-Autorun
    }
    "clean" {
        Clean-Data
    }
    "autorun" {
        Start-Autorun
    }
}
