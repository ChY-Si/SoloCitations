# Push this repository to GitHub.
#
# Git Credential Manager needs to show its sign-in window, which only works in
# an interactive terminal - so run this yourself from PowerShell:
#
#     powershell -ExecutionPolicy Bypass -File scripts\push_to_github.ps1
#
# On the first run a browser / sign-in window opens; approve it and the push
# completes.  The credential is stored by Windows, so later pushes are silent.

$ErrorActionPreference = 'Stop'

$repo   = 'D:\Python\Projects\SoloCitations'
$url    = 'https://github.com/ChY-Si/SoloCitations.git'
$branch = 'main'

# Rewriting history is intended here: the local repository is a fresh start and
# the remote only holds the Apache-2.0 LICENSE commit, whose file is included in
# the local commit below.
$expectedRemote = '1283419aac1a2748214819af6775263e2fdaf08f'

Set-Location $repo

Write-Host "Local HEAD:" -ForegroundColor Cyan
git log -1 --format='  %H  %an <%ae>%n  %s'

Write-Host "`nMaking sure the remote points at $url" -ForegroundColor Cyan
git remote remove origin 2>$null
git remote add origin $url

Write-Host "`nRemote main is currently:" -ForegroundColor Cyan
git ls-remote origin refs/heads/main | ForEach-Object { "  $_" }

Write-Host "`nPushing (a sign-in window may appear)..." -ForegroundColor Yellow
git push --force-with-lease="refs/heads/main:$expectedRemote" origin $branch

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nForce-with-lease refused: the remote has moved since this repository was" -ForegroundColor Red
    Write-Host "prepared.  Re-check the remote, then push again with:" -ForegroundColor Red
    Write-Host "  git push --force-with-lease origin main" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`nPushed. Verifying the remote..." -ForegroundColor Green
git ls-remote origin refs/heads/main | ForEach-Object { "  $_" }
Write-Host "`nLocal HEAD: $(git rev-parse HEAD)"
Write-Host "Done: https://github.com/ChY-Si/SoloCitations"
