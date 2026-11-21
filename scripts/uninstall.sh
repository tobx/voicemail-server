# ---- Execution Validation ----

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    . "${0%/*}/bootstrap.sh"

    print_error_message "This script must not be run directly. Uninstall the application with ${magenta}install.sh --uninstall${reset}."
    exit 1
fi

# ---- Configuration ----

errors=""

# ---- Header Display ----

printf '%b\n\n' "${yellow}${project_name}${reset} uninstallation"


# ---- System Configuration ----

print_section "System Configuration"

description="Uninstalling systemd service"
error_message="Systemd service uninstallation failed."

print_task "Uninstalling systemd service"
if systemd_service_is_installed "$project_name"; then
    if uninstall_systemd_service "$project_name"; then
        print_task_success_tag
    else
        print_task_failure_tag
        print_lf
        print_error_message "Systemd service uninstallation failed."
        errors="true"
    fi
else
    print_task_success_tag
    print_task_comment "${yellow}${project_name}.service${reset} is not installed"
fi

description="Deleting system user ${yellow}${system_user}${reset}"
error_message="System user deletion failed."
delete_system_user() {
    if user_exists "$system_user"; then
        deluser --system "$system_user"
    fi
}
if ! execute_with_status "$description" "$error_message" delete_system_user; then
    errors="true"
fi


description="Deleting symlink to binary file ${yellow}${binary_file}${reset}"
error_message="Symlink deletion failed."
if ! execute_with_status "$description" "$error_message" rm -f "$binary_file"; then
    errors="true"
fi

description="Deleting config file"
error_message="Config file deletion failed."
if ! execute_with_status "$description" "$error_message" rm -f "$config_file"; then
    errors="true"
fi

# ---- Application Files ----

print_lf
print_section "Application Files"

description="Deleting application files"
error_message="Application files deletion failed."
if ! execute_with_status "$description" "$error_message" rm -rf "$install_dir"; then
    errors="true"
fi


# ---- Summary ----

print_lf
print_info_message "Data in the following directories was not deleted:
  Data directory:         ${yellow}${data_dir}${reset}
  uv cache dir:           ${yellow}${UV_CACHE_DIR}${reset}
  uv python install dir:  ${yellow}${UV_PYTHON_INSTALL_DIR}${reset}"
print_lf
print_info_message "Check ${yellow}https://docs.astral.sh/uv/${reset} for more information about ${yellow}uv${reset}."
print_lf
if [ "$errors" = "true" ]; then
    print_warning_message "${yellow}${project_name}${reset} uninstallation completed with errors."
    return 1
else
    print_success_message "${yellow}${project_name}${reset} uninstallation completed."
fi
