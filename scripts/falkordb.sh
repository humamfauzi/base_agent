#!/usr/bin/env bash

set -euo pipefail

# ============================================================
# FalkorDB Local Deployment Script
# - Runs FalkorDB in Docker
# - Uses persistent volume for data durability
# - Creates dedicated Docker network
# - Supports start/stop/restart/logs
# ============================================================

CONTAINER_NAME="falkordb"
IMAGE="falkordb/falkordb:latest"
PORT="6379"

DATA_DIR="$(pwd)/falkordb-data"
NETWORK="falkordb-net"

usage() {
    echo "Usage: $0 {start|stop|restart|logs|status|remove}"
    exit 1
}

create_network() {
    if ! docker network inspect "$NETWORK" >/dev/null 2>&1; then
        echo "[INFO] Creating Docker network: $NETWORK"
        docker network create "$NETWORK"
    fi
}

start_container() {
    mkdir -p "$DATA_DIR"

    create_network

    if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}\$"; then
        echo "[INFO] Container already exists."

        if ! docker ps --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}\$"; then
            echo "[INFO] Starting existing container..."
            docker start "$CONTAINER_NAME"
        else
            echo "[INFO] Container already running."
        fi

        return
    fi

    echo "[INFO] Starting FalkorDB container..."

    docker run -d \
        --name "$CONTAINER_NAME" \
        --network "$NETWORK" \
        -p "${PORT}:6379" \
        -v "${DATA_DIR}:/data" \
        --restart unless-stopped \
        "$IMAGE"

    echo "[INFO] FalkorDB started."
    echo "[INFO] Persistent data directory:"
    echo "       $DATA_DIR"
}

stop_container() {
    echo "[INFO] Stopping container..."
    docker stop "$CONTAINER_NAME"
}

restart_container() {
    stop_container
    start_container
}

logs_container() {
    docker logs -f "$CONTAINER_NAME"
}

status_container() {
    docker ps -a --filter "name=$CONTAINER_NAME"
}

remove_container() {
    echo "[WARNING] Removing container..."
    docker rm -f "$CONTAINER_NAME" || true

    echo "[INFO] Data volume preserved at:"
    echo "       $DATA_DIR"
}

case "${1:-}" in
    start)
        start_container
        ;;
    stop)
        stop_container
        ;;
    restart)
        restart_container
        ;;
    logs)
        logs_container
        ;;
    status)
        status_container
        ;;
    remove)
        remove_container
        ;;
    *)
        usage
        ;;
esac

# chmod +x falkordb.sh
# 
# ./falkordb.sh start
# ./falkordb.sh logs
# ./falkordb.sh status
# ./falkordb.sh stop