param(
    [bool]$Dry = $true
)

$rules = @(
    @{ Pattern = '(\bfrom\s+)core\.capabilities'; Replacement = '$1core.services.capabilities' },
    @{ Pattern = '(\bimport\s+)core\.capabilities'; Replacement = '$1core.services.capabilities' },
    @{ Pattern = '(\bfrom\s+)core\.conn_broker'; Replacement = '$1core.services.conn_broker' },
    @{ Pattern = '(\bimport\s+)core\.conn_broker'; Replacement = '$1core.services.conn_broker' },
    @{ Pattern = '(\bfrom\s+\.)capabilities'; Replacement = '$1services.capabilities' }
)

if (Test-Path 'core/services/contracts') {
    $rules += @{ Pattern = '(\bfrom\s+)core\.contracts'; Replacement = '$1core.services.contracts' }
    $rules += @{ Pattern = '(\bimport\s+)core\.contracts'; Replacement = '$1core.services.contracts' }
}

$updated = @()
$files = Get-ChildItem -Path . -Include *.py -Recurse -File

foreach ($file in $files) {
    $content = Get-Content -LiteralPath $file.FullName -Raw
    $newContent = $content
    foreach ($rule in $rules) {
        $newContent = [regex]::Replace($newContent, $rule.Pattern, $rule.Replacement)
    }
    if ($newContent -ne $content) {
        $updated += $file.FullName
        if (-not $Dry) {
            [System.IO.File]::WriteAllText($file.FullName, $newContent, [System.Text.Encoding]::UTF8)
        }
    }
}

$servicesInit = 'core/services/__init__.py'
if (-not (Test-Path $servicesInit)) {
    if ($Dry) {
        Write-Host "Dry run: would create $servicesInit"
    }
    else {
        New-Item -ItemType File -Path $servicesInit -Force | Out-Null
        Write-Host "Created $servicesInit"
    }
}

if ($Dry) {
    Write-Host "Dry run: would update $($updated.Count) file(s)."
    foreach ($path in $updated) {
        Write-Host "  $path"
    }
}
else {
    Write-Host "Updated $($updated.Count) file(s)."
    foreach ($path in $updated) {
        Write-Host "  $path"
    }
}
