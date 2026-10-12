# Push this repository to GitHub.
#
# Git Credential Manager needs to show its sign-in window, which only works in
# an interactive terminal - so run this yourself from PowerShell:
#
#     powershell -ExecutionPolicy Bypass -File scripts\push_to_github.ps1
#
# If no credential is stored yet, a browser / sign-in window opens; approve it
# and the push completes.  Windows stores the credential, so later pushes are
# silent.
#
# This repository starts a fresh history, so the push replaces the remote's
# single LICENSE commit (that same Apache-2.0 file is part of the local commit).
# --force-with-lease is used so the push is refused if the remote has moved.

$ErrorActionPreference = 'Stop'

$repo   = 'D:\Python\Projects\SoloCitations'
$url    = 'https://github.com/ChY-Si/SoloCitations.git'
$branch = 'main'

Set-Location $repo

Write-Host 'Local HEAD:' -ForegroundColor Cyan
git log -1 --format='  %H  %an <%ae>%n  %s'

Write-Host "`nPointing the remote at $url" -ForegroundColor Cyan
git remote remove origin 2>$null
git remote add origin $url
git remote -v

Write-Host 'Fetching the current remote state...' -ForegroundColor Cyan
$remoteLine = git ls-remote origin "refs/heads/$branch"
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Could not reach the remote. Check the network and try again.' -ForegroundColor Red
    exit 1
}

$remoteSha = ($remoteLine -split '\s+')[0]
if (-not $remoteSha) {
    Write-Host 'Remote branch not found; a plain push will create it.' -ForegroundColor Yellow
    $lease = "refs/heads/${branch}:"
} else {
    Write-Host "  remote $branch = $remoteSha"
    $lease = "refs/heads/${branch}:$remoteSha"
}

Write-Host "`nPushing (a sign-in window may appear)..." -ForegroundColor Yellow
git push --force-with-lease="$lease" origin $branch

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nThe push did not complete." -ForegroundColor Red
    Write-Host 'If it was refused because the remote moved, inspect it first:' -ForegroundColor Red
    Write-Host '  git fetch origin && git log --oneline origin/main' -ForegroundColor Red
    Write-Host 'then push again with:  git push --force-with-lease origin main' -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`nPushed. Verifying the remote..." -ForegroundColor Green
git ls-remote origin "refs/heads/$branch" | ForEach-Object { "  $_" }
Write-Host "  local  HEAD = $(git rev-parse HEAD)"
Write-Host "`nDone: https://github.com/ChY-Si/SoloCitations"
