$ErrorActionPreference = 'Stop'
Write-Warning 'This removes local resource data and the metadata database.'
$confirm = Read-Host 'Type RESET to remove contents of data/buckets, data/instances, data/applications, data/databases, and data/mini_aws.db'
if ($confirm -ne 'RESET') { Write-Host 'Cancelled.'; exit 0 }

$root = Resolve-Path "$PSScriptRoot\.."
foreach ($name in @('buckets', 'instances', 'applications', 'databases')) {
  $target = Join-Path $root "data\$name"
  if (Test-Path $target) {
    Get-ChildItem -Force $target |
      Where-Object { $_.Name -ne '.gitkeep' } |
      Remove-Item -Recurse -Force
  }
}

$metadata = Join-Path $root 'data\mini_aws.db'
if (Test-Path $metadata) {
  Remove-Item $metadata -Force
}

Write-Host 'Local resource data cleared. The next backend start recreates the metadata schema.'
