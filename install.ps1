# Uplifted One-Click Installation Script for Windows
# PowerShell 5.1+ required
# Run as: powershell -ExecutionPolicy Bypass -File install.ps1

#Requires -Version 5.1

# Configuration
$ErrorActionPreference = "Stop"
$InstallDir = if ($env:UPLIFTED_INSTALL_DIR) { $env:UPLIFTED_INSTALL_DIR } else { "$env:USERPROFILE\.uplifted" }
$PythonMinVersion = [Version]"3.10"
$RepoUrl = "https://github.com/uplifted/uplifted.git"
$Branch = if ($env:UPLIFTED_BRANCH) { $env:UPLIFTED_BRANCH } else { "main" }

# Colors
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White",
        [string]$Prefix = ""
    )

    $prefixColors = @{
        "INFO" = "Cyan"
        "SUCCESS" = "Green"
        "WARNING" = "Yellow"
        "ERROR" = "Red"
        "STEP" = "Magenta"
    }

    if ($Prefix -and $prefixColors.ContainsKey($Prefix)) {
        Write-Host "[$Prefix] " -ForegroundColor $prefixColors[$Prefix] -NoNewline
    }
    Write-Host $Message -ForegroundColor $Color
}

function Write-Info { Write-ColorOutput $args[0] -Prefix "INFO" }
function Write-Success { Write-ColorOutput $args[0] -Prefix "SUCCESS" }
function Write-Warning { Write-ColorOutput $args[0] -Prefix "WARNING" }
function Write-Error { Write-ColorOutput $args[0] -Prefix "ERROR" }
function Write-Step { param($StepNum, $Message) Write-ColorOutput $Message -Prefix "STEP $StepNum" }

# Print banner
function Print-Banner {
    Write-Host @"

    _   _       _ _  __ _           _
   | | | |_ __ | (_)/ _| |_ ___  __| |
   | | | | '_ \| | | |_| __/ _ \/ _\` |
   | |_| | |_) | | |  _| ||  __/ (_| |
    \___/| .__/|_|_|_|  \__\___|\__,_|
         |_|

    One-Click Installation Script for Windows

"@ -ForegroundColor Cyan
}

# Check if running as Administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Check Python installation
function Test-Python {
    Write-Step 1 "Checking Python installation..."

    try {
        $pythonCmd = Get-Command python -ErrorAction Stop
        $pythonVersion = & python --version 2>&1
        Write-Info "Found: $pythonVersion"

        # Get version number
        $versionMatch = $pythonVersion -match "Python (\d+\.\d+\.\d+)"
        if ($versionMatch) {
            $installedVersion = [Version]$matches[1]

            if ($installedVersion -lt $PythonMinVersion) {
                Write-Error "Python $PythonMinVersion or higher is required. Found: $installedVersion"
                Write-Info "Download from: https://www.python.org/downloads/"
                exit 1
            }

            Write-Success "Python version check passed"
            return $true
        }
    }
    catch {
        Write-Error "Python not found in PATH"
        Write-Info "Please install Python $PythonMinVersion or higher from:"
        Write-Info "https://www.python.org/downloads/"
        Write-Info ""
        Write-Info "Make sure to check 'Add Python to PATH' during installation"
        exit 1
    }
}

# Install system dependencies
function Install-SystemDeps {
    Write-Step 2 "Checking system dependencies..."

    # Check for Git
    try {
        $gitCmd = Get-Command git -ErrorAction Stop
        Write-Info "Git found: $($gitCmd.Version)"
    }
    catch {
        Write-Warning "Git not found"
        Write-Info "Installing Git..."

        # Check if winget is available
        try {
            winget install --id Git.Git -e --source winget --silent
            Write-Success "Git installed"

            # Refresh PATH
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        }
        catch {
            Write-Error "Failed to install Git automatically"
            Write-Info "Please install Git manually from: https://git-scm.com/download/win"
            exit 1
        }
    }

    # Check for Visual C++ Build Tools (optional but recommended)
    Write-Info "Checking for Visual C++ Build Tools..."
    $vsBuildToolsPath = "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Tools\MSVC"
    if (-not (Test-Path $vsBuildToolsPath)) {
        Write-Warning "Visual C++ Build Tools not found (optional)"
        Write-Info "Some packages may require compilation"
        Write-Info "Download from: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2019"
    }

    Write-Success "System dependencies check complete"
}

