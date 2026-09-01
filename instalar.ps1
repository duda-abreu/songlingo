$ErrorActionPreference = "Stop"

$executavelPython = if (Get-Command py -ErrorAction SilentlyContinue) {
    "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    "python"
} else {
    throw "Python 3.11+ não encontrado. Instale em https://python.org"
}

& $executavelPython -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")

if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível instalar as dependências."
}

Write-Host "Pronto. Rode: $executavelPython main.py"
