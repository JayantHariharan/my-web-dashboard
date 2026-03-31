#!/usr/bin/env bash
#
# Cleanup script for Render deployments
# Use this to manually clean up old/dangling resources
#
# Usage:
#   ./cleanup-old-deployments.sh [--dry-run]
#
# Requirements:
#   - RENDER_API_KEY secret must be available
#   - RENDER_SERVICE_ID environment variable or passed as argument
#

set -euo pipefail

DRY_RUN=false
SERVICE_ID=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --service-id)
      SERVICE_ID="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [--dry-run] [--service-id SERVICE_ID]"
      echo ""
      echo "Options:"
      echo "  --dry-run        Show what would be deleted without actually deleting"
      echo "  --service-id     Render service ID (overrides env var)"
      echo "  --help           Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Check required environment variables
if [ -z "${RENDER_API_KEY:-}" ]; then
  echo "❌ ERROR: RENDER_API_KEY environment variable is required"
  echo "Set it via: export RENDER_API_KEY=your-api-key"
  exit 1
fi

if [ -z "${SERVICE_ID:-}" ] && [ -z "${RENDER_SERVICE_ID:-}" ]; then
  echo "❌ ERROR: Either --service-id or RENDER_SERVICE_ID environment variable is required"
  exit 1
fi

SERVICE_ID="${SERVICE_ID:-${RENDER_SERVICE_ID}}"

echo "🔧 Cleanup utility for Render deployments"
echo "   Service ID: $SERVICE_ID"
echo "   Dry run: $DRY_RUN"
echo ""

# Function to call Render API
call_api() {
  curl -s \
    -H "Authorization: Bearer $RENDER_API_KEY" \
    -H "Content-Type: application/json" \
    "$@"
}

# 1. List all deployments
echo "📋 Fetching deployments..."
deployments=$(call_api "https://api.render.com/v1/services/$SERVICE_ID/deploys" | jq -r '.[] | "\(.id) \(.status) \(.created_at)"' || echo "")

if [ -z "$deployments" ]; then
  echo "No deployments found."
  exit 0
fi

echo "Found deployments:"
echo "$deployments" | while read -r id status created; do
  echo "  $id - $status - $created"
done

# 2. Find old failed/inError deployments (keep last 5)
echo ""
echo "🧹 Finding old failed/inError deployments to clean up..."

# Get deployments older than 7 days (adjust as needed)
CUTOFF_DATE=$(date -d "7 days ago" --utc +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -v-7d -u +%Y-%m-%dT%H:%M:%S)

to_delete=()
while IFS= read -r line; do
  if [ -z "$line" ]; then
    continue
  fi
  id=$(echo "$line" | awk '{print $1}')
  status=$(echo "$line" | awk '{print $2}')
  created=$(echo "$line" | awk '{print $3}')

  # Check if status is errored, failed, build_failed, update_failed, or canceled
  if [[ "$status" =~ ^(errored|failed|build_failed|update_failed|canceled)$ ]]; then
    # Check if older than cutoff
    if [[ "$created" < "$CUTOFF_DATE" ]]; then
      to_delete+=("$id")
    fi
  fi
done <<< "$deployments"

if [ ${#to_delete[@]} -eq 0 ]; then
  echo "✅ No old failed deployments to clean up."
else
  echo "Found ${#to_delete[@]} old failed deployments to delete:"
  printf '  %s\n' "${to_delete[@]}"

  if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Would delete these deployments."
  else
    echo ""
    echo "⚠️  Deleting these deployments..."
    for id in "${to_delete[@]}"; do
      echo "  Deleting $id..."
      if call_api -X DELETE "https://api.render.com/v1/services/$SERVICE_ID/deploys/$id" > /dev/null 2>&1; then
        echo "    ✅ Deleted $id"
      else
        echo "    ❌ Failed to delete $id"
      fi
    done
  fi
fi

# 3. Optional: Clean up old environment variable versions (if needed)
# Render automatically manages env var history, but you can manually prune if needed

echo ""
echo "✅ Cleanup complete!"
