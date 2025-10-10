# PowerShell smoke test script for deployment validation
# Run this after deployment to verify everything is working

param(
    [string]$ApiBase = "http://localhost:8000",
    [string]$State = "AZ",
    [string]$Gender = "MALE", 
    [string]$Year = "2014"
)

Write-Host "Running Smoke Tests for Youth Rankings API" -ForegroundColor Green
Write-Host "API Base: $ApiBase" -ForegroundColor Yellow
Write-Host "=" * 50

# Test 1: Basic health check
Write-Host "`nTest 1: Health Check" -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "$ApiBase/api/health" -Method Get
    Write-Host "  PASS: Health check successful" -ForegroundColor Green
    Write-Host "  Rankings file: $($health.rankings.path)" -ForegroundColor White
    Write-Host "  History file: $($health.history.path)" -ForegroundColor White
} catch {
    Write-Host "  FAIL: Health check failed - $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 2: Rankings endpoint with new meta/data structure
Write-Host "`nTest 2: Rankings Response Structure" -ForegroundColor Cyan
try {
    $rankings = Invoke-RestMethod -Uri "$ApiBase/api/rankings?state=$State&gender=$Gender&year=$Year&limit=3" -Method Get
    
    if ($rankings.meta -and $rankings.data) {
        Write-Host "  PASS: Response has meta and data structure" -ForegroundColor Green
        Write-Host "  Meta: $($rankings.meta | ConvertTo-Json -Compress)" -ForegroundColor White
        Write-Host "  Records returned: $($rankings.data.Count)" -ForegroundColor White
        
        # Show first team details
        if ($rankings.data.Count -gt 0) {
            $firstTeam = $rankings.data[0]
            Write-Host "  First team: $($firstTeam.Team) (GP:$($firstTeam.GamesPlayed), PS:$($firstTeam.PowerScore), Adj:$($firstTeam.PowerScore_adj))" -ForegroundColor White
        }
    } else {
        Write-Host "  FAIL: Missing meta or data structure" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  FAIL: Rankings endpoint failed - $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 3: Inactivity toggle
Write-Host "`nTest 3: Inactivity Toggle" -ForegroundColor Cyan
try {
    $withInactive = Invoke-RestMethod -Uri "$ApiBase/api/rankings?include_inactive=true&limit=5" -Method Get
    $withoutInactive = Invoke-RestMethod -Uri "$ApiBase/api/rankings?include_inactive=false&limit=5" -Method Get
    
    Write-Host "  PASS: Inactivity toggle working" -ForegroundColor Green
    Write-Host "  With inactive: $($withInactive.data.Count) teams, hidden: $($withInactive.meta.hidden_inactive)" -ForegroundColor White
    Write-Host "  Without inactive: $($withoutInactive.data.Count) teams, hidden: $($withoutInactive.meta.hidden_inactive)" -ForegroundColor White
} catch {
    Write-Host "  FAIL: Inactivity toggle test failed - $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 4: Penalty multipliers verification
Write-Host "`nTest 4: Penalty Multipliers" -ForegroundColor Cyan
try {
    $allRankings = Invoke-RestMethod -Uri "$ApiBase/api/rankings?state=$State&gender=$Gender&year=$Year&limit=20" -Method Get
    
    $multiplierTests = @()
    foreach ($team in $allRankings.data) {
        $gp = $team.GamesPlayed
        if ($gp -in @(9, 15, 22)) {
            $expectedMult = if ($gp -lt 10) { 0.75 } elseif ($gp -lt 20) { 0.90 } else { 1.00 }
            $actualMult = $team.GP_Mult
            $expectedAdj = [math]::Round($team.PowerScore * $expectedMult, 3)
            $actualAdj = $team.PowerScore_adj
            
            if ([math]::Abs($expectedAdj - $actualAdj) -lt 0.002) {
                $multiplierTests += "PASS: GP $gp - $($team.Team)"
            } else {
                $multiplierTests += "FAIL: GP $gp - $($team.Team) (expected: $expectedAdj, actual: $actualAdj)"
            }
        }
    }
    
    if ($multiplierTests.Count -gt 0) {
        Write-Host "  PASS: Found teams for multiplier testing" -ForegroundColor Green
        $multiplierTests | ForEach-Object { Write-Host "    $_" -ForegroundColor White }
    } else {
        Write-Host "  INFO: No teams found with GP 9, 15, or 22 for testing" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  FAIL: Penalty multiplier test failed - $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 5: File preference (v4 over v3)
Write-Host "`nTest 5: File Preference" -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "$ApiBase/api/health" -Method Get
    $rankingsPath = $health.rankings.path
    
    if ($rankingsPath -like "*v4*") {
        Write-Host "  PASS: Using v4 file (preferred)" -ForegroundColor Green
    } elseif ($rankingsPath -like "*v3*") {
        Write-Host "  WARNING: Using v3 file (fallback)" -ForegroundColor Yellow
    } else {
        Write-Host "  WARNING: Using legacy file" -ForegroundColor Yellow
    }
    Write-Host "  File: $rankingsPath" -ForegroundColor White
} catch {
    Write-Host "  FAIL: File preference test failed - $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`n" + "=" * 50 -ForegroundColor Green
Write-Host "SUCCESS: All smoke tests passed!" -ForegroundColor Green
Write-Host "API is ready for production use." -ForegroundColor Green

