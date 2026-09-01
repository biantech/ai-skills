#!/bin/zsh
set -euo pipefail

# Stable entrypoint. Select the implementation with JENKINS_CLIENT_IMPL.
case "${JENKINS_CLIENT_IMPL:-python}" in
  python) exec python3 "${0:A:h}/jenkins-dev.py" "$@" ;;
  shell) exec "${0:A:h}/jenkins-dev.sh" "$@" ;;
  *) print -u2 -r -- "[jenkins-api-build] JENKINS_CLIENT_IMPL must be python or shell"; exit 1 ;;
esac
