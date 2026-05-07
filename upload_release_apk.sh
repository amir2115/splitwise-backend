#!/bin/zsh

set -euo pipefail

# Update these values before running the script.
API_BASE_URL="https://api.splitwise.ir/api/v1"
ADMIN_SECRET="W>HKR9b5q\6@z8Z2#Ck5),2="
SPLITWISE_VERSION_NAME="1.1.0"
APK_FILE_NAME="app-organic-release.apk"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APK_PATH="$SCRIPT_DIR/android_releases/$SPLITWISE_VERSION_NAME/$APK_FILE_NAME"
UPLOAD_URL="${API_BASE_URL%/}/admin/app-download/apk"

if [[ ! -f "$APK_PATH" ]]; then
  echo "APK file not found: $APK_PATH"
  exit 1
fi

if [[ -z "$ADMIN_SECRET" ]]; then
  echo "Set ADMIN_SECRET at the top of this script before running it."
  exit 1
fi

response="$(
  curl --fail-with-body --silent --show-error \
    -X POST "$UPLOAD_URL" \
    -H "X-Admin-Secret: $ADMIN_SECRET" \
    -F "file=@$APK_PATH;type=application/vnd.android.package-archive"
)"

direct_download_url="$(printf '%s' "$response" | python3 -c 'import json,sys; print(json.load(sys.stdin)["direct_download_url"])')"

echo "Uploaded APK to: $direct_download_url"