# Clone or update repository
function Setup-Repository {
    Write-Step 3 "Setting up repository..."

    if (Test-Path $InstallDir) {
        Write-Warning "Installation directory already exists: $InstallDir"
        $response = Read-Host "Update existing installation? (Y/n)"

        if ($response -match "^[Nn]$") {
            Write-Info "Skipping repository setup"
            return
        }

        Write-Info "Updating existing installation..."
        Push-Location $InstallDir
        git pull origin $Branch
        Pop-Location
    }
    else {
        Write-Info "Cloning repository to $InstallDir..."
        git clone --branch $Branch $RepoUrl $InstallDir
    }

    Write-Success "Repository setup complete"
}

# Setup Python environment
function Setup-PythonEnv {
    Write-Step 4 "Setting up Python environment..."

    Push-Location $InstallDir

    # Create virtual environment
    if (-not (Test-Path "venv")) {
        Write-Info "Creating virtual environment..."
        python -m venv venv
    }
    else {
        Write-Info "Virtual environment already exists"
    }

    # Activate virtual environment
    Write-Info "Activating virtual environment..."
    & ".\venv\Scripts\Activate.ps1"

    # Upgrade pip
    Write-Info "Upgrading pip..."
    python -m pip install --upgrade pip --quiet

    # Install uv
    Write-Info "Installing uv..."
    pip install uv --quiet

    # Install dependencies
    Write-Info "Installing dependencies (this may take a few minutes)..."
    uv pip install -e .

    Pop-Location

    Write-Success "Python environment setup complete"
}

# Generate configuration
function Generate-Config {
    Write-Step 5 "Generating configuration..."

    Push-Location $InstallDir

    # Activate venv
    & ".\venv\Scripts\Activate.ps1"

    # Create directories
    $dirs = @("config", "data", "logs", "plugins")
    foreach ($dir in $dirs) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir | Out-Null
        }
    }

    # Generate default configuration
    $configFile = "config\config.yaml"
    if (-not (Test-Path $configFile)) {
        Write-Info "Generating default configuration..."

        $pythonScript = @"
from uplifted.extensions import generate_config_template
generate_config_template('development', 'config/config.yaml')
print('Configuration generated: config/config.yaml')
"@

        python -c $pythonScript
    }
    else {
        Write-Info "Configuration already exists: $configFile"
    }

    # Copy environment template
    if (-not (Test-Path ".env")) {
        Write-Info "Creating .env file..."
        Copy-Item ".env.example" ".env"
        Write-Warning "Please edit .env and add your API keys"
    }

    Pop-Location

    Write-Success "Configuration generated"
}

# Create Windows Service (optional)
function Create-WindowsService {
    Write-Step 6 "Setting up Windows Service (optional)..."

    if (-not (Test-Administrator)) {
        Write-Warning "Administrator privileges required to create Windows Service"
        Write-Info "Skipping service creation"
        return
    }

    $response = Read-Host "Install as Windows Service? (Y/n)"
    if ($response -match "^[Nn]$") {
        Write-Info "Skipping service setup"
        return
    }

    Write-Info "Creating Windows Service..."

    # Check if NSSM is available
    try {
        $nssmCmd = Get-Command nssm -ErrorAction Stop
        Write-Info "NSSM found"
    }
    catch {
        Write-Warning "NSSM not found"
        Write-Info "Installing NSSM..."

        try {
            choco install nssm -y
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine")
        }
        catch {
            Write-Warning "Failed to install NSSM automatically"
            Write-Info "Please install NSSM manually: choco install nssm"
            Write-Info "Or download from: https://nssm.cc/download"
            return
        }
    }

    # Install service
    $pythonPath = Join-Path $InstallDir "venv\Scripts\python.exe"
    $scriptPath = Join-Path $InstallDir "server\run_main_server.py"

    nssm install Uplifted $pythonPath "-m" "server.run_main_server"
    nssm set Uplifted AppDirectory $InstallDir
    nssm set Uplifted DisplayName "Uplifted AI Agent System"
    nssm set Uplifted Description "Uplifted AI Agent System"
    nssm set Uplifted Start SERVICE_AUTO_START

    Write-Success "Windows Service created: Uplifted"
    Write-Info "Start with: net start Uplifted"
    Write-Info "Stop with: net stop Uplifted"
}

