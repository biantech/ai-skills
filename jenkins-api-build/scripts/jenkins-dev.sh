#!/bin/zsh
set -euo pipefail
unsetopt XTRACE 2>/dev/null || true

readonly JENKINS_BASE_URL="${JENKINS_BASE_URL:-https://jenkins-dev.goldenmilestech.net}"
readonly DEFAULT_DEV_USER="fanxr"
readonly DEFAULT_UAT_RC_USER="tengxq"

die() {
  print -u2 -r -- "[jenkins-api-build] $*"
  exit 1
}

usage() {
  print -u2 -r -- "Usage:
  $0 inspect <dev|uat|rc> <search|3rd-modules|gateway>
  $0 build <dev|uat|rc> <search|3rd-modules|gateway>
  $0 build-modules <dev|uat|rc> <api>...
  $0 build-api <dev|uat|rc> search [--gateway]
  $0 queue-status <dev|uat|rc> <queue-id>
  $0 wait-queue <dev|uat|rc> <search|3rd-modules|gateway> <queue-id>
  $0 status <dev|uat|rc> <search|3rd-modules|gateway> <build-number>
  $0 wait-build <dev|uat|rc> <search|3rd-modules|gateway> <build-number>"
  exit 1
}

require_tools() {
  command -v curl >/dev/null 2>&1 || die "curl is required"
  command -v jq >/dev/null 2>&1 || die "jq is required"
}

require_uint() {
  local name="$1"
  local value="$2"
  [[ "$value" =~ '^[0-9]+$' ]] || die "$name must be a non-negative integer"
}

require_positive_uint() {
  local name="$1"
  local value="$2"
  require_uint "$name" "$value"
  (( value > 0 )) || die "$name must be greater than zero"
}

bounded_seconds() {
  local name="$1"
  local value="$2"
  local minimum="$3"
  local maximum="$4"
  require_uint "$name" "$value"
  (( value >= minimum && value <= maximum )) || die "$name must be between $minimum and $maximum seconds"
  print -r -- "$value"
}

environment_user() {
  case "$1" in
    dev) print -r -- "${JENKINS_DEV_USER:-$DEFAULT_DEV_USER}" ;;
    uat|rc) print -r -- "${JENKINS_UAT_RC_USER:-$DEFAULT_UAT_RC_USER}" ;;
    *) die "Unknown Jenkins environment: $1" ;;
  esac
}

resolve_job() {
  local environment="$1"
  local project="$2"
  environment_user "$environment" >/dev/null
  case "$project" in
    search) print -r -- "search-jar-${environment}" ;;
    3rd-modules) print -r -- "3rd-modules-${environment}" ;;
    gateway) print -r -- "gateway-app-jar-${environment}" ;;
    *) die "Unknown Jenkins project: $project" ;;
  esac
}

credential_token() {
  local environment="$1"
  local value=""
  local token_file=""

  case "$environment" in
    dev)
      value="${JENKINS_DEV_TOKEN:-}"
      token_file="${JENKINS_DEV_TOKEN_FILE:-}"
      ;;
    uat|rc)
      value="${JENKINS_UAT_RC_TOKEN:-}"
      token_file="${JENKINS_UAT_RC_TOKEN_FILE:-}"
      ;;
    *) die "Unknown Jenkins environment: $environment" ;;
  esac

  if [[ -z "$value" && -n "$token_file" ]]; then
    [[ -f "$token_file" && -r "$token_file" ]] || die "Configured Jenkins token file is not readable"
    value="$(<"$token_file")"
  fi

  [[ -n "$value" ]] || die "No Jenkins token configured for $environment"
  [[ "$value" != *$'\n'* && "$value" != *$'\r'* ]] || die "Jenkins token must be a single line"
  [[ "$value" =~ '^[A-Za-z0-9._~+/-]+$' ]] || die "Jenkins token contains unsupported characters"
  print -r -- "$value"
}

credential_config() {
  local environment="$1"
  local user token
  user="$(environment_user "$environment")"
  token="$(credential_token "$environment")"
  [[ "$user" =~ '^[A-Za-z0-9._@-]+$' ]] || die "Jenkins username contains unsupported characters"
  printf 'user = "%s:%s"\n' "$user" "$token"
}

clean_curl_env() {
  env \
    -u JENKINS_DEV_TOKEN \
    -u JENKINS_UAT_RC_TOKEN \
    -u JENKINS_DEV_TOKEN_FILE \
    -u JENKINS_UAT_RC_TOKEN_FILE \
    "$@"
}

authenticated_curl() {
  local environment="$1"
  shift
  credential_config "$environment" | clean_curl_env curl --config - \
    --silent --show-error --fail-with-body --globoff \
    --connect-timeout 10 --max-time 30 \
    "$@"
}

