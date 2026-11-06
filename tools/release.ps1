<#
.SYNOPSIS
    Kurs Manager - yangilanish chiqarish (ikki marta bosiladigan qatlam).
.DESCRIPTION
    1. updates.json dan joriy versiyani oqiydi va patch ni oshiradi (1.4.8 -> 1.4.9)
    2. Versiya va izohni so'raydi (Enter = tavsiya etilgan qiymat)
    3. Release allaqachon yaratilmaganini tekshiradi
    4. Qisqa tasdiq so'raydi (push bekor qilib bolmaydi)
    5. build-release.ps1 ni chaqiradi:
       3 ta build (Win10 EXE, Win8 EXE, APK) -> GitHub Release -> updates.json -> git push
.PARAMETER DryRun
    Faqat versiya/izoh hisobini ko'rsatadi, build boshlamaydi va hech narsa yozmaydi.
#>
[CmdletBinding()]
param(
    [switch]$DryRun = $false
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$UpdatesJson = Join-Path $RepoRoot "updates.json"
$BuildScript = Join-Path $PSScriptRoot "build-release.ps1"
$RepoSlug = "hayotbekmaxmudjonov380-arch/kurs-menejeri"
$Line = "=" * 52

Write-Host ""
Write-Host $Line -ForegroundColor Cyan
Write-Host "  Kurs Manager - yangilanish chiqarish" -ForegroundColor Cyan
Write-Host $Line -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path -LiteralPath $UpdatesJson)) {
    throw "updates.json topilmadi: $UpdatesJson"
}
if (-not (Test-Path -LiteralPath $BuildScript)) {
    throw "build-release.ps1 topilmadi: $BuildScript"
}

# --- Joriy holat ---
$Updates = Get-Content -LiteralPath $UpdatesJson -Raw -Encoding UTF8 | ConvertFrom-Json
$Current = [string]$Updates.win10.version
$CurCode = [int]$Updates.android.versionCode

$M = [regex]::Match($Current, '^(\d+)\.(\d+)\.(\d+)$')
if (-not $M.Success) {
    throw "Versiya x.x.x shaklida emas: $Current"
}
$Next = "{0}.{1}.{2}" -f ([int]$M.Groups[1].Value), ([int]$M.Groups[2].Value), ([int]$M.Groups[3].Value + 1)
$NextCode = $CurCode + 1

Write-Host "  Joriy versiya   : $Current" -ForegroundColor Gray
Write-Host "  Joriy code      : $CurCode" -ForegroundColor Gray
Write-Host "  Tavsiya etilgan : $Next   (code $NextCode)" -ForegroundColor Gray
Write-Host "  Oxirgi release  : https://github.com/$RepoSlug/releases" -ForegroundColor Gray
Write-Host ""

# --- Versiya kiritish ---
Write-Host "  Yangi versiya (Enter = $Next): " -NoNewline -ForegroundColor White
$Ver = Read-Host
if ([string]::IsNullOrWhiteSpace($Ver)) { $Ver = $Next }
$Ver = ($Ver.Trim()) -replace '^[vV]', ''

if ($Ver -notmatch '^\d+\.\d+\.\d+$') {
    throw "Versiya notogri kiritildi (kutilgan x.x.x): $Ver"
}
if ([version]$Ver -le [version]$Current) {
    throw "Versiya $Current dan katta bolishi kerak (kiritildi: $Ver)."
}

# --- Release mavjudligini oldindan tekshirish (6 daqiqa builddan keyin yiqilmaslik uchun) ---
$Gh = Get-Command gh -ErrorAction SilentlyContinue
if ($Gh) {
    # gh "release not found" ni stderr ga yozadi; uni shu qatlamda yutamiz.
    $PrevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & gh release view "v$Ver" --repo $RepoSlug --json tagName 2>&1 | Out-Null
    $GhCode = $LASTEXITCODE
    $ErrorActionPreference = $PrevEap
    if ($GhCode -eq 0) {
        throw "Release v$Ver allaqachon mavjud. Boshqa versiya kiriting."
    }
    Write-Host "  Release v$Ver hali yoq - tegri." -ForegroundColor Green
}

# --- Izoh ---
$DefNotes = "Yangilanish tizimi, yangilanish oynasi dizayni va Windows 8 build tuzatildi"
Write-Host ""
Write-Host "  Izoh (Enter = tayyor matn): " -NoNewline -ForegroundColor White
$NotesIn = Read-Host
if ([string]::IsNullOrWhiteSpace($NotesIn)) { $NotesIn = $DefNotes }
$NotesIn = $NotesIn.Trim()

# --- DryRun shu yerda tugaydi ---
if ($DryRun) {
    Write-Host ""
    Write-Host "  DRY RUN - build boshlanmadi, hech narsa ozgartirilmadi." -ForegroundColor Cyan
    Write-Host "  Buyruq: build-release.ps1 -Version $Ver -Notes `"$NotesIn`""
    Write-Host ""
    exit 0
}

# --- Tasdiq (push va Release keyin bekor qilib bolmaydi) ---
Write-Host ""
Write-Host $Line -ForegroundColor Yellow
Write-Host "  TASDIQ" -ForegroundColor Yellow
Write-Host $Line -ForegroundColor Yellow
Write-Host "  Versiya     : $Current  ->  $Ver"
Write-Host "  Android     : versionCode $CurCode  ->  $NextCode"
Write-Host "  Izoh        : $NotesIn"
Write-Host "  Build       : Win10 EXE + Win8 EXE + APK"
Write-Host "  Oxirida     : GitHub Release + updates.json + git push"
Write-Host "  Muddat      : 6-10 daqiqa"
Write-Host $Line -ForegroundColor Yellow
Write-Host ""
Write-Host "  Diqqat: GitHub Release yaratilgandan keyin ochirib bolmaydi." -ForegroundColor Red
Write-Host ""

Write-Host "  Davom etish uchun Enter bosing (bekor qilish uchun boshqa nima yozing): " -NoNewline -ForegroundColor White
$Ok = Read-Host
if ($Ok -ne "") {
    Write-Host ""
    Write-Host "  Bekor qilindi. Hech narsa ozgartirilmadi." -ForegroundColor Yellow
    Write-Host ""
    exit 0
}

# --- Asosiy ish ---
Write-Host ""
Write-Host "  Build boshlandi (6-10 daqiqa)..." -ForegroundColor Cyan
Write-Host ""

$Failed = $false
try {
    & $BuildScript -Version $Ver -Notes $NotesIn
} catch {
    $Failed = $true
    Write-Host ""
    Write-Host "  XATO: $($_.Exception.Message)" -ForegroundColor Red
}

if ($Failed) { exit 1 }

Write-Host ""
Write-Host $Line -ForegroundColor Green
Write-Host "  YAKUNLANDI - foydalanuvchilarga yangilanish yuborildi" -ForegroundColor Green
Write-Host $Line -ForegroundColor Green
Write-Host "  Release : https://github.com/$RepoSlug/releases/tag/v$Ver"
Write-Host "  Eslatma : foydalanuvchilarga 5-10 daqiqada tarqaladi (CDN keshi)."
Write-Host ""
exit 0
