"""
Запускает перевод Color.use_case на русский.
Запуск:
  .\translate_use_cases.ps1
  .\translate_use_cases.ps1 -Runs 160 -BatchSize 500 -PauseSeconds 300
"""

param(
    [int]$Runs = 160,
    [int]$BatchSize = 500,
    [int]$PauseSeconds = 5
)

for ($i = 1; $i -le $Runs; $i++) {
    Write-Host ("Run {0} / {1}: translating {2} use_case values" -f $i, $Runs, $BatchSize)
    python seed_colors.py translate-use-cases $BatchSize

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Stopped on run $i with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }

    if ($i -lt $Runs -and $PauseSeconds -gt 0) {
        Start-Sleep -Seconds $PauseSeconds
    }
}

Write-Host "Completed $Runs runs."
