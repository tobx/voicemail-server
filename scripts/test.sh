#!/usr/bin/env bash

set -euo pipefail


# ---- Configuration ----

. "${0%/*}/bootstrap.sh"

test_dir="test"
config_file="${test_dir}/config.toml"
data_dir="${test_dir}/data"

usage="[OPTIONS]

Options:
      --cleanup  Delete test call logs, voicemails and emails.
  -h, --help     Print help"


# ---- Initialization ----

cd "$project_dir"


# ---- Argument Parser ----

while [ "$#" -gt 0 ]; do
    case "$1" in
        --cleanup)
            cleanup="true"
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
        *) break ;;
    esac
done

if [ "${cleanup-}" = "true" ]; then
    . "${scripts_dir}/test-cleanup.sh"
    exit 0
fi


# ---- Environment Validation ----

if [ ! -e "$config_file" ]; then
    cp "config.template.toml" "$config_file"
    sed \
        -e 's|data_directory = .*|data_directory = "'"$data_dir"'"|' \
        -e 's|command = .*|command = ["test/mail.py"]|' \
        "$config_file" > "${config_file}.tmp"
    mv "${config_file}.tmp" "$config_file"
    print_info_message "Config file '${yellow}${config_file}${reset}' created. Adjust its settings and rerun this script."
    exit 0
fi


# ---- Execution ----

uv run -- voicemail-server --config "${config_file}" "$@"
