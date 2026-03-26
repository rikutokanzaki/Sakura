#!/bin/bash

# Uninstallation process begins
if sudo -v; then
  echo "Authentication succeeded."
else
  echo "Authentication failed."
  exit 1
fi

set -a
source ./.env
set +a

COMPOSE_DIR=./compose

select_option() {
  local prompt="$1"
  local default_index="$2"
  shift 2
  local options=("$@")
  local input idx

  echo "$prompt (Enter=$default_index)" >&2
  for i in "${!options[@]}"; do
    printf "  %2d) %s\n" "$((i+1))" "${options[$i]}" >&2
  done

  read -p "Selection (number or name): " input
  [ -z "$input" ] && input="$default_index"

  if [[ "$input" =~ ^[0-9]+$ ]]; then
    idx=$((input-1))
    if [ "$idx" -lt 0 ] || [ "$idx" -ge "${#options[@]}" ]; then
      echo ""
      return 1
    fi
    echo "${options[$idx]}"
    return 0
  fi

  for opt in "${options[@]}"; do
    if [ "$opt" = "$input" ]; then
      echo "$opt"
      return 0
    fi
  done

  echo ""
  return 1
}

MODE_OPTIONS=("dynamic" "static" "standalone" "rotate")
SELECTED_MODE=$(select_option "Select deployment mode to remove" 1 "${MODE_OPTIONS[@]}")
if [ $? -ne 0 ] || [ -z "$SELECTED_MODE" ]; then
  echo "Error: invalid mode selection"
  exit 1
fi

PROFILE_OPTIONS=()
case "$SELECTED_MODE" in
  dynamic|static|rotate)
    PROFILE_OPTIONS=("standard" "http" "ssh")
    ;;
  standalone)
    PROFILE_OPTIONS=("cowrie" "heralding" "h0neytr4p")
    ;;
  *)
    echo "Error: unsupported mode: $SELECTED_MODE"
    exit 1
    ;;
esac

SELECTED_PROFILE=$(select_option "Select startup profile to remove" 1 "${PROFILE_OPTIONS[@]}")
if [ $? -ne 0 ] || [ -z "$SELECTED_PROFILE" ]; then
  echo "Error: invalid profile selection"
  exit 1
fi

case "$SELECTED_MODE:$SELECTED_PROFILE" in
  dynamic:standard)
    SELECTED_COMPOSE_FILE="$COMPOSE_DIR/dynamic/standard.yml"
    ;;
  dynamic:http)
    SELECTED_COMPOSE_FILE="$COMPOSE_DIR/dynamic/http.yml"
    ;;
  dynamic:ssh)
    SELECTED_COMPOSE_FILE="$COMPOSE_DIR/dynamic/ssh.yml"
    ;;
  static:standard)
    SELECTED_COMPOSE_FILE="$COMPOSE_DIR/static/standard.yml"
    ;;
  static:http)
    SELECTED_COMPOSE_FILE="$COMPOSE_DIR/static/http.yml"
    ;;
  static:ssh)
    SELECTED_COMPOSE_FILE="$COMPOSE_DIR/static/ssh.yml"
    ;;
  standalone:cowrie)
    SELECTED_COMPOSE_FILE="$COMPOSE_DIR/standalone/cowrie.yml"
    ;;
  standalone:heralding)
    SELECTED_COMPOSE_FILE="$COMPOSE_DIR/standalone/heralding.yml"
    ;;
  standalone:h0neytr4p)
    SELECTED_COMPOSE_FILE="$COMPOSE_DIR/standalone/h0neytr4p.yml"
    ;;
  rotate:standard)
    SELECTED_COMPOSE_FILE="$COMPOSE_DIR/rotate/standard.yml"
    ;;
  rotate:http)
    SELECTED_COMPOSE_FILE="$COMPOSE_DIR/rotate/http.yml"
    ;;
  rotate:ssh)
    SELECTED_COMPOSE_FILE="$COMPOSE_DIR/rotate/ssh.yml"
    ;;
  *)
    echo "Error: unsupported selection: $SELECTED_MODE/$SELECTED_PROFILE"
    exit 1
    ;;
esac

if [ ! -f "$SELECTED_COMPOSE_FILE" ]; then
  echo "Compose file not found: $SELECTED_COMPOSE_FILE"
  exit 1
fi

echo
echo "Deleting services with Docker Compose..."
echo

if ! docker compose -f "$SELECTED_COMPOSE_FILE" down --rmi all --volumes --remove-orphans; then
  echo "Error: docker compose down failed."
  exit 1
fi

echo
echo "Handling data backup..."
echo

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_NAME="$(basename "$SCRIPT_DIR")"

INSTALL_DATE_FILE=".install_date"
TODAY=$(date +"%Y%m%d")
TIMENOW=$(date +"%H%M%S")

if [ -f "$INSTALL_DATE_FILE" ]; then
  INSTALL_DATE=$(cat "$INSTALL_DATE_FILE")
else
  INSTALL_DATE="unknown"
fi

PERIOD_DIR="${INSTALL_DATE}-${TODAY}-${TIMENOW}"

ARCHIVE_BASE="${ARCHIVE_DATA_PATH}/${PROJECT_NAME}"
TARGET_DIR="${ARCHIVE_BASE}/${PERIOD_DIR}"

if [ -d "./data" ]; then
  echo "Creating archive dir: $TARGET_DIR"
  if ! mkdir -p "$TARGET_DIR"; then
    echo "Error: cannot create '$TARGET_DIR' (check ARCHIVE_DATA_PATH and permissions)." >&2
  else
    echo "Copying ./data -> ${TARGET_DIR}/data"
    if cp -a ./data "${TARGET_DIR}/data"; then
      echo "Captured malicious activity data copied successfully."
      echo
      echo "Removing original ./data directory..."
      if sudo rm -rf ./data; then
        echo "Original ./data directory removed."
      else
        echo "Error: failed to remove original ./data directory." >&2
      fi
    else
      echo "Error: failed to copy data to '${TARGET_DIR}/data'." >&2
    fi
  fi
else
  echo "No ./data directory found. Skipping."
fi

echo
echo "Uninstallation complete."
