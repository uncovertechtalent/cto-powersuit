#!/bin/sh
# Routing tests for alertmanager.yml. Each case sends one label set through the
# routing tree and checks the receiver it reaches. Exit 1 on any mismatch.
#
# Run from the repository root:
#   sh observability/alertmanager/tests/routes.sh
# Without a local amtool, run it from the Alertmanager image:
#   AMTOOL="docker run --rm -v $PWD/observability/alertmanager:/am:ro --entrypoint amtool prom/alertmanager:v0.28.1" \
#   CONFIG=/am/alertmanager.yml sh observability/alertmanager/tests/routes.sh
set -u

AMTOOL="${AMTOOL:-amtool}"
CONFIG="${CONFIG:-observability/alertmanager/alertmanager.yml}"
failed=0

expect() {
  want="$1"
  shift
  if $AMTOOL config routes test --config.file="$CONFIG" --verify.receivers="$want" "$@" >/dev/null 2>&1; then
    echo "ok   $* -> $want"
  else
    echo "FAIL $* -> want $want, got: $($AMTOOL config routes test --config.file="$CONFIG" "$@" 2>&1)"
    failed=1
  fi
}

# One case per team and severity, plus the fallbacks.
expect platform-page   route=platform severity=page
expect platform-ticket route=platform severity=ticket
expect platform-ticket route=platform severity=info
expect app-page        route=app severity=page
expect app-ticket      route=app severity=ticket
expect default         route=unknown severity=page
expect default         severity=page

exit "$failed"
