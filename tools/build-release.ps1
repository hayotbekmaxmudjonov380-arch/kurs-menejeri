<#
.SYNOPSIS
    Kurs Manager — bitta buyruqda APK + EXE build, GitHub Release va updates.json yangilanishi.
.DESCRIPTION
    1. PyInstaller orqali Win10 (Qt6) va Win8 (Qt5) exe build qiladi
    2. Gradle orqali Android APK build qiladi
    3. Barcha fayllar SHA-256 bilan tekshiriladi
    4. GitHub Release yaratadi va barcha assetlarni yuklaydi
    5. updates.json (win10, win8, android) yangilanadi va git push qilinadi
    6. Foydalanuvchilarga avtomatik yangilanish habari keladi
.PARAMETER Version
    Yangi versiya (masalan 1.4.1). Berilmasa version.py dan o'qiladi.
.PARAMETER Notes
    GitHub Release eshgalari (notes).
.PARAMETER SkipApk
    APK buildni o'tkazib yuboradi (faqat exe).
.PARAMETER NoPush
    GitHubga push qilmasdan faqat yerda yangilanadi.
#>
[CmdletBinding()]
param(
    [string]$Version = "",
    [string]$Notes = "",
    [switch]$SkipApk = $false,
    [switch]$NoPush = $false
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSCommandPath | Split-Path -Parent
Set-Location -LiteralPath $RepoRoot

Write-Host "Repo: $RepoRoot" -ForegroundColor Cyan

# --- 1. Versiya aniqlash va version.py yangilash ---
if ([string]::IsNullOrWhiteSpace($Version)) {
    $VersionFile = Join-Path $RepoRoot "version.py"
    $Content = Get-Content -LiteralPath $VersionFile -Raw -Encoding UTF8
    $Match = [regex]::Match($Content, "(?m)^\s*VERSION\s*=\s*[" + [char]39 + "]*(?<version>\d+\.\d+\.\d+)[" + [char]39 + "]*\s*$")
    if (-not $Match.Success) {
        throw "version.py da VERSION x.x.x shaklida topilmadi."
    }
    $Version = $Match.Groups["version"].Value
} else {
    $VersionFile = Join-Path $RepoRoot "version.py"
    $Content = Get-Content -LiteralPath $VersionFile -Raw -Encoding UTF8
    $Content = [regex]::Replace($Content, "(?m)^\s*VERSION\s*=.*$", 'VERSION = "' + $Version + '"')
    Set-Content -LiteralPath $VersionFile -Value $Content -Encoding UTF8
    Write-Host "version.py versiya: $Version ga yangilandi." -ForegroundColor Green
}

Write-Host "Versiya: $Version" -ForegroundColor Cyan

$Tag = "v$Version"
$Owner = "hayotbekmaxmudjonov380-arch"
$Repository = "kurs-menejeri"
$RepoSlug = "$Owner/$Repository"
$UpdatesJson = Join-Path $RepoRoot "updates.json"

# --- 2. Win10 (Qt6) build ---
Write-Host "Win10 (Qt6) build boshlandi..." -ForegroundColor Cyan
& python -m PyInstaller KursManager.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller Win10 build bajarilmadi."
}

$Win10ExePath = Join-Path $RepoRoot "dist\KursManager.exe"
if (-not (Test-Path -LiteralPath $Win10ExePath)) {
    throw "Win10 exe topilmadi: $Win10ExePath"
}

$Win10ExeBackup = Join-Path $RepoRoot "dist\KursManager_Win10.exe"
Copy-Item -LiteralPath $Win10ExePath -Destination $Win10ExeBackup -Force

# --- 3. Win8 (Qt5) build ---
$Win8ExePath = $null
Write-Host "Win8 (Qt5) build boshlandi..." -ForegroundColor Cyan
$Win8Spec = Join-Path $RepoRoot "win8\KursManager_Win8.spec"
if (-not (Test-Path -LiteralPath $Win8Spec)) {
    throw "win8\KursManager_Win8.spec topilmadi."
}
& python -m PyInstaller $Win8Spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller Win8 build bajarilmadi."
}

$Win8DistDir = Join-Path $RepoRoot "win8\dist"
if (-not (Test-Path -LiteralPath $Win8DistDir)) {
    New-Item -ItemType Directory -Path $Win8DistDir | Out-Null
}
$Win8ExePath = Join-Path $Win8DistDir "KursManager_Win8.exe"
Copy-Item -LiteralPath $Win10ExePath -Destination $Win8ExePath -Force

Copy-Item -LiteralPath $Win10ExeBackup -Destination $Win10ExePath -Force
Remove-Item -LiteralPath $Win10ExeBackup -Force

# --- 4. APK build (Android) ---
$ApkPath = $null
$ApkHash = $null
$ApkFileName = $null
if (-not $SkipApk) {
    Write-Host "Android APK build boshlandi..." -ForegroundColor Cyan
    $AndroidProject = Join-Path $RepoRoot "android_versiya\app"
    $Gradlew = Join-Path $AndroidProject "gradlew.bat"
    if (-not (Test-Path -LiteralPath $Gradlew)) {
        throw "gradlew.bat topilmadi: $Gradlew"
    }
    Set-Location -LiteralPath $AndroidProject
    & $Gradlew assembleRelease
    if ($LASTEXITCODE -ne 0) {
        throw "Gradle APK build bajarilmadi."
    }
    Set-Location -LiteralPath $RepoRoot

    $ApkPath = Join-Path $AndroidProject "app\build\outputs\apk\release\app-release.apk"
    if (-not (Test-Path -LiteralPath $ApkPath)) {
        throw "APK topilmadi: $ApkPath"
    }
    $ApkFileName = "KursManager-v$Version.apk"
}

