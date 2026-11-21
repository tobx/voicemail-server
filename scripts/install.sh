#!/usr/bin/env bash

set -euo pipefail


# ---- Configuration ----

. "${0%/*}/bootstrap.sh"

binary_file="/usr/local/bin/${project_name}"
config_file="/usr/local/etc/${project_name}.toml"
data_dir="/var/local/lib/${project_name}"
install_dir="/usr/local/lib/${project_name}"
system_user="voicemail"
systemd_dir="/usr/local/lib/systemd/system"

export UV_CACHE_DIR=/var/local/cache/uv
export UV_PYTHON_INSTALL_DIR=/usr/local/lib/uv/python

usage="[OPTIONS]

Options:
      --info       Display installation information
      --parallel   Enable parallel compilation
      --uninstall  Uninstall ${project_name}
  -h, --help       Print help"

umask 022


# ---- Argument Parser ----

while [ "$#" -gt 0 ]; do
    case "$1" in
        --info)
            info="true"
            shift
            ;;
        --parallel)
            parallel="true"
            shift
            ;;
        --uninstall)
            uninstall="true"
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        --*) raise_usage_error ;;
        *) break ;;
    esac
done

if [ "${info-}" = "true" ]; then
    . "${scripts_dir}/info.sh"
    exit 0
fi

if [ "${uninstall-}" = "true" ]; then
    . "${scripts_dir}/uninstall.sh"
    exit 0
fi


# ---- Header Display ----

printf '%b\n\n' "${yellow}${project_name}${reset} installation"


# ---- Environment Validation ----

print_section "Environment Validation"

description="Verifying that this script is running on a Debian-like operating system"
error_message="This script must be run on a Debian-like operating system."
execute_with_status "$description" "$error_message" os_is_debian_like

description="Verifying that this script is running as ${yellow}root${reset}"
error_message="This script must be run as ${yellow}root${reset}."
execute_with_status "$description" "$error_message" [ "$EUID" -eq 0 ]

description="Verifying that system user ${yellow}${system_user}${reset} exists"
error_message=""
if ! execute_with_status "$description" "$error_message" id "$system_user" 2>/dev/null; then
    if ! confirm "Create user ${yellow}${system_user}${reset} now?"; then
        print_lf
        print_error_message "Cannot continue installation without system user ${yellow}${system_user}${reset}."
        exit 1
    fi

    description="Creating system user ${yellow}${system_user}${reset}"
    error_message="Creating system user ${system_user} failed."
    execute_with_status "$description" "$error_message" adduser --system --group "$system_user"
fi

description="Verifying that system group ${yellow}${system_user}${reset} exists"
error_message="System group ${yellow}${system_user}${reset} does not exist."
execute_with_status "$description" "$error_message" getent group "$system_user"

description="Verifying that system user ${yellow}${system_user}${reset} is a member of group ${yellow}${system_user}${reset}"
error_message="System user ${yellow}${system_user}${reset} is not a member of group ${yellow}${system_user}${reset}."
execute_with_status "$description" "$error_message" user_is_member_of_group "$system_user" "$system_user"

description="Verifying that ${yellow}uv${reset} is installed"
error_message="This script requires ${yellow}uv${reset} to be installed. See: ${blue}https://docs.astral.sh/uv/${reset}"
execute_with_status "$description" "$error_message" command -v "uv"


# ---- File Synchronization ----

print_lf
print_section "File Synchronization"

files_to_sync=(
    ".pjsip-version"
    ".python-version"
    "LICENSE"
    "README.md"
    "scripts"
    "src"
)

description="Synchronizing files to ${yellow}${install_dir}${reset}"
error_message="File synchronization failed."
synchronize_files() {
    cd "$project_dir"
    rsync \
        --recursive \
        --delete \
        --exclude "*.DS_Store" \
        "${files_to_sync[@]}" \
        "${install_dir}"
    cp "${project_dir}/pyproject.template.toml" "${install_dir}/pyproject.toml"
}
execute_with_status "$description" "$error_message" synchronize_files


# ---- Setup ----

flags=("--embed" "install-python" "--skip-uv-check")
if [ "${parallel-}" = "true" ]; then
    flags+=("--parallel")
fi
print_lf
"${install_dir}/$(basename -- "$scripts_dir")/setup.sh" "${flags[@]}"


# ---- System Configuration ----

print_lf
print_section "System Configuration"

description="Copying config file if it does not already exist"
error_message="Copying config file failed."
copy_config_file() {
    if [ ! -e "$config_file" ]; then
        install -g "${system_user}" -m 640 "${project_dir}/config.template.toml" "$config_file"
    fi
}
execute_with_status "$description" "$error_message" copy_config_file

description="Creating data directory"
error_message="Data directory creation failed."
create_data_dir() {
    if [ ! -e "$data_dir" ]; then
        install -d -g "${system_user}" -m 770 "$data_dir"
    fi
}
execute_with_status "$description" "$error_message" create_data_dir

description="Creating symlink to binary file ${yellow}${binary_file}${reset}"
error_message="Symlink creation failed."
create_binary_file_symlink() {
    if [ ! -L "$binary_file" ]; then
        ln -s "${install_dir}/.venv/bin/${project_name}" "$binary_file"
    fi
}
execute_with_status "$description" "$error_message" create_binary_file_symlink

description="Installing systemd service"
error_message="Systemd service installation failed."
install_systemd_service() {
    if ! cmp --silent "${project_dir}/systemd/${project_name}.service" "${systemd_dir}/${project_name}.service"; then
        mkdir -p "$systemd_dir"
        cp "${project_dir}/systemd/${project_name}.service" "${systemd_dir}/"
        systemctl daemon-reload
        systemd_service_has_changed="true"
    fi
}
execute_with_status "$description" "$error_message" install_systemd_service


# ---- Installation Cleanup ----

print_lf
print_section "Installation Cleanup"

description="Deleting scripts directory"
error_message="Scripts directory deletion failed."
execute_with_status "$description" "$error_message" rm -r "${install_dir}/scripts"


# ---- Success Confirmation ----

print_lf
print_info_message "Configure ${yellow}${project_name}${reset} in config file ${yellow}${config_file}${reset}."
if ! systemctl is-enabled "$project_name" >/dev/null; then
    print_lf
    print_warning_message "Systemd service ${yellow}${project_name}.service${reset} is not enabled. Configure ${yellow}${project_name}${reset} first, then enable the service with: ${magenta}systemctl enable --now ${project_name}.service${reset}"
elif [ "${systemd_service_has_changed-}" = "true" ]; then
    print_lf
    print_warning_message "Systemd service ${yellow}${project_name}.service${reset} has changed. Restart it with: ${magenta}systemctl restart ${project_name}.service${reset}"
fi
print_lf
print_success_message "${yellow}${project_name}${reset} installation completed."
