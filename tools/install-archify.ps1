$ErrorActionPreference = 'Stop'
$solutionRoot = Split-Path -Parent $PSScriptRoot
$archifyPath = Join-Path $PSScriptRoot 'archify'

if (-not (Test-Path -LiteralPath $archifyPath)) {
    git clone https://github.com/tt-a1i/archify.git $archifyPath
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo descargar Archify.' }
    git -C $archifyPath checkout --detach 73aaa0696e8f72c232ea710e6fa94fd953f3e773
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo seleccionar la revisión de Archify usada en esta solución.' }
}

# Conserva cualquier instalación existente; recomienda el visor en el workspace.
code.cmd --install-extension root-at-skic.archify-vscode-ext@0.5.1
if ($LASTEXITCODE -ne 0) { throw 'No se pudo instalar Archify Diagram Viewer.' }
Write-Output "Archify disponible en $archifyPath"
Write-Output "Abrir la solución en VS Code: $solutionRoot"
