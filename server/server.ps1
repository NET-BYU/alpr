param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("setup", "run", "clean")]
    [string]$Action
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

function Test-PythonInstalled {
    Write-Info "Checking if Python is installed..."
    
    $pythonCommands = @("python", "python3", "python3.10", "python3.11", "python3.12")
    
    foreach ($cmd in $pythonCommands) {
        try {
            $version = & $cmd --version 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Info "Found Python: $version using command '$cmd'"
                return $cmd
            }
        }
        catch {
            # Command not found, continue to next
        }
    }
    
    Write-Error "Python not found! Please install Python from the Microsoft Store or python.org"
    Write-Info "Recommended: Install Python 3.10+ from Microsoft Store"
    exit 1
}

function Test-VenvExists {
    Write-Info "Checking if virtual environment exists..."
    
    if (Test-Path ".venv") {
        Write-Info "Virtual environment found at .venv"
        return $true
    } else {
        Write-Warning "Virtual environment not found"
        return $false
    }
}

function New-VirtualEnvironment {
    param([string]$PythonCmd)
    
    Write-Info "Creating virtual environment..."
    
    try {
        & $PythonCmd -m venv .venv
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create virtual environment"
        }
        Write-Info "Virtual environment created successfully"
    }
    catch {
        Write-Error "Failed to create virtual environment: $_"
        exit 1
    }
}

function Enter-VirtualEnvironment {
    Write-Info "Activating virtual environment..."
    
    $activateScript = ".\.venv\Scripts\Activate.ps1"
    
    if (Test-Path $activateScript) {
        try {
            & $activateScript
            Write-Info "Virtual environment activated"
        }
        catch {
            Write-Error "Failed to activate virtual environment: $_"
            exit 1
        }
    } else {
        Write-Error "Virtual environment activation script not found at $activateScript"
        exit 1
    }
}

function Install-Requirements {
    Write-Info "Installing required packages..."
    
    try {
        python -m pip install --upgrade pip
        python -m pip install -r req.txt
        
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install packages"
        }
        
        Write-Info "Required packages installed successfully"
    }
    catch {
        Write-Error "Failed to install requirements: $_"
        exit 1
    }
}

function Start-Server {
    Write-Info "Starting ALPR Integrated Server..."
    
    if (-not (Test-Path "alpr_integrated_server.py")) {
        Write-Error "alpr_integrated_server.py not found in current directory"
        Write-Info "Make sure you're running this script from the correct directory"
        exit 1
    }
    
    try {
        Write-Info "Server will be available at: http://localhost:5000"
        Write-Info "Dashboard available at: http://localhost:5000/dashboard"
        Write-Info "Press Ctrl+C to stop the server"
        Write-Info ""
        
        python alpr_integrated_server.py
    }
    catch {
        Write-Error "Failed to start server: $_"
        exit 1
    }
}

function Setup-Environment {
    Write-Info "Setting up ALPR Integrated Server environment..."
    
    # Check if Python is installed
    $pythonCmd = Test-PythonInstalled
    
    # Check if venv exists, create if not
    if (-not (Test-VenvExists)) {
        New-VirtualEnvironment -PythonCmd $pythonCmd
    }
    
    # Activate virtual environment
    Enter-VirtualEnvironment
    
    # Install requirements
    Install-Requirements
    
    Write-Info ""
    Write-Info "Setup completed successfully!"
    Write-Info "To run the server, use: .\server.ps1 run"
    Write-Info ""
}

function Run-Server {
    Write-Info "Running ALPR Integrated Server..."
    
    # Check if Python is installed
    $pythonCmd = Test-PythonInstalled
    
    # Check if venv exists
    if (-not (Test-VenvExists)) {
        Write-Error "Virtual environment not found. Please run setup first:"
        Write-Info ".\server.ps1 setup"
        exit 1
    }
    
    # Activate virtual environment
    Enter-VirtualEnvironment
    
    # Start the server
    Start-Server
}

function Clean-Environment {
    Write-Info "Cleaning plates folder and removing data/log files..."

    $platesFolder = "plates"
    $filesToRemove = @("alpr_parsed_data.jsonl", "alpr_raw_data.jsonl", "event.log", "alpr_vin_lookup.json")

    # Remove all files in plates folder
    if (Test-Path $platesFolder) {
        try {
            Get-ChildItem -Path $platesFolder -File | Remove-Item -Force
            Write-Info "Cleaned all files in '$platesFolder'"
        }
        catch {
            Write-Warning "Failed to clean some files in '$platesFolder': $_"
        }
    } else {
        Write-Warning "'$platesFolder' folder does not exist"
    }

    # Remove specific files
    foreach ($file in $filesToRemove) {
        if (Test-Path $file) {
            try {
                Remove-Item $file -Force
                Write-Info "Removed file: $file"
            }
            catch {
                Write-Warning "Failed to remove file: $file"
            }
        } else {
            Write-Info "File not found (skipped): $file"
        }
    }

    Write-Info "Clean operation completed."
}

# Main script execution
Write-Info "ALPR Integrated Server Setup Script"
Write-Info "Action: $Action"
Write-Info ""

switch ($Action) {
    "setup" {
        Setup-Environment
    }
    "run" {
        Run-Server
    }
    "clean" {
        Clean-Environment
    }
}