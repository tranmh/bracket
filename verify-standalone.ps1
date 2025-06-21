Write-Host "🔍 Verifying Standalone Implementation..." -ForegroundColor Cyan

$checks = @()

# Check file structure
$requiredFiles = @(
    "standalone/build/backend.py",
    "standalone/build/frontend.py", 
    "standalone/electron/main.js",
    "standalone/electron/package.json",
    "build-standalone.ps1"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        $checks += "✅ $file exists"
    } else {
        $checks += "❌ $file missing"
    }
}

# Check if database modification was made
$dbFile = "backend/bracket/database.py"
if (Test-Path $dbFile) {
    $content = Get-Content $dbFile -Raw
    if ($content -like "*BRACKET_STANDALONE*") {
        $checks += "✅ Database modification applied"
    } else {
        $checks += "❌ Database modification needed"
    }
} else {
    $checks += "❌ Database file not found"
}

# Display results
foreach ($check in $checks) {
    if ($check.StartsWith("✅")) {
        Write-Host $check -ForegroundColor Green
    } else {
        Write-Host $check -ForegroundColor Red
    }
}

$passed = ($checks | Where-Object { $_.StartsWith("✅") }).Count
$total = $checks.Count

Write-Host "`n📊 Verification: $passed/$total checks passed" -ForegroundColor $(if ($passed -eq $total) { "Green" } else { "Yellow" })

if ($passed -eq $total) {
    Write-Host "🎉 Ready to build! Run: .\build-standalone.ps1" -ForegroundColor Green
} else {
    Write-Host "⚠️ Please address the missing items above" -ForegroundColor Yellow
}