# ---- Execution Validation ----

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    . "${0%/*}/bootstrap.sh"

    print_error_message "This script must not be run directly. Get information with ${magenta}install.sh --info${reset}."
    exit 1
fi


# ---- Header Display ----

printf '%s\n' "${yellow}${project_name}${reset} installation information"


# ---- Information Display ----

format() {
    printf "%-${name_column_width}s%s\n" "${1}:" "$2"
}

printf '\n%s\n' "${cyan}Installation Paths${reset}"
name_column_width=14
format "Binary file" "$binary_file"
format "Config file" "$config_file"
format "Data dir" "$data_dir"
format "Install dir" "$install_dir"

printf '\n%s\n' "${cyan}Tooling Paths${reset}"
name_column_width=18
format "systemd service" "$systemd_dir/${project_name}.service"
format "uv cache dir" "$UV_CACHE_DIR"
format "uv python dir" "$UV_PYTHON_INSTALL_DIR"

printf '\n%s\n' "${cyan}System User & Group${reset}"
name_column_width=15
format "System user" "$system_user"
