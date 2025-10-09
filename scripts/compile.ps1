<#
.SYNOPSIS
    Script di compilazione per il progetto C++ "arbitrage_system".
.DESCRIPTION
    Da eseguire da /scripts.
    Compila i sorgenti in /cpp/src e genera l'eseguibile in /cpp/build/test_client.exe.
    Usa header da /cpp/include.
#>

# Percorsi fissi e deterministici
$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$SrcDir = Join-Path $ProjectRoot "cpp\src"
$IncDir = Join-Path $ProjectRoot "cpp\include"
$BuildDir = Join-Path $ProjectRoot "cpp\build"
$Executable = Join-Path $BuildDir "test_client.exe"

Write-Host "Compilazione progetto Arbitrage System"
Write-Host "Sorgenti: $SrcDir"
Write-Host "Include: $IncDir"
Write-Host "Output: $BuildDir"
Write-Host ""

# Crea la cartella build se non esiste
if (-not (Test-Path $BuildDir)) {
    Write-Host "Creo cartella build..."
    New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
}

# Elenco deterministico dei file sorgenti
$Sources = @(
    (Join-Path $SrcDir "Graph.cpp"),
    (Join-Path $SrcDir "SocketClient.cpp"),
    (Join-Path $SrcDir "main.cpp")
)

# Verifica che i file esistano
foreach ($src in $Sources) {
    if (-not (Test-Path $src)) {
        Write-Host "Errore: File sorgente mancante -> $src"
        exit 1
    }
}

# Costruzione comando di compilazione
$Command = "g++ " + ($Sources -join " ") + `
    " -I`"" + $IncDir + "`"" + `
    " -o `"" + $Executable + "`"" + `
    " -lws2_32 -mconsole"

Write-Host "Eseguo comando:"
Write-Host "    $Command"
Write-Host ""

# Esecuzione effettiva
$process = Start-Process -FilePath "cmd.exe" -ArgumentList "/c $Command" -NoNewWindow -Wait -PassThru

# Verifica risultato
if ($process.ExitCode -eq 0) {
    Write-Host ""
    Write-Host "Compilazione completata con successo."
    Write-Host "Eseguibile: $Executable"
} else {
    Write-Host ""
    Write-Host "Errore nella compilazione (ExitCode: $($process.ExitCode))"
    exit $process.ExitCode
}
