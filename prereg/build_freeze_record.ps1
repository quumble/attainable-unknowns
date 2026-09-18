param(
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RawDir = Join-Path $RepoRoot "api-study\data\raw"

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $PSScriptRoot "API_PILOT_0.1_FREEZE_RECORD.json"
}

$TrackedStudyFiles = @(
    "api-study/config.yaml",
    "api-study/passages.json",
    "api-study/run.py",
    "api-study/analyze_confirmatory.py",
    "api-study/SPECIFICITY_CODEBOOK.md",
    "prereg/API_PILOT_0.1_PREREGISTRATION.md"
)

$StudyHashes = [ordered]@{}
foreach ($RelativePath in $TrackedStudyFiles) {
    $FullPath = Join-Path $RepoRoot $RelativePath
    if (-not (Test-Path $FullPath)) {
        throw "Required freeze file is missing: $RelativePath"
    }
    $StudyHashes[$RelativePath] = (Get-FileHash -Algorithm SHA256 $FullPath).Hash.ToLowerInvariant()
}

$SmokeRuns = @()
if (Test-Path $RawDir) {
    $ManifestFiles = Get-ChildItem $RawDir -Filter "*.manifest.json" -File | Sort-Object Name
    foreach ($ManifestFile in $ManifestFiles) {
        $Manifest = Get-Content $ManifestFile.FullName -Raw | ConvertFrom-Json

        $IsBoundedSmoke = $false
        if ($null -ne $Manifest.full_design_run) {
            $IsBoundedSmoke = ($Manifest.full_design_run -eq $false)
        }
        elseif ($null -ne $Manifest.confirmatory) {
            $IsBoundedSmoke = ($Manifest.confirmatory -eq $false)
        }
        elseif (($null -ne $Manifest.planned_requests) -and ($null -ne $Manifest.full_design_requests)) {
            $IsBoundedSmoke = ([int]$Manifest.planned_requests -lt [int]$Manifest.full_design_requests)
        }

        if (-not $IsBoundedSmoke) {
            continue
        }

        $RecordsPath = $null
        if ($Manifest.records_file) {
            $RecordsName = [System.IO.Path]::GetFileName([string]$Manifest.records_file)
            $Candidate = Join-Path $RawDir $RecordsName
            if (Test-Path $Candidate) {
                $RecordsPath = $Candidate
            }
        }

        $SmokeRuns += [ordered]@{
            run_id = $Manifest.run_id
            model_key = $Manifest.model_key
            model = $Manifest.model
            provider = $Manifest.provider
            status = $Manifest.status
            planned_requests = $Manifest.planned_requests
            successful_requests = $Manifest.successful_requests
            error_requests = $Manifest.error_requests
            full_design_run = $Manifest.full_design_run
            legacy_confirmatory_field = $Manifest.confirmatory
            config_sha256 = $Manifest.config_sha256
            passages_sha256 = $Manifest.passages_sha256
            runner_sha256 = $Manifest.runner_sha256
            manifest_file = $ManifestFile.Name
            manifest_sha256 = (Get-FileHash -Algorithm SHA256 $ManifestFile.FullName).Hash.ToLowerInvariant()
            records_file = if ($RecordsPath) { [System.IO.Path]::GetFileName($RecordsPath) } else { $null }
            records_sha256 = if ($RecordsPath) { (Get-FileHash -Algorithm SHA256 $RecordsPath).Hash.ToLowerInvariant() } else { $null }
        }
    }
}

$GitCommit = (& git -C $RepoRoot rev-parse HEAD).Trim()
$GitStatus = @(& git -C $RepoRoot status --porcelain)

$Record = [ordered]@{
    study = "Attainable Unknowns API Pilot 0.1"
    generated_at_utc = [DateTime]::UtcNow.ToString("o")
    pre_freeze_git_commit = $GitCommit
    pre_freeze_worktree_dirty = ($GitStatus.Count -gt 0)
    note = "Generated before founder-signed pre-collection freeze. Smoke-test response content was not inspected by this script."
    frozen_study_files_sha256 = $StudyHashes
    excluded_bounded_smoke_runs = $SmokeRuns
}

$Record | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 $OutputPath

Write-Host "Freeze record written to:"
Write-Host $OutputPath
Write-Host ""
Write-Host "Bounded smoke runs recorded:" $SmokeRuns.Count
$SmokeRuns |
    Select-Object run_id, model_key, status, planned_requests, successful_requests, error_requests |
    Format-Table -AutoSize
