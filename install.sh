#!/bin/bash

SAKURAINSTALLER=$(
  cat <<"EOF"
 ____        _                         ___           _        _ _
/ ___|  __ _| | ___   _ _ __ __ _     |_ _|_ __  ___| |_ __ _| | | ___ _ __
\___ \ / _` | |/ / | | | '__/ _` |     | || '_ \/ __| __/ _` | | |/ _ \ '__|
 ___) | (_| |   <| |_| | | | (_| |     | || | | \__ \ || (_| | | |  __/ |
|____/ \__,_|_|\_\\__,_|_|  \__,_|    |___|_| |_|___/\__\__,_|_|_|\___|_|
EOF
)

# Installation process begins
if sudo -v; then
  echo "Authentication succeeded."
else
  echo "Authentication failed."
  exit 1
fi

set -a
source ./.env
set +a

if [ -z "$KIBANA_PASSWORD" ]; then
  echo "Error: KIBANA_PASSWORD is not set."
  exit 1
fi

if [ -z "$SAKURA_DATA_PATH" ]; then
  echo "Error: SAKURA_DATA_PATH is not set."
  exit 1
fi

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
SELECTED_MODE=$(select_option "Select deployment mode" 1 "${MODE_OPTIONS[@]}")
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

SELECTED_PROFILE=$(select_option "Select startup profile" 1 "${PROFILE_OPTIONS[@]}")
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

SELECTED_TYPE="$SELECTED_MODE/$SELECTED_PROFILE"

upsert_env_var() {
  local key="$1"
  local value="$2"
  local env_file="./.env"
  local tmp_file

  if [ ! -f "$env_file" ]; then
    echo "Error: $env_file not found"
    exit 1
  fi

  tmp_file=$(mktemp)
  awk -v k="$key" -v v="$value" '
    BEGIN { updated = 0 }
    $0 ~ "^[[:space:]]*" k "[[:space:]]*=" {
      print k "=" v
      updated = 1
      next
    }
    { print }
    END {
      if (updated == 0) {
        print k "=" v
      }
    }
  ' "$env_file" > "$tmp_file"

  if ! mv "$tmp_file" "$env_file"; then
    rm -f "$tmp_file"
    echo "Error: failed to update $env_file"
    exit 1
  fi
}

DISPATCHER_HTTP_TARGET="auto"
if [ "$SELECTED_MODE" = "standalone" ]; then
  case "$SELECTED_PROFILE" in
    heralding|h0neytr4p)
      DISPATCHER_HTTP_TARGET="$SELECTED_PROFILE"
      ;;
    *)
      DISPATCHER_HTTP_TARGET="h0neytr4p"
      ;;
  esac
fi

upsert_env_var "DISPATCHER_MODE" "$SELECTED_MODE"
upsert_env_var "DISPATCHER_HTTP_TARGET" "$DISPATCHER_HTTP_TARGET"
upsert_env_var "SELECTED_COMPOSE_FILE" "$SELECTED_COMPOSE_FILE"
upsert_env_var "SELECTED_PROFILE" "$SELECTED_PROFILE"

set -a
source ./.env
set +a

SELECTED_COMPOSE_DIR=$(dirname "$(realpath -m "$SELECTED_COMPOSE_FILE")")

if [[ "$SAKURA_DATA_PATH" = /* ]]; then
  HOST_DATA_PATH="$SAKURA_DATA_PATH"
else
  HOST_DATA_PATH="$(realpath -m "$SELECTED_COMPOSE_DIR/$SAKURA_DATA_PATH")"
fi

echo "Resolved host data path: $HOST_DATA_PATH"

if [ ! -f "$SELECTED_COMPOSE_FILE" ]; then
  echo "Compose file not found: $SELECTED_COMPOSE_FILE"
  exit 1
fi

echo "Selected type: $SELECTED_TYPE"
echo "Selected compose file: $SELECTED_COMPOSE_FILE"
echo

echo "$SAKURAINSTALLER"
echo
echo

sudo mkdir -p -m 777 "$HOST_DATA_PATH/cowrie"
sudo mkdir -p -m 755 "$HOST_DATA_PATH/wordpot/log"
sudo chown 2000:2000 "$HOST_DATA_PATH/wordpot/log"
sudo mkdir -p -m 755 "$HOST_DATA_PATH/h0neytr4p/log"
sudo chown 2000:2000 "$HOST_DATA_PATH/h0neytr4p/log"
sudo mkdir -p -m 755 "$HOST_DATA_PATH/h0neytr4p/payloads"
sudo chown 2000:2000 "$HOST_DATA_PATH/h0neytr4p/payloads"
sudo mkdir -p -m 755 "$HOST_DATA_PATH/heralding"
sudo chmod 444 ./elk/metricbeat/metricbeat.yml
sudo chown root:root ./elk/metricbeat/metricbeat.yml

STOP_CANDIDATES=()
case "$SELECTED_MODE" in
  dynamic|rotate)
    STOP_CANDIDATES=("cowrie" "h0neytr4p" "wordpot")
    ;;
  static|standalone)
    STOP_CANDIDATES=()
    ;;
  *)
    STOP_CANDIDATES=()
    ;;
esac

echo "Starting services with Docker Compose..."
if ! docker compose -f "$SELECTED_COMPOSE_FILE" up -d; then
  echo "Error: docker compose up failed. Aborting without stopping services or importing Kibana objects."
  exit 1
fi

AVAILABLE_SERVICES=$(docker compose -f "$SELECTED_COMPOSE_FILE" ps --services 2>/dev/null || true)
STOP_TARGETS=()

for service in "${STOP_CANDIDATES[@]}"; do
  if echo "$AVAILABLE_SERVICES" | grep -qx "$service"; then
    STOP_TARGETS+=("$service")
  else
    echo "Skip stop (service not present in this profile): $service"
  fi
done

if [ "${#STOP_TARGETS[@]}" -gt 0 ]; then
  echo "Stopping standby honeypot services: ${STOP_TARGETS[*]}"
  docker compose -f "$SELECTED_COMPOSE_FILE" stop "${STOP_TARGETS[@]}"
  echo
  echo "All specified services have been stopped."
else
  echo "No matching honeypot services to stop."
fi

echo
echo "Importing Kibana saved objects..."
echo

response=$(curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:64297/api/saved_objects/_import?createNewCopies=true \
  -u elastic:"$KIBANA_PASSWORD" \
  -H "kbn-xsrf: true" \
  -F file=@./elk/kibana/export.ndjson)

body=$(echo "$response" | sed '$d')
status=$(echo "$response" | tail -n1)

echo
echo "$body"
echo

if [ "$status" = "200" ]; then
  echo "Kibana saved objects completely imported."
else
  echo "Failed to import Kibana saved objects. HTTP status: $status"
fi

INSTALL_DATE=$(date +"%Y%m%d")
cat > .install_info <<EOF
INSTALL_DATE=${INSTALL_DATE}
PREV_SELECTED_MODE=${SELECTED_MODE}
PREV_SELECTED_PROFILE=${SELECTED_PROFILE}
SELECTED_COMPOSE_FILE=${SELECTED_COMPOSE_FILE}
EOF

echo
echo "Installation metadata recorded (.install_info)."
