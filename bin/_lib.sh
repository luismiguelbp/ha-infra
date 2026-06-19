#!/usr/bin/env bash
# Shared helpers for bin/ scripts. Source from other scripts; do not run directly.

project_root() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "$script_dir/.." && pwd
}

ansible_cd() {
  cd "$(project_root)/ansible"
}

ensure_ansible() {
  if ! command -v ansible-playbook >/dev/null 2>&1; then
    echo "ansible-playbook not found. Install with: brew install ansible" >&2
    exit 1
  fi
}

load_project_env() {
  local env_file
  env_file="$(project_root)/.env"
  if [[ -f "$env_file" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$env_file"
    set +a
  fi
}

# Set by verify_managed_infra_config for ansible wrappers.
MANAGED_INFRA_INVENTORY_FILE=""
MANAGED_INFRA_DOCKER=""

# Required deploy files under MANAGED_INFRA_CONFIG/docker (must not be repo templates).
EDGE_STACK_REQUIRED_FILES=(
  compose.yml
  compose-mosquitto.yml
  compose-node-red.yml
  compose-postgresql.yml
  compose-grafana.yml
  env.example
)

# Verify external configs and set MANAGED_INFRA_* paths for Ansible.
# Refuses repo templates so deployments always use MANAGED_INFRA_CONFIG.
verify_managed_infra_config() {
  load_project_env

  if [[ -z "${MANAGED_INFRA_CONFIG:-}" ]]; then
    echo "MANAGED_INFRA_CONFIG is not set. Add it to .env (see .env.example)." >&2
    echo "Refusing to run: this repository contains templates only." >&2
    exit 1
  fi

  if [[ ! -d "$MANAGED_INFRA_CONFIG" ]]; then
    echo "MANAGED_INFRA_CONFIG not found: $MANAGED_INFRA_CONFIG" >&2
    exit 1
  fi

  local inventory_src="$MANAGED_INFRA_CONFIG/ansible/inventory/hosts.yml"
  if [[ ! -f "$inventory_src" ]]; then
    echo "MANAGED_INFRA_CONFIG is missing ansible/inventory/hosts.yml" >&2
    exit 1
  fi

  local repo_inventory
  repo_inventory="$(cd "$(project_root)/ansible/inventory" && pwd)/hosts.yml"
  if [[ "$(cd "$(dirname "$inventory_src")" && pwd)/hosts.yml" == "$repo_inventory" ]]; then
    echo "MANAGED_INFRA_CONFIG/ansible/inventory points at this repo's inventory (templates)." >&2
    exit 1
  fi

  local docker_src="$MANAGED_INFRA_CONFIG/docker"
  if [[ ! -d "$docker_src" ]]; then
    echo "MANAGED_INFRA_CONFIG has no docker/ directory: $docker_src" >&2
    exit 1
  fi

  local repo_docker
  repo_docker="$(cd "$(project_root)/docker" && pwd)"
  if [[ "$(cd "$docker_src" && pwd)" == "$repo_docker" ]]; then
    echo "MANAGED_INFRA_CONFIG/docker points at this repo's docker/ (templates)." >&2
    exit 1
  fi

  local missing=()
  local file
  for file in "${EDGE_STACK_REQUIRED_FILES[@]}"; do
    if [[ ! -f "$docker_src/$file" ]]; then
      missing+=("$file")
    fi
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "MANAGED_INFRA_CONFIG/docker is missing required files: ${missing[*]}" >&2
    exit 1
  fi

  MANAGED_INFRA_INVENTORY_FILE="$inventory_src"
  MANAGED_INFRA_DOCKER="$docker_src"

  echo "Using inventory from: $(dirname "$inventory_src")" >&2
  echo "Using edge stack configs from: $docker_src" >&2
}

verify_managed_infra_backup() {
  load_project_env

  if [[ -z "${MANAGED_INFRA_BACKUP:-}" ]]; then
    echo "MANAGED_INFRA_BACKUP is not set. Add it to .env (see .env.example)." >&2
    exit 1
  fi

  local backup_root="$MANAGED_INFRA_BACKUP"
  if [[ "$backup_root" == "~"* ]]; then
    backup_root="${HOME}${backup_root:1}"
  fi

  local backup_parent
  backup_parent="$(dirname "$backup_root")"
  if [[ ! -d "$backup_parent" ]]; then
    echo "Parent directory for MANAGED_INFRA_BACKUP does not exist: $backup_parent" >&2
    exit 1
  fi

  mkdir -p "$backup_root"

  MANAGED_INFRA_BACKUP="$(cd "$backup_root" && pwd)"

  local repo_root
  repo_root="$(project_root)"
  case "$MANAGED_INFRA_BACKUP" in
    "$repo_root"|"$repo_root"/*)
      echo "MANAGED_INFRA_BACKUP must be outside this git repository: $repo_root" >&2
      exit 1
      ;;
  esac

  echo "Using backup root: $MANAGED_INFRA_BACKUP" >&2
}

# Parse --limit / -l from ansible-playbook args; prints exactly one inventory hostname.
require_ansible_single_host_limit() {
  local limit_hosts=()
  local arg
  local next_is_limit=false

  for arg in "$@"; do
    if [[ "$next_is_limit" == true ]]; then
      limit_hosts+=("$arg")
      next_is_limit=false
      continue
    fi

    case "$arg" in
      --limit)
        next_is_limit=true
        ;;
      --limit=*)
        local value="${arg#--limit=}"
        local part
        IFS=',' read -ra parts <<< "$value"
        for part in "${parts[@]}"; do
          limit_hosts+=("$part")
        done
        ;;
      -l)
        next_is_limit=true
        ;;
      -l*)
        local value="${arg#-l}"
        local part
        IFS=',' read -ra parts <<< "$value"
        for part in "${parts[@]}"; do
          limit_hosts+=("$part")
        done
        ;;
    esac
  done

  if [[ ${#limit_hosts[@]} -eq 0 ]]; then
    echo "Refusing to run: pass exactly one host with --limit <hostname>." >&2
    exit 1
  fi

  if [[ ${#limit_hosts[@]} -gt 1 ]]; then
    echo "Refusing to run: --limit must name exactly one host (got: ${limit_hosts[*]})." >&2
    exit 1
  fi

  if [[ "${limit_hosts[0]}" == *"*"* || "${limit_hosts[0]}" == *":"* ]]; then
    echo "Refusing to run: --limit must be a single inventory hostname, not a pattern." >&2
    exit 1
  fi

  printf '%s' "${limit_hosts[0]}"
}

# Resolve edge_stack_restore_source from -e extra vars; default to the limited host.
resolve_edge_stack_restore_source() {
  local limit_host="$1"
  shift
  local source_host="$limit_host"
  local arg
  local next_is_extra=false
  local token

  for arg in "$@"; do
    if [[ "$next_is_extra" == true ]]; then
      # Ansible accepts multiple key=value pairs in one -e string.
      for token in $arg; do
        if [[ "$token" == edge_stack_restore_source=* ]]; then
          source_host="${token#edge_stack_restore_source=}"
        fi
      done
      next_is_extra=false
      continue
    fi

    case "$arg" in
      -e)
        next_is_extra=true
        ;;
      -e*)
        local value="${arg#-e}"
        for token in $value; do
          if [[ "$token" == edge_stack_restore_source=* ]]; then
            source_host="${token#edge_stack_restore_source=}"
          fi
        done
        ;;
      edge_stack_restore_source=*)
        source_host="${arg#edge_stack_restore_source=}"
        ;;
    esac
  done

  printf '%s' "$source_host"
}

# Drop --limit / -l arguments so wrappers can enforce a single host limit.
filter_ansible_args_without_limit() {
  local filtered=()
  local arg
  local skip_next=false

  for arg in "$@"; do
    if [[ "$skip_next" == true ]]; then
      skip_next=false
      continue
    fi

    case "$arg" in
      --limit|-l)
        skip_next=true
        ;;
      --limit=*|-l*)
        ;;
      *)
        filtered+=("$arg")
        ;;
    esac
  done

  if [[ ${#filtered[@]} -gt 0 ]]; then
    printf '%s\0' "${filtered[@]}"
  fi
}

verify_backup_mirror_exists() {
  local source_host="$1"
  local mirror_root="$MANAGED_INFRA_BACKUP/$source_host"

  if [[ ! -f "$mirror_root/manifest.json" ]]; then
    echo "Backup mirror not found: $mirror_root/manifest.json" >&2
    echo "Run ./bin/infra-backup-edge-stack --limit $source_host first, or set -e edge_stack_restore_source=<host>." >&2
    exit 1
  fi

  echo "Using backup source: $mirror_root" >&2
}
