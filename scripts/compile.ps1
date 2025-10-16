<#
.SYNOPSIS
    Compilation script for the C++ "arbitrage_system" project.
.DESCRIPTION
    To be run from /scripts.
    Compiles sources in /cpp/src and generates the executable in /cpp/build/test_client.exe.
    Uses headers from /cpp/include.
#>

# Fixed and deterministic paths
$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$SrcDir = Join-Path $ProjectRoot "cpp\src"
$IncDir = Join-Path $ProjectRoot "cpp\include"
$BuildDir = Join-Path $ProjectRoot "cpp\build"
$Executable = Join-Path $BuildDir "arbitrage_detector.exe"

Write-Host "Compiling Arbitrage System project"
Write-Host "Sources: $SrcDir"
Write-Host "Include: $IncDir"
Write-Host "Output: $BuildDir"
Write-Host ""

# Create build folder if it doesn't exist
if (-not (Test-Path $BuildDir)) {
    Write-Host "Creating build folder..."
    New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
}

# Deterministic list of source files
$Sources = @(
    (Join-Path $SrcDir "Graph.cpp"),
    (Join-Path $SrcDir "SocketClient.cpp"),
    (Join-Path $SrcDir "main.cpp")
)

# Verify that files exist
foreach ($src in $Sources) {
    if (-not (Test-Path $src)) {
        Write-Host "Error: Missing source file -> $src"
        exit 1
    }
}

# Build compilation command
$Command = "g++ " + ($Sources -join " ") + `
    " -I`"" + $IncDir + "`"" + `
    " -o `"" + $Executable + "`"" + `
    " -lws2_32 -mconsole"

Write-Host "Executing command:"
Write-Host "    $Command"
Write-Host ""

# Actual execution
$process = Start-Process -FilePath "cmd.exe" -ArgumentList "/c $Command" -NoNewWindow -Wait -PassThru

# Verify result
if ($process.ExitCode -eq 0) {
    Write-Host ""
    Write-Host "Compilation completed successfully."
    Write-Host "Executable: $Executable"
} else {
    Write-Host ""
    Write-Host "Compilation error (ExitCode: $($process.ExitCode))"
    exit $process.ExitCode
}
