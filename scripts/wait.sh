#!/usr/bin/env bash
# Usage: ./wait.sh host:port -- command args
TIMEOUT=30
QUIET=0

echoerr() { if [ "$QUIET" -ne 1 ]; then echo "$@" 1>&2; fi }

wait_for() {
    local hostport="$1"
    local host=${hostport%:*}
    local port=${hostport#*:}
    shift
    for i in $(seq $TIMEOUT); do
        nc -z "$host" "$port" >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            exec "$@"
        fi
        sleep 1
    done
    echo "Timeout waiting for $hostport" >&2
    exit 1
}

if [ $# -lt 3 ]; then
    echo "Usage: $0 host:port -- command args"
    exit 1
fi

wait_for "$@"