authenticated_crumb_post() {
  local environment="$1"
  local crumb_field="$2"
  local crumb_value="$3"
  shift 3
  {
    credential_config "$environment"
    printf 'header = "%s: %s"\n' "$crumb_field" "$crumb_value"
  } | clean_curl_env curl --config - \
    --silent --show-error --fail-with-body --globoff \
    --connect-timeout 10 --max-time 30 \
    "$@"
}

api_get() {
  local environment="$1"
  local url="$2"
  authenticated_curl "$environment" --header "Accept: application/json" "$url"
}

job_state_json() {
  local environment="$1"
  local job="$2"
  api_get "$environment" "${JENKINS_BASE_URL}/job/${job}/api/json?tree=name,fullName,buildable,inQueue,lastBuild[number,result,building],property[parameterDefinitions[name,type]]"
}

inspect() {
  local environment="$1"
  local job="$2"
  job_state_json "$environment" "$job" \
    | jq -c '{name,fullName,buildable,inQueue,lastBuild,parameters:[.property[]?.parameterDefinitions[]? | {name,type}]}'
}

assert_job_queueable() {
  local environment="$1"
  local job="$2"
  local state
  state="$(job_state_json "$environment" "$job")"
  [[ "$(print -r -- "$state" | jq -r '.buildable')" == "true" ]] || die "Job is not buildable: $job"
  if [[ "${JENKINS_ALLOW_DUPLICATE:-0}" != "1" ]]; then
    [[ "$(print -r -- "$state" | jq -r '.inQueue')" != "true" ]] || die "Job is already queued: $job"
    [[ "$(print -r -- "$state" | jq -r '.lastBuild.building // false')" != "true" ]] || die "Job is already building: $job"
  fi
}

