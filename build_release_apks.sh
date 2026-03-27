#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ANDROID_DIR="$SCRIPT_DIR/android"

# Release settings. Update these values before running the script.
OFFLINE_SPLITWISE_VERSION_CODE="42"
OFFLINE_SPLITWISE_VERSION_NAME="1.4.0"
OFFLINE_SPLITWISE_API_BASE_URL="https://api.splitwise.ir/api/v1"
OFFLINE_SPLITWISE_RELEASE_STORE_FILE="/Users/amir/keys/offline-splitwise-release.jks"
OFFLINE_SPLITWISE_RELEASE_STORE_PASSWORD="your-store-password"
OFFLINE_SPLITWISE_RELEASE_KEY_ALIAS="offline-splitwise"
OFFLINE_SPLITWISE_RELEASE_KEY_PASSWORD="your-key-password"

# Optional distribution URLs. Defaults exist in Gradle, but keeping them here makes
# the release inputs explicit and easier to edit from one place.
OFFLINE_SPLITWISE_BAZAAR_STORE_URL="https://cafebazaar.ir/app/com.encer.offlinesplitwise"
OFFLINE_SPLITWISE_MYKET_STORE_URL="https://myket.ir/app/com.encer.offlinesplitwise"
OFFLINE_SPLITWISE_ORGANIC_STORE_URL="https://splitwise.ir/downloads/offline-splitwise"

if [[ ! -d "$ANDROID_DIR" ]]; then
  echo "Android project not found: $ANDROID_DIR"
  exit 1
fi

if [[ ! -f "$OFFLINE_SPLITWISE_RELEASE_STORE_FILE" ]]; then
  echo "Keystore file not found: $OFFLINE_SPLITWISE_RELEASE_STORE_FILE"
  echo "Update OFFLINE_SPLITWISE_RELEASE_STORE_FILE at the top of this script."
  exit 1
fi

build_variant() {
  local variant="$1"
  local output_name="$2"
  local apk_path="$ANDROID_DIR/app/build/outputs/apk/${variant}/release/app-${variant}-release.apk"

  echo ""
  echo "==> Building ${variant} release"

  (
    cd "$ANDROID_DIR"
    ./gradlew ":app:assemble${variant:u}Release" \
      -POFFLINE_SPLITWISE_VERSION_CODE="$OFFLINE_SPLITWISE_VERSION_CODE" \
      -POFFLINE_SPLITWISE_VERSION_NAME="$OFFLINE_SPLITWISE_VERSION_NAME" \
      -POFFLINE_SPLITWISE_API_BASE_URL="$OFFLINE_SPLITWISE_API_BASE_URL" \
      -POFFLINE_SPLITWISE_RELEASE_STORE_FILE="$OFFLINE_SPLITWISE_RELEASE_STORE_FILE" \
      -POFFLINE_SPLITWISE_RELEASE_STORE_PASSWORD="$OFFLINE_SPLITWISE_RELEASE_STORE_PASSWORD" \
      -POFFLINE_SPLITWISE_RELEASE_KEY_ALIAS="$OFFLINE_SPLITWISE_RELEASE_KEY_ALIAS" \
      -POFFLINE_SPLITWISE_RELEASE_KEY_PASSWORD="$OFFLINE_SPLITWISE_RELEASE_KEY_PASSWORD" \
      -POFFLINE_SPLITWISE_BAZAAR_STORE_URL="$OFFLINE_SPLITWISE_BAZAAR_STORE_URL" \
      -POFFLINE_SPLITWISE_MYKET_STORE_URL="$OFFLINE_SPLITWISE_MYKET_STORE_URL" \
      -POFFLINE_SPLITWISE_ORGANIC_STORE_URL="$OFFLINE_SPLITWISE_ORGANIC_STORE_URL"
  )

  if [[ ! -f "$apk_path" ]]; then
    echo "Expected APK was not produced: $apk_path"
    exit 1
  fi

  cp "$apk_path" "$SCRIPT_DIR/$output_name"
  echo "Saved: $SCRIPT_DIR/$output_name"
}

build_variant "bazaar" "app-bazaar-release.apk"
build_variant "myket" "app-myket-release.apk"
build_variant "organic" "app-organic-release.apk"

echo ""
echo "All release APKs are ready next to this script:"
echo "- $SCRIPT_DIR/app-bazaar-release.apk"
echo "- $SCRIPT_DIR/app-myket-release.apk"
echo "- $SCRIPT_DIR/app-organic-release.apk"

if [[ -t 0 ]]; then
  echo ""
  read "REPLY?Press Enter to close..."
fi
