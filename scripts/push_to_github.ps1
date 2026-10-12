# Push this repository to GitHub as ChY-Si.
#
# Run this yourself from PowerShell - the prompt needs your desktop:
#
#     powershell -ExecutionPolicy Bypass -File scripts\push_to_github.ps1
#
# ---------------------------------------------------------------------------
# Why the earlier runs failed
# ---------------------------------------------------------------------------
# A: "Permission to ChY-Si/SoloCitations.git denied to TKS-jp" (HTTP 403)
#    Windows held an old generic credential for github.com belonging to the
#    account TKS-jp.  Git sent it, GitHub refused, and Git Credential Manager
#    never prompted because it thought a credential was already available.
#    That entry has now been deleted, so git will ask again.
#
# B: no sign-in window appeared
#    Without a credential git asks Git Credential Manager, which needs to
#    create helper processes.  Under a restricted (sandboxed) shell that fails
#    with "couldn't create signal pipe, Win32 error 5", so the prompt never
#    opens.  Running this script from a normal PowerShell window avoids that.
#
# ---------------------------------------------------------------------------
# Two ways to authenticate
# ---------------------------------------------------------------------------
# 1) Interactive (default): a browser / sign-in window appears; approve it.
#
#        powershell -ExecutionPolicy Bypass -File scripts\push_to_github.ps1
#
# 2) Personal Access Token (no window, good for scripted runs).  Create one at
#    https://github.com/settings/tokens with "repo" scope, then:
#
#        $env:GITHUB_TOKEN = 'github_pat_...'
#        powershell -ExecutionPolicy Bypass -File scripts\push_to_github.ps1
#
#    The token is handed to git through the standard input of the credential
#    helper, so it never appears in a command line.  A GitHub *password* will
#    not work - GitHub requires a token.
#
# NOTE: clearing the stored github.com credential also affects other
# repositories on this machine that push over HTTPS (e.g.
# D:\Python\Projects\Clock, Wifai).  Their next push will ask for credentials
# again; the token above can be reused for them.

$ErrorActionPreference = 'Stop'

$repo             = 'D:\Python\Projects\SoloCitations'
$url              = 'https://github.com/ChY-Si/SoloCitations.git'
$branch           = 'main'
$credentialTarget = 'git:https://github.com'
$user             = 'ChY-Si'

Set-Location $repo

# ---------------------------------------------------------------------------
# 1. Show what will be pushed.
# ---------------------------------------------------------------------------
Write-Host 'Local HEAD:' -ForegroundColor Cyan
git log -1 --format='  %H  %an <%ae>%n  %s'

Write-Host "`nStored github.com credentials:" -ForegroundColor Cyan
$stored = cmdkey /list:$credentialTarget 2>&1 | Out-String
if ($stored -match 'User:\s*(\S+)') {
    $user = $Matches[1]
    Write-Host "  user = $user" -ForegroundColor Yellow
} else {
    Write-Host '  none (git will prompt)' -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# 2. Confirm the remote.
# ---------------------------------------------------------------------------
Write-Host "`nPointing the remote at $url" -ForegroundColor Cyan
git remote remove origin 2>$null
git remote add origin $url
git remote -v

# ---------------------------------------------------------------------------
# 3. Read the current remote SHA; the push is refused if the remote moved.
# ---------------------------------------------------------------------------
Write-Host "`nFetching the current remote state..." -ForegroundColor Cyan
$remoteLine = git ls-remote origin "refs/heads/$branch"
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Could not reach the remote. Check the network and try again.' -ForegroundColor Red
    exit 1
}
$remoteSha = ($remoteLine -split '\s+')[0]
if (-not $remoteSha) {
    Write-Host 'Remote branch not found; a plain push will create it.' -ForegroundColor Yellow
    $lease = "refs/heads/${branch}:"
    $remoteSha = ''
} else {
    Write-Host "  remote $branch = $remoteSha"
    $lease = "refs/heads/${branch}:$remoteSha"
}

# ---------------------------------------------------------------------------
# 4. Authenticate.
# ---------------------------------------------------------------------------
$usingToken = [bool]$env:GITHUB_TOKEN
if ($usingToken) {
    Write-Host "`nStoring the supplied token for github.com (helper: store)..." -ForegroundColor Cyan
    $payload = "protocol=https`nhost=github.com`nusername=$user`npassword=$env:GITHUB_TOKEN`n`n"
    $payload | git credential approve
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Could not hand the token to git.' -ForegroundColor Red
        exit 1
    }
    Write-Host '  stored. It can be removed later with:' -ForegroundColor Green
    Write-Host "    `"protocol=https``nhost=github.com``n`" | git credential reject" -ForegroundColor DarkGray
} else {
    Write-Host "`nNo GITHUB_TOKEN set - git will ask Git Credential Manager." -ForegroundColor Yellow
    Write-Host 'A sign-in window should appear; approve it to continue.' -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 5. Push.  The remote holds one LICENSE commit; this repository starts a fresh
#    history that already contains that same Apache-2.0 file.
# ---------------------------------------------------------------------------
Write-Host "`nPushing..." -ForegroundColor Yellow
git push --force-with-lease="$lease" origin $branch
$pushExit = $LASTEXITCODE

if ($pushExit -ne 0) {
    Write-Host "`nThe push did not complete (exit $pushExit)." -ForegroundColor Red
    Write-Host 'If a stale credential is still in the way, remove it with:' -ForegroundColor Red
    Write-Host "  cmdkey /delete:$credentialTarget" -ForegroundColor Red
    Write-Host 'If nothing prompts at all, set a Personal Access Token as shown at' -ForegroundColor Red
    Write-Host 'the top of this script and run it again.' -ForegroundColor Red
    if ($usingToken) {
        Write-Host 'Removing the token that was just stored...' -ForegroundColor Yellow
        "protocol=https`nhost=github.com`n`n" | git credential reject
    }
    exit $pushExit
}

Write-Host "`nPushed. Verifying the remote..." -ForegroundColor Green
git ls-remote origin "refs/heads/$branch" | ForEach-Object { "  $_" }
Write-Host "  local  HEAD = $(git rev-parse HEAD)"
Write-Host "`nDone: https://github.com/ChY-Si/SoloCitations"