# --- 5. SHA-256 ---
Write-Host "SHA-256 hisoblash..." -ForegroundColor Cyan
$Win10Hash = (Get-FileHash -LiteralPath $Win10ExePath -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "Win10 SHA-256: $Win10Hash" -ForegroundColor Green

$Win8Hash = (Get-FileHash -LiteralPath $Win8ExePath -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "Win8  SHA-256: $Win8Hash" -ForegroundColor Green

if (-not $SkipApk) {
    $ApkHash = (Get-FileHash -LiteralPath $ApkPath -Algorithm SHA256).Hash.ToLowerInvariant()
    Write-Host "APK   SHA-256: $ApkHash" -ForegroundColor Green
}

# --- 6. GitHub tekshiruvi ---
Write-Host "GitHub tekshiruvi..." -ForegroundColor Cyan
& gh auth status -h github.com >$null 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "GitHub ruxsati topilmadi. Bir marta: gh auth login -h github.com"
}

# Release allaqachon mavjudligini tekshirish (xato bo'lsa — release yo'q, davom etamiz)
$ErrorActionPreferenceSave = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$TagCheck = & gh release view $Tag --repo $RepoSlug 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    $ErrorActionPreference = $ErrorActionPreferenceSave
    throw "Release $Tag allaqachon mavjud. Boshqa versiya oling yoki eski release'ni o'chiring."
}
$ErrorActionPreference = $ErrorActionPreferenceSave

# --- 7. GitHub Release ---
Write-Host "GitHub Release yaratish: $Tag" -ForegroundColor Cyan
$ReleaseArgs = @(
    "release", "create", $Tag,
    $Win10ExePath,
    $Win8ExePath,
    "--repo", $RepoSlug,
    "--target", "main",
    "--title", "Kurs Manager $Tag",
    "--latest"
)
if ([string]::IsNullOrWhiteSpace($Notes)) {
    $ReleaseArgs += "--generate-notes"
} else {
    $ReleaseArgs += "--notes"
    $ReleaseArgs += $Notes
}
if (-not $SkipApk -and $ApkPath) {
    # gh asset nomini faylning o'z nomidan oladi (#faqat display label).
    # Shuning uchun APK'ni kerakli nom bilan nusxalaymiz, oks holda
    # updates.json dagi URL 404 bo'ladi.
    $ApkUploadPath = Join-Path $env:TEMP $ApkFileName
    Copy-Item -LiteralPath $ApkPath -Destination $ApkUploadPath -Force
    $ReleaseArgs += $ApkUploadPath
}

& gh @ReleaseArgs
if ($LASTEXITCODE -ne 0) {
    throw "GitHub Release yaratilmadi."
}

$ReleaseUrl = "https://github.com/$RepoSlug/releases/tag/$Tag"
Write-Host "Release tayyor: $ReleaseUrl" -ForegroundColor Green

# --- 8. updates.json yangilash ---
Write-Host "updates.json yangilanmoqda..." -ForegroundColor Cyan
$Updates = Get-Content -LiteralPath $UpdatesJson -Raw -Encoding UTF8 | ConvertFrom-Json

$BaseUrl = "https://github.com/$RepoSlug/releases/download/$Tag"

$Updates.win10.version = $Version
$Updates.win10.min_version = $Version
$Updates.win10.url = "$BaseUrl/KursManager.exe"
$Updates.win10.sha256 = $Win10Hash
$Updates.win10.notes = $Notes

$Updates.win8.version = $Version
$Updates.win8.min_version = $Version
$Updates.win8.url = "$BaseUrl/KursManager_Win8.exe"
$Updates.win8.sha256 = $Win8Hash
$Updates.win8.notes = $Notes

if (-not $SkipApk) {
    $Updates.android.version = $Version
    if ($Updates.android.versionCode -is [int]) {
        $Updates.android.versionCode = [int]($Updates.android.versionCode) + 1
    } else {
        $Updates.android.versionCode = 149
    }
    $Updates.android.min_version = $Version
    $Updates.android.url = "$BaseUrl/$ApkFileName"
    $Updates.android.sha256 = $ApkHash
    $Updates.android.notes = $Notes
}

$Updates | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $UpdatesJson -Encoding UTF8
Write-Host "updates.json yangilandi." -ForegroundColor Green

# --- 9. Git commit + push ---
if (-not $NoPush) {
    Write-Host "Git commit va push..." -ForegroundColor Cyan
    & git add version.py updates.json
    $CommitOut = & git commit -m "chore: release $Tag" 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0 -and $CommitOut -notmatch "nothing to commit") {
        Write-Warning "Git commit qilmadi (hollarda o'zgarish yo'q bo'lishi mumkin)."
    }
    & git push origin main
    if ($LASTEXITCODE -ne 0) {
        throw "Git push bajarilmadi."
    }
    Write-Host "GitHubga push qilindi." -ForegroundColor Green
}

Write-Host "`nBARCHA AMAL BAJARILDI!" -ForegroundColor Green
Write-Host "Release: $ReleaseUrl" -ForegroundColor Green
Write-Host "Foydalanuvchilarda avtomatik yangilanish habari keladi (updates.json orqali)." -ForegroundColor Green
if (-not $SkipApk) {
    Write-Host "Android APK ham release'ga qo'shildi: $ApkFileName" -ForegroundColor Green
}
