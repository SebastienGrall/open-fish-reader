$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Assert-CommandSuccess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

Write-Host ""
Write-Host "[1/6] Verification de Python"
python --version
Assert-CommandSuccess "Python est introuvable ou inutilisable."

Write-Host ""
Write-Host "[2/6] Installation ou verification de PyInstaller"
python -m pip install --upgrade "pyinstaller>=6.15,<7"
Assert-CommandSuccess "Installation de PyInstaller impossible."

Write-Host ""
Write-Host "[3/6] Generation des metadonnees Windows"
python .\build_tools\create_windows_version_info.py
Assert-CommandSuccess "Generation des metadonnees Windows impossible."

Write-Host ""
Write-Host "[4/6] Controles du projet"
python -m compileall .\src
Assert-CommandSuccess "Compilation du code Python impossible."

ruff format --check .
Assert-CommandSuccess "Le formatage Ruff doit etre applique avec : ruff format ."

ruff check .
Assert-CommandSuccess "Analyse Ruff en echec."

pytest
Assert-CommandSuccess "Tests automatises en echec."

Write-Host ""
Write-Host "[5/6] Construction de l'application portable"
python -m PyInstaller --noconfirm --clean .\OpenFishReader.spec
Assert-CommandSuccess "Construction PyInstaller impossible."

Write-Host ""
Write-Host "Lecture des informations de version"

$Version = python -c "import sys; sys.path.insert(0, 'src'); from open_fish_reader.version import APP_VERSION; print(APP_VERSION)"
Assert-CommandSuccess "Lecture de APP_VERSION impossible."

$Publisher = python -c "import sys; sys.path.insert(0, 'src'); from open_fish_reader.version import ORGANIZATION_NAME; print(ORGANIZATION_NAME)"
Assert-CommandSuccess "Lecture de ORGANIZATION_NAME impossible."

$Version = "$Version".Trim()
$Publisher = "$Publisher".Trim()

if ([string]::IsNullOrWhiteSpace($Version)) {
    throw "APP_VERSION est vide dans version.py."
}

if ([string]::IsNullOrWhiteSpace($Publisher)) {
    throw "ORGANIZATION_NAME est vide dans version.py."
}

Write-Host "Version : $Version"
Write-Host "Organisme : $Publisher"

$IsccCandidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 7\ISCC.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 7\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 7\ISCC.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
)

$Iscc = $IsccCandidates |
    Where-Object { $_ -and (Test-Path $_) } |
    Select-Object -First 1

if ([string]::IsNullOrWhiteSpace($Iscc)) {
    throw "ISCC.exe est introuvable. Installez Inno Setup 7 ou 6."
}

Write-Host ""
Write-Host "[6/6] Construction de l'installateur Windows"
Write-Host "Compilateur Inno Setup : $Iscc"

& $Iscc "/DMyAppVersion=$Version" "/DMyAppPublisher=$Publisher" ".\installer\OpenFishReader.iss"
Assert-CommandSuccess "Compilation Inno Setup impossible."

$PortableExecutable = Join-Path $ProjectRoot "dist\Open Fish Reader\OpenFishReader.exe"
$InstallerFolder = Join-Path $ProjectRoot "installer_output"
$Installers = Get-ChildItem -Path $InstallerFolder -Filter "*.exe" -File -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Construction terminee avec succes."

if (Test-Path $PortableExecutable) {
    Write-Host "Application portable : $PortableExecutable"
}
else {
    Write-Warning "Executable portable introuvable : $PortableExecutable"
}

if (-not $Installers) {
    throw "Aucun installateur trouve dans installer_output."
}

Write-Host ""
Write-Host "Installateur(s) genere(s) :"
$Installers |
    Select-Object FullName, Length, LastWriteTime |
    Format-Table -AutoSize
