# Render Deployment Diagnostics Script (PowerShell)
# Run this locally to verify your Render configuration before pushing

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "🔍 Render Deployment Diagnostics" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Check required environment variables
Write-Host ""
Write-Host "📋 Checking environment variables..." -ForegroundColor Yellow

$missing = 0

if (-not $env:RENDER_API_KEY) {
    Write-Host "❌ RENDER_API_KEY is not set" -ForegroundColor Red
    $missing++
} else {
    Write-Host "✅ RENDER_API_KEY is set (length: $($env:RENDER_API_KEY.Length))" -ForegroundColor Green
}

if (-not $env:RENDER_SERVICE_ID_TEST) {
    Write-Host "❌ RENDER_SERVICE_ID_TEST is not set (for staging)" -ForegroundColor Red
    $missing++
} else {
    Write-Host "✅ RENDER_SERVICE_ID_TEST is set: $env:RENDER_SERVICE_ID_TEST" -ForegroundColor Green
}

if (-not $env:RENDER_SERVICE_ID_PROD) {
    Write-Host "❌ RENDER_SERVICE_ID_PROD is not set (for production)" -ForegroundColor Red
    $missing++
} else {
    Write-Host "✅ RENDER_SERVICE_ID_PROD is set: $env:RENDER_SERVICE_ID_PROD" -ForegroundColor Green
}

if (-not $env:RENDER_ENV_GROUP_ID_TEST) {
    Write-Host "⚠️  RENDER_ENV_GROUP_ID_TEST is not set (optional for staging)" -ForegroundColor Yellow
} else {
    Write-Host "✅ RENDER_ENV_GROUP_ID_TEST is set: $env:RENDER_ENV_GROUP_ID_TEST" -ForegroundColor Green
}

if (-not $env:RENDER_ENV_GROUP_ID_PROD) {
    Write-Host "⚠️  RENDER_ENV_GROUP_ID_PROD is not set (optional for production)" -ForegroundColor Yellow
} else {
    Write-Host "✅ RENDER_ENV_GROUP_ID_PROD is set: $env:RENDER_ENV_GROUP_ID_PROD" -ForegroundColor Green
}

if ($missing -gt 0) {
    Write-Host ""
    Write-Host "❌ Missing $missing required environment variable(s)" -ForegroundColor Red
    Write-Host "Set them in your shell or environment:"
    Write-Host "  `$env:RENDER_API_KEY = 'your-api-key'"
    Write-Host "  `$env:RENDER_SERVICE_ID_TEST = 'srv-xxx'"
    Write-Host "  `$env:RENDER_SERVICE_ID_PROD = 'srv-yyy'"
    exit 1
}

# Test API connectivity
Write-Host ""
Write-Host "🌐 Testing Render API connectivity..." -ForegroundColor Yellow

function Test-Service {
    param(
        [string]$ServiceId,
        [string]$ServiceName
    )

    Write-Host ""
    Write-Host "Testing $ServiceName ($ServiceId)..." -ForegroundColor Yellow

    $headers = @{
        "Authorization" = "Bearer $env:RENDER_API_KEY"
    }

    try {
        $response = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$ServiceId" -Method Get -Headers $headers -ErrorAction Stop
        $statusCode = 200
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        $responseBody = $_.ErrorDetails.Message
    }

    Write-Host "HTTP Status: $statusCode"

    if ($statusCode -notin 200,201) {
        Write-Host "❌ Failed to access service '$ServiceName'" -ForegroundColor Red
        Write-Host "Response:"
        if ($responseBody) {
            try {
                $json = $responseBody | ConvertFrom-Json
                $json | ConvertTo-Json -Depth 10
            } catch {
                Write-Host $responseBody
            }
        }
        Write-Host ""
        Write-Host "Possible causes:" -ForegroundColor Yellow
        Write-Host "  - Service ID is incorrect"
        Write-Host "  - API key doesn't have access to this service"
        Write-Host "  - Service belongs to a different Render account"
        return $false
    }

    $serviceInfo = $response.service
    Write-Host "✅ Service accessible!" -ForegroundColor Green
    Write-Host "   Name: $($serviceInfo.name)"
    Write-Host "   URL: https://$($serviceInfo.url)"
    Write-Host "   State: $($serviceInfo.state)"
    Write-Host "   Auto-Deploy: $($serviceInfo.autoDeploy)"

    if ($serviceInfo.autoDeploy -eq $true) {
        Write-Host ""
        Write-Host "⚠️  WARNING: Auto-Deploy is ENABLED" -ForegroundColor Yellow
        Write-Host "   This may conflict with GitHub Actions deployments." -ForegroundColor Yellow
        Write-Host "   Consider disabling Auto-Deploy in Render dashboard." -ForegroundColor Yellow
    }

    return $true
}

$test1 = Test-Service -ServiceId $env:RENDER_SERVICE_ID_TEST -ServiceName "Staging Service"
$test2 = Test-Service -ServiceId $env:RENDER_SERVICE_ID_PROD -ServiceName "Production Service"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
if ($test1 -and $test2) {
    Write-Host "✅ All services verified!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Ensure Auto-Deploy is DISABLED in Render dashboard"
    Write-Host "2. Push to develop branch to test staging deployment"
    Write-Host "3. Check GitHub Actions tab for workflow progress"
    Write-Host "4. If deployment fails, check the logs for specific error"
} else {
    Write-Host "❌ Some services failed verification" -ForegroundColor Red
    Write-Host "Fix the issues above before pushing to GitHub" -ForegroundColor Red
}
Write-Host "==========================================" -ForegroundColor Cyan
