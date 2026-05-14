<#
  build-all.ps1
  Converts all translated/*.txt files into chapter HTML pages, updates chapters.html,
  and fixes prev/next nav across all chapters. Run this once after all translations are done.

  Usage:
    .\build-all.ps1           # build everything
    .\build-all.ps1 -DryRun   # show what would run without executing
#>

param([switch]$DryRun)

Set-Location $PSScriptRoot

$files = Get-ChildItem translated\*.txt | Sort-Object Name
if ($files.Count -eq 0) {
    Write-Host "No files found in translated\. Nothing to build." -ForegroundColor Yellow
    exit 0
}

Write-Host "Found $($files.Count) translated files to build." -ForegroundColor Cyan
$done = 0

foreach ($f in $files) {
    if ($DryRun) {
        Write-Host "[DRY ] python build-chapter.py $($f.Name)" -ForegroundColor Cyan
        continue
    }

    Write-Host "[BUILD] $($f.Name)" -ForegroundColor Yellow
    python build-chapter.py $f.FullName
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] $($f.Name) - stopping." -ForegroundColor Red
        exit $LASTEXITCODE
    }
    $done++
}

if ($DryRun) {
    Write-Host "Dry run complete." -ForegroundColor Cyan
    exit 0
}

Write-Host ""
Write-Host "Built $done chapters." -ForegroundColor Green
Write-Host ""
Write-Host "Next: review the output, then commit:" -ForegroundColor Cyan
Write-Host "  git add chapters\ chapters.html" -ForegroundColor White
Write-Host "  git commit -m `"Build HTML for all $done translated chapters`"" -ForegroundColor White
Write-Host "  git push" -ForegroundColor White
