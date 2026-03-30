#!/bin/bash
# Render Deployment Diagnostics Script
# Run this locally to verify your Render configuration before pushing

echo "=========================================="
echo "🔍 Render Deployment Diagnostics"
echo "=========================================="

# Check required environment variables
echo ""
echo "📋 Checking environment variables..."

missing=0
if [ -z "$RENDER_API_KEY" ]; then
    echo "❌ RENDER_API_KEY is not set"
    missing=$((missing + 1))
else
    echo "✅ RENDER_API_KEY is set (length: ${#RENDER_API_KEY})"
fi

if [ -z "$RENDER_SERVICE_ID_TEST" ]; then
    echo "❌ RENDER_SERVICE_ID_TEST is not set (for staging)"
    missing=$((missing + 1))
else
    echo "✅ RENDER_SERVICE_ID_TEST is set: $RENDER_SERVICE_ID_TEST"
fi

if [ -z "$RENDER_SERVICE_ID_PROD" ]; then
    echo "❌ RENDER_SERVICE_ID_PROD is not set (for production)"
    missing=$((missing + 1))
else
    echo "✅ RENDER_SERVICE_ID_PROD is set: $RENDER_SERVICE_ID_PROD"
fi

if [ -z "$RENDER_ENV_GROUP_ID_TEST" ]; then
    echo "⚠️  RENDER_ENV_GROUP_ID_TEST is not set (optional for staging)"
else
    echo "✅ RENDER_ENV_GROUP_ID_TEST is set: $RENDER_ENV_GROUP_ID_TEST"
fi

if [ -z "$RENDER_ENV_GROUP_ID_PROD" ]; then
    echo "⚠️  RENDER_ENV_GROUP_ID_PROD is not set (optional for production)"
else
    echo "✅ RENDER_ENV_GROUP_ID_PROD is set: $RENDER_ENV_GROUP_ID_PROD"
fi

if [ $missing -gt 0 ]; then
    echo ""
    echo "❌ Missing $missing required environment variable(s)"
    echo "Set them in your shell or in .env file:"
    echo "  export RENDER_API_KEY='your-api-key'"
    echo "  export RENDER_SERVICE_ID_TEST='srv-xxx'"
    echo "  export RENDER_SERVICE_ID_PROD='srv-yyy'"
    exit 1
fi

# Test API connectivity
echo ""
echo "🌐 Testing Render API connectivity..."

test_service() {
    local service_id=$1
    local service_name=$2

    echo ""
    echo "Testing $service_name ($service_id)..."

    response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
        "https://api.render.com/v1/services/$service_id" \
        -H "Authorization: Bearer $RENDER_API_KEY")

    http_code=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
    response_body=$(echo "$response" | sed '/HTTP_STATUS:/d')

    echo "HTTP Status: $http_code"

    if [[ ! "$http_code" =~ ^(200|201)$ ]]; then
        echo "❌ Failed to access service '$service_name'"
        echo "Response:"
        echo "$response_body" | jq '.' 2>/dev/null || echo "$response_body"
        echo ""
        echo "Possible causes:"
        echo "  - Service ID is incorrect"
        echo "  - API key doesn't have access to this service"
        echo "  - Service belongs to a different Render account"
        return 1
    fi

    service_info=$(echo "$response_body" | jq -r '.service // {}')
    name=$(echo "$service_info" | jq -r '.name // "N/A"')
    url=$(echo "$service_info" | jq -r '.url // "N/A"')
    state=$(echo "$service_info" | jq -r '.state // "N/A"')
    autodeploy=$(echo "$service_info" | jq -r '.autoDeploy // "N/A"')

    echo "✅ Service accessible!"
    echo "   Name: $name"
    echo "   URL: https://$url"
    echo "   State: $state"
    echo "   Auto-Deploy: $autodeploy"

    if [ "$autodeploy" = "true" ]; then
        echo ""
        echo "⚠️  WARNING: Auto-Deploy is ENABLED"
        echo "   This may conflict with GitHub Actions deployments."
        echo "   Consider disabling Auto-Deploy in Render dashboard."
    fi

    return 0
}

test_service "$RENDER_SERVICE_ID_TEST" "Staging Service"
test_result1=$?

test_service "$RENDER_SERVICE_ID_PROD" "Production Service"
test_result2=$?

echo ""
echo "=========================================="
if [ $test_result1 -eq 0 ] && [ $test_result2 -eq 0 ]; then
    echo "✅ All services verified!"
    echo ""
    echo "Next steps:"
    echo "1. Ensure Auto-Deploy is DISABLED in Render dashboard"
    echo "2. Push to develop branch to test staging deployment"
    echo "3. Check GitHub Actions tab for workflow progress"
    echo "4. If deployment fails, check the logs for specific error"
else
    echo "❌ Some services failed verification"
    echo "Fix the issues above before pushing to GitHub"
fi
echo "=========================================="