validate_module_parameters() {
  local environment="$1"
  local job="$2"
  shift 2
  (( $# > 0 )) || die "At least one API module is required"

  local state api
  state="$(job_state_json "$environment" "$job")"
  for api in "$@"; do
    [[ "$api" =~ '^[A-Za-z][A-Za-z0-9_-]*$' ]] || die "Invalid API module name: $api"
    print -r -- "$state" | jq -e --arg api "$api" '
      any(.property[]?.parameterDefinitions[]?;
        .name == $api and
        ((.type // "") == "BooleanParameterDefinition" or ((.type // "") | endswith("BooleanParameterDefinition"))))
    ' >/dev/null || die "Job $job has no Boolean parameter named $api"
  done
}

normalize_queue_location() {
  local location="$1"
  local queue_url queue_id prefix
  if [[ "$location" == /* ]]; then
    queue_url="${JENKINS_BASE_URL}${location}"
  else
    queue_url="$location"
  fi

  prefix="${JENKINS_BASE_URL}/queue/item/"
  [[ "$queue_url" == "$prefix"* ]] || die "Jenkins returned a cross-origin queue Location"
  queue_id="${queue_url#$prefix}"
  queue_id="${queue_id%/}"
  require_positive_uint "queue id" "$queue_id"
  [[ "$queue_url" == "${prefix}${queue_id}/" ]] || die "Jenkins returned an invalid queue Location"
  print -r -- "$queue_url"
}

fresh_crumb() {
  local environment="$1"
  local crumb_json field value
  crumb_json="$(api_get "$environment" "${JENKINS_BASE_URL}/crumbIssuer/api/json")"
  field="$(print -r -- "$crumb_json" | jq -er '.crumbRequestField | strings')" || die "Invalid Jenkins crumb field"
  value="$(print -r -- "$crumb_json" | jq -er '.crumb | strings')" || die "Invalid Jenkins crumb value"
  [[ "$field" =~ '^[A-Za-z0-9-]+$' ]] || die "Unsafe Jenkins crumb field"
  [[ "$value" =~ '^[A-Za-z0-9._~+/-]+$' ]] || die "Unsafe Jenkins crumb value"
  jq -cn --arg field "$field" --arg value "$value" '{field:$field,value:$value}'
}

queue_build() {
  local environment="$1"
  local job="$2"
  shift 2
  assert_job_queueable "$environment" "$job"

  local crumb field value headers location queue_url queue_id
  crumb="$(fresh_crumb "$environment")"
  field="$(print -r -- "$crumb" | jq -r '.field')"
  value="$(print -r -- "$crumb" | jq -r '.value')"
  headers="$(authenticated_crumb_post "$environment" "$field" "$value" \
    --output /dev/null --dump-header - --request POST "$@")"
  location="$(print -r -- "$headers" | awk 'BEGIN { IGNORECASE=1 } /^Location:/ { sub(/^[^:]*:[[:space:]]*/, ""); sub(/\r$/, ""); print; exit }')"
  [[ -n "$location" ]] || die "Jenkins build response did not include a queue Location"
  queue_url="$(normalize_queue_location "$location")"
  queue_id="${queue_url#${JENKINS_BASE_URL}/queue/item/}"
  queue_id="${queue_id%/}"
  jq -cn --arg job "$job" --arg queueUrl "$queue_url" --argjson queueId "$queue_id" \
    '{job:$job,queueId:$queueId,queueUrl:$queueUrl}'
}

build() {
  local environment="$1"
  local job="$2"
  queue_build "$environment" "$job" "${JENKINS_BASE_URL}/job/${job}/build"
}

build_modules() {
  local environment="$1"
  shift
  local job
  job="$(resolve_job "$environment" 3rd-modules)" || return 1
  validate_module_parameters "$environment" "$job" "$@"

  local api_arguments=()
  local api
  for api in "$@"; do
    api_arguments+=(--data-urlencode "${api}=true")
  done
  queue_build "$environment" "$job" "${api_arguments[@]}" \
    "${JENKINS_BASE_URL}/job/${job}/buildWithParameters"
}

queue_status() {
  local environment="$1"
  local queue_id="$2"
  require_positive_uint "queue id" "$queue_id"
  api_get "$environment" "${JENKINS_BASE_URL}/queue/item/${queue_id}/api/json?tree=id,cancelled,why,blocked,stuck,task[name,url],executable[number,url]" \
    | jq -c '{id,cancelled,why,blocked,stuck,job:.task.name,executable:(.executable // null)}'
}

wait_queue() {
  local environment="$1"
  local expected_job="$2"
  local queue_id="$3"
  require_positive_uint "queue id" "$queue_id"
  local timeout interval deadline now state job executable_number executable_url expected_url
  timeout="$(bounded_seconds JENKINS_QUEUE_TIMEOUT_SECONDS "${JENKINS_QUEUE_TIMEOUT_SECONDS:-300}" 1 3600)"
  interval="$(bounded_seconds JENKINS_POLL_INTERVAL_SECONDS "${JENKINS_POLL_INTERVAL_SECONDS:-5}" 1 60)"
  deadline=$(( $(date +%s) + timeout ))

  while true; do
    state="$(queue_status "$environment" "$queue_id")"
    [[ "$(print -r -- "$state" | jq -r '.cancelled')" != "true" ]] || die "Jenkins queue item $queue_id was cancelled"
    job="$(print -r -- "$state" | jq -r '.job // empty')"
    [[ -z "$job" || "$job" == "$expected_job" ]] || die "Queue item $queue_id belongs to unexpected Job $job"
    executable_number="$(print -r -- "$state" | jq -r '.executable.number // empty')"
    if [[ -n "$executable_number" ]]; then
      require_positive_uint "build number" "$executable_number"
      executable_url="$(print -r -- "$state" | jq -r '.executable.url // empty')"
      expected_url="${JENKINS_BASE_URL}/job/${expected_job}/${executable_number}/"
      [[ "$executable_url" == "$expected_url" ]] || die "Queue item returned an unexpected build URL"
      print -r -- "$state"
      return 0
    fi
    now="$(date +%s)"
    (( now < deadline )) || die "Timed out waiting for queue item $queue_id"
    sleep "$interval"
  done
}

status() {
  local environment="$1"
  local job="$2"
  local build_number="$3"
  require_positive_uint "build number" "$build_number"
  api_get "$environment" "${JENKINS_BASE_URL}/job/${job}/${build_number}/api/json?tree=number,building,result,timestamp,duration,estimatedDuration,url,displayName" \
    | jq -c '{number,building,result,timestamp,duration,estimatedDuration,url,displayName}'
}

wait_build() {
  local environment="$1"
  local job="$2"
  local build_number="$3"
  require_positive_uint "build number" "$build_number"
  local timeout interval deadline now state
  timeout="$(bounded_seconds JENKINS_BUILD_TIMEOUT_SECONDS "${JENKINS_BUILD_TIMEOUT_SECONDS:-1800}" 1 14400)"
  interval="$(bounded_seconds JENKINS_POLL_INTERVAL_SECONDS "${JENKINS_POLL_INTERVAL_SECONDS:-5}" 1 60)"
  deadline=$(( $(date +%s) + timeout ))

  while true; do
    state="$(status "$environment" "$job" "$build_number")"
    if [[ "$(print -r -- "$state" | jq -r '.building')" == "false" && "$(print -r -- "$state" | jq -r '.result // empty')" != "" ]]; then
      print -r -- "$state"
      return 0
    fi
    now="$(date +%s)"
    (( now < deadline )) || die "Timed out waiting for build ${job} #${build_number}"
    sleep "$interval"
  done
}

wait_queued_build() {
  local environment="$1"
  local job="$2"
  local queued="$3"
  local queue_id queue_state build_number build_state
  queue_id="$(print -r -- "$queued" | jq -er '.queueId')"
  queue_state="$(wait_queue "$environment" "$job" "$queue_id")"
  build_number="$(print -r -- "$queue_state" | jq -er '.executable.number')"
  build_state="$(wait_build "$environment" "$job" "$build_number")"
  jq -cn --argjson queued "$queued" --argjson queue "$queue_state" --argjson build "$build_state" \
    '{queued:$queued,queue:$queue,build:$build}'
}

require_success() {
  local step="$1"
  local state="$2"
  local result
  result="$(print -r -- "$state" | jq -r '.build.result // empty')"
  if [[ "$result" != "SUCCESS" ]]; then
    print -r -- "$state"
    die "$step finished with result ${result:-unknown}; downstream Jobs were not queued"
  fi
}

build_api() {
  local environment="$1"
  local target="$2"
  local gateway="${3:-}"
  [[ "$target" == "search" ]] || die "build-api currently supports only the search target"
  [[ -z "$gateway" || "$gateway" == "--gateway" ]] || die "Unknown build-api option: $gateway"

  local api_job target_job gateway_job=""
  api_job="$(resolve_job "$environment" 3rd-modules)" || return 1
  target_job="$(resolve_job "$environment" "$target")" || return 1
  if [[ "$gateway" == "--gateway" ]]; then
    gateway_job="$(resolve_job "$environment" gateway)" || return 1
  fi

  validate_module_parameters "$environment" "$api_job" "$target"
  assert_job_queueable "$environment" "$api_job"
  assert_job_queueable "$environment" "$target_job"
  [[ -z "$gateway_job" ]] || assert_job_queueable "$environment" "$gateway_job"

  local api_queued api_state target_queued target_state gateway_queued gateway_state
  api_queued="$(build_modules "$environment" "$target")"
  api_state="$(wait_queued_build "$environment" "$api_job" "$api_queued")"
  require_success "API module build" "$api_state"

  target_queued="$(build "$environment" "$target_job")"
  target_state="$(wait_queued_build "$environment" "$target_job" "$target_queued")"
  require_success "Target build" "$target_state"

  if [[ -n "$gateway_job" ]]; then
    gateway_queued="$(build "$environment" "$gateway_job")"
    gateway_state="$(wait_queued_build "$environment" "$gateway_job" "$gateway_queued")"
    require_success "Gateway build" "$gateway_state"
    jq -cn --argjson api "$api_state" --argjson target "$target_state" --argjson gateway "$gateway_state" \
      '{steps:[{name:"3rd-modules",state:$api},{name:"target",state:$target},{name:"gateway",state:$gateway}]}'
  else
    jq -cn --argjson api "$api_state" --argjson target "$target_state" \
      '{steps:[{name:"3rd-modules",state:$api},{name:"target",state:$target}]}'
  fi
}

main() {
  require_tools
  [[ "$JENKINS_BASE_URL" =~ '^https://[A-Za-z0-9.-]+(:[0-9]+)?$' ]] || die "JENKINS_BASE_URL must be an HTTPS origin without a path"
  (( $# > 0 )) || usage
  local command="$1"
  local job=""
  shift
  case "$command" in
    inspect)
      (( $# == 2 )) || usage
      job="$(resolve_job "$1" "$2")" || return 1
      inspect "$1" "$job"
      ;;
    build)
      (( $# == 2 )) || usage
      job="$(resolve_job "$1" "$2")" || return 1
      build "$1" "$job"
      ;;
    build-modules)
      (( $# >= 2 )) || usage
      build_modules "$1" "${@:2}"
      ;;
    build-api)
      (( $# == 2 || $# == 3 )) || usage
      build_api "$1" "$2" "${3:-}"
      ;;
    queue-status)
      (( $# == 2 )) || usage
      environment_user "$1" >/dev/null
      queue_status "$1" "$2"
      ;;
    wait-queue)
      (( $# == 3 )) || usage
      job="$(resolve_job "$1" "$2")" || return 1
      wait_queue "$1" "$job" "$3"
      ;;
    status)
      (( $# == 3 )) || usage
      job="$(resolve_job "$1" "$2")" || return 1
      status "$1" "$job" "$3"
      ;;
    wait-build)
      (( $# == 3 )) || usage
      job="$(resolve_job "$1" "$2")" || return 1
      wait_build "$1" "$job" "$3"
      ;;
    *) usage ;;
  esac
}

main "$@"
