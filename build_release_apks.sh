#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ANDROID_DIR="$SCRIPT_DIR/android"

# Release settings. Update these values before running the script.
SPLITWISE_VERSION_CODE="3"
SPLITWISE_VERSION_NAME="1.2.0"
SPLITWISE_API_BASE_URL="https://api.splitwise.ir/api/v1"
SPLITWISE_RELEASE_STORE_FILE="/Users/amir/keys/splitwise.jks"
SPLITWISE_RELEASE_STORE_PASSWORD="Amir@31357900"
SPLITWISE_RELEASE_KEY_ALIAS="key-splitwise"
SPLITWISE_RELEASE_KEY_PASSWORD="Amir@31357900"

# Optional distribution URLs. Defaults exist in Gradle, but keeping them here makes
# the release inputs explicit and easier to edit from one place.
SPLITWISE_BAZAAR_STORE_URL="https://cafebazaar.ir/app/com.encer.splitwise"
SPLITWISE_MYKET_STORE_URL="https://myket.ir/app/com.encer.splitwise"
SPLITWISE_ORGANIC_STORE_URL="https://splitwise.ir/download-app"

RELEASE_DIR="$SCRIPT_DIR/android_releases/$SPLITWISE_VERSION_NAME"

if [[ ! -d "$ANDROID_DIR" ]]; then
  echo "Android project not found: $ANDROID_DIR"
  exit 1
fi

if [[ ! -f "$SPLITWISE_RELEASE_STORE_FILE" ]]; then
  echo "Keystore file not found: $SPLITWISE_RELEASE_STORE_FILE"
  echo "Update SPLITWISE_RELEASE_STORE_FILE at the top of this script."
  exit 1
fi

mkdir -p "$RELEASE_DIR"

build_variant() {
  local variant="$1"
  local apk_output_name="$2"
  local aab_output_name="$3"
  local apk_path="$ANDROID_DIR/app/build/outputs/apk/${variant}/release/app-${variant}-release.apk"
  local aab_path="$ANDROID_DIR/app/build/outputs/bundle/${variant}Release/app-${variant}-release.aab"

  echo ""
  echo "==> Building ${variant} release APK and AAB"

  (
    cd "$ANDROID_DIR"
    ./gradlew ":app:assemble${variant:u}Release" \
      ":app:bundle${variant:u}Release" \
      -PSPLITWISE_VERSION_CODE="$SPLITWISE_VERSION_CODE" \
      -PSPLITWISE_VERSION_NAME="$SPLITWISE_VERSION_NAME" \
      -PSPLITWISE_API_BASE_URL="$SPLITWISE_API_BASE_URL" \
      -PSPLITWISE_RELEASE_STORE_FILE="$SPLITWISE_RELEASE_STORE_FILE" \
      -PSPLITWISE_RELEASE_STORE_PASSWORD="$SPLITWISE_RELEASE_STORE_PASSWORD" \
      -PSPLITWISE_RELEASE_KEY_ALIAS="$SPLITWISE_RELEASE_KEY_ALIAS" \
      -PSPLITWISE_RELEASE_KEY_PASSWORD="$SPLITWISE_RELEASE_KEY_PASSWORD" \
      -PSPLITWISE_BAZAAR_STORE_URL="$SPLITWISE_BAZAAR_STORE_URL" \
      -PSPLITWISE_MYKET_STORE_URL="$SPLITWISE_MYKET_STORE_URL" \
      -PSPLITWISE_ORGANIC_STORE_URL="$SPLITWISE_ORGANIC_STORE_URL"
  )

  if [[ ! -f "$apk_path" ]]; then
    echo "Expected APK was not produced: $apk_path"
    exit 1
  fi

  if [[ ! -f "$aab_path" ]]; then
    echo "Expected AAB was not produced: $aab_path"
    exit 1
  fi

  cp "$apk_path" "$RELEASE_DIR/$apk_output_name"
  cp "$aab_path" "$RELEASE_DIR/$aab_output_name"
  echo "Saved: $RELEASE_DIR/$apk_output_name"
  echo "Saved: $RELEASE_DIR/$aab_output_name"
}

build_variant "bazaar" "app-bazaar-release.apk" "app-bazaar-release.aab"
build_variant "myket" "app-myket-release.apk" "app-myket-release.aab"
build_variant "organic" "app-organic-release.apk" "app-organic-release.aab"

echo ""
echo "All release APKs and AABs are ready in: $RELEASE_DIR"
echo "- $RELEASE_DIR/app-bazaar-release.apk"
echo "- $RELEASE_DIR/app-bazaar-release.aab"
echo "- $RELEASE_DIR/app-myket-release.apk"
echo "- $RELEASE_DIR/app-myket-release.aab"
echo "- $RELEASE_DIR/app-organic-release.apk"
echo "- $RELEASE_DIR/app-organic-release.aab"

if [[ -t 0 ]]; then
  echo ""
  read "REPLY?Press Enter to close..."
fi
