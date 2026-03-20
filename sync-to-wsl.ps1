# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    PROFETA WSL SYNC SCRIPT
# ═══════════════════════════════════════════════════════════════════════════════════════════
#
# Description: Synchronizes PROFETA project from Windows to WSL (Ubuntu 24.04)
# Author: BilliDynamics™
# Date: March 2026
#
# Usage: .\sync-to-wsl.ps1
#
# ═══════════════════════════════════════════════════════════════════════════════════════════

# Configuration
$WindowsSource = "C:\work\gitrepo\Profeta"
$WSLDestination = "\\wsl.localhost\Ubuntu-24.04\home\ubuntu\Profeta"

# Files and folders to exclude from sync
$ExcludeDirs = @(
    "__pycache__",
    "logs",
    "models",
    "output",
    "reports",
    ".git",
    "conda",
    "venv",
    ".venv"
)

$ExcludeFiles = @(
    "*.pyc",
    "*.log",
    "*.md~",
    ".DS_Store"
)

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    SYNC FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════════════════

function Sync-Projeto {
    param(
        [switch]$DryRun,
        [switch]$Verbose
    )

    Write-Host "╔══════════════════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║                    PROFETA - WSL Synchronization Script                                  ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""

    # Check if WSL path exists
    if (-not (Test-Path $WSLDestination)) {
        Write-Host "❌ WSL destination not found: $WSLDestination" -ForegroundColor Red
        Write-Host "   Make sure WSL Ubuntu 24.04 is running and the path is correct." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "   You can start WSL with: wsl -d Ubuntu-24.04" -ForegroundColor Gray
        return $false
    }

    # Check if Windows source exists
    if (-not (Test-Path $WindowsSource)) {
        Write-Host "❌ Windows source not found: $WindowsSource" -ForegroundColor Red
        return $false
    }

    Write-Host "📁 Source:      $WindowsSource" -ForegroundColor Green
    Write-Host "📁 Destination: $WSLDestination" -ForegroundColor Green
    Write-Host ""

    # Create destination if not exists
    if (-not (Test-Path $WSLDestination)) {
        Write-Host "📦 Creating destination directory..." -ForegroundColor Yellow
        New-Item -ItemType Directory -Force -Path $WSLDestination | Out-Null
    }

    # Build robocopy arguments
    $RobocopyArgs = @(
        $WindowsSource,
        $WSLDestination,
        "*.*",
        "/E",                    # Copy subdirectories (including empty)
        "/COPY:DAT",             # Copy Data, Attributes, Timestamps
        "/R:2",                  # Retry count: 2
        "/W:1",                  # Wait time: 1 second
        "/NFL",                  # No File List
        "/NDL",                  # No Directory List
        "/NJH",                  # No Job Header
        "/NJS",                  # No Job Summary
        "/NP",                   # No Progress
        "/XD"                    # Exclude Directories
    )
    
    # Add excluded directories
    $RobocopyArgs += $ExcludeDirs
    $RobocopyArgs += "/XF"       # Exclude Files
    # Add excluded files
    $RobocopyArgs += $ExcludeFiles

    if ($DryRun) {
        Write-Host "🔍 DRY RUN MODE - No files will be copied" -ForegroundColor Yellow
        Write-Host ""
        $RobocopyArgs += "/L"    # List only (don't copy)
    }

    if ($Verbose) {
        $RobocopyArgs = $RobocopyArgs | Where-Object { $_ -notin @("/NFL", "/NDL", "/NJH", "/NJS", "/NP") }
    }

    Write-Host "🚀 Starting synchronization..." -ForegroundColor Cyan
    Write-Host ""

    # Execute robocopy
    $StartTime = Get-Date
    $Result = robocopy $RobocopyArgs
    $EndTime = Get-Date
    $Duration = $EndTime - $StartTime

    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║                              Synchronization Complete                                    ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "⏱️  Duration: $($Duration.TotalSeconds.ToString("0.00")) seconds" -ForegroundColor Gray
    Write-Host ""

    # Interpret robocopy exit code
    $ExitCode = $Result
    if ($ExitCode -ge 8) {
        Write-Host "❌ Some files could not be copied. Exit code: $ExitCode" -ForegroundColor Red
        return $false
    } elseif ($ExitCode -ge 4) {
        Write-Host "⚠️  Mismatch detected. Exit code: $ExitCode" -ForegroundColor Yellow
    } elseif ($ExitCode -ge 2) {
        Write-Host "✅ Extra files or mismatches were copied. Exit code: $ExitCode" -ForegroundColor Green
    } elseif ($ExitCode -eq 1) {
        Write-Host "✅ All files copied successfully!" -ForegroundColor Green
    } elseif ($ExitCode -eq 0) {
        Write-Host "✅ No files needed to be copied (already in sync)" -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "📌 Next steps in WSL:" -ForegroundColor Cyan
    Write-Host "   1. wsl -d Ubuntu-24.04" -ForegroundColor Gray
    Write-Host "   2. cd ~/Profeta" -ForegroundColor Gray
    Write-Host "   3. conda activate profeta" -ForegroundColor Gray
    Write-Host "   4. python profeta-universal.py config-lstm.ini" -ForegroundColor Gray
    Write-Host ""

    return $true
}

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════════════════

# Parse command line arguments
$DryRun = $false
$VerboseOutput = $false

if ($args -contains "--dry-run" -or $args -contains "-d") {
    $DryRun = $true
}

if ($args -contains "--verbose" -or $args -contains "-v") {
    $VerboseOutput = $true
}

if ($args -contains "--help" -or $args -contains "-h") {
    Write-Host ""
    Write-Host "Usage: .\sync-to-wsl.ps1 [options]" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -d, --dry-run    Show what would be copied without actually copying" -ForegroundColor Gray
    Write-Host "  -v, --verbose    Show detailed file list during copy" -ForegroundColor Gray
    Write-Host "  -h, --help       Show this help message" -ForegroundColor Gray
    Write-Host ""
    exit 0
}

# Execute sync
Sync-Projeto -DryRun:$DryRun -Verbose:$VerboseOutput

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    END OF SCRIPT
# ═══════════════════════════════════════════════════════════════════════════════════════════