# Create launcher scripts
function Create-Launchers {
    Write-Step 7 "Creating launcher scripts..."

    Push-Location $InstallDir

    # Create start script
    $startScript = @"
@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python -m server.run_main_server
pause
"@
    Set-Content -Path "start.bat" -Value $startScript

    # Create stop script
    $stopScript = @"
@echo off
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *run_main_server*"
"@
    Set-Content -Path "stop.bat" -Value $stopScript

    # Create status script
    $statusScript = @"
@echo off
tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq *run_main_server*" | find "python.exe" >nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Uplifted is running
) else (
    echo [X] Uplifted is not running
)
pause
"@
    Set-Content -Path "status.bat" -Value $statusScript

    # Create PowerShell launcher
    $psLauncher = @"
# Uplifted Launcher
`$InstallDir = "$InstallDir"
Set-Location `$InstallDir
& "`$InstallDir\venv\Scripts\Activate.ps1"
python -m server.run_main_server
"@
    Set-Content -Path "start.ps1" -Value $psLauncher

    Pop-Location

    Write-Success "Launcher scripts created"
}

# Create desktop shortcut (optional)
function Create-DesktopShortcut {
    Write-Step 8 "Creating desktop shortcut (optional)..."

    $response = Read-Host "Create desktop shortcut? (Y/n)"
    if ($response -match "^[Nn]$") {
        Write-Info "Skipping shortcut creation"
        return
    }

    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Uplifted.lnk")
    $Shortcut.TargetPath = "powershell.exe"
    $Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$InstallDir\start.ps1`""
    $Shortcut.WorkingDirectory = $InstallDir
    $Shortcut.IconLocation = "powershell.exe"
    $Shortcut.Description = "Start Uplifted AI Agent System"
    $Shortcut.Save()

    Write-Success "Desktop shortcut created"
}

# Print summary
function Print-Summary {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  Installation Complete!" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "Installation Directory: " -NoNewline
    Write-Host $InstallDir -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Quick Start:" -ForegroundColor Cyan
    Write-Host "  1. Edit configuration: " -NoNewline
    Write-Host "notepad $InstallDir\.env" -ForegroundColor Yellow
    Write-Host "  2. Add your API keys (OpenAI, Anthropic, etc.)"
    Write-Host "  3. Start server: " -NoNewline
    Write-Host "cd $InstallDir && .\start.bat" -ForegroundColor Yellow
    Write-Host "  4. Access API: " -NoNewline
    Write-Host "http://localhost:7541" -ForegroundColor Yellow
    Write-Host "  5. API Docs: " -NoNewline
    Write-Host "http://localhost:7541/docs" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Management Commands:" -ForegroundColor Cyan
    Write-Host "  Start: " -NoNewline
    Write-Host "$InstallDir\start.bat" -ForegroundColor Yellow
    Write-Host "  Stop: " -NoNewline
    Write-Host "$InstallDir\stop.bat" -ForegroundColor Yellow
    Write-Host "  Status: " -NoNewline
    Write-Host "$InstallDir\status.bat" -ForegroundColor Yellow

    if (Get-Service -Name "Uplifted" -ErrorAction SilentlyContinue) {
        Write-Host ""
        Write-Host "Windows Service:" -ForegroundColor Cyan
        Write-Host "  Start: " -NoNewline
        Write-Host "net start Uplifted" -ForegroundColor Yellow
        Write-Host "  Stop: " -NoNewline
        Write-Host "net stop Uplifted" -ForegroundColor Yellow
        Write-Host "  Status: " -NoNewline
        Write-Host "sc query Uplifted" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "Documentation:" -ForegroundColor Cyan
    Write-Host "  Configuration: $InstallDir\docs\CONFIG_MANAGEMENT.md"
    Write-Host "  Deployment: $InstallDir\docs\DEPLOYMENT.md"
    Write-Host "  API Usage: $InstallDir\examples\API_USAGE.md"
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
}

# Main installation flow
function Main {
    try {
        Print-Banner

        Write-Info "Starting Uplifted installation for Windows..."
        Write-Host ""

        Test-Python
        Install-SystemDeps
        Setup-Repository
        Setup-PythonEnv
        Generate-Config
        Create-WindowsService
        Create-Launchers
        Create-DesktopShortcut

        Print-Summary
    }
    catch {
        Write-Host ""
        Write-Error "Installation failed: $_"
        Write-Host $_.ScriptStackTrace
        exit 1
    }
}

# Run main function
Main
