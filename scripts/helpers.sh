debian_packages_are_installed() {
    for pkg in "$@"; do
        dpkg -s "$pkg" >/dev/null 2>&1 || return 1
    done
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

confirm() {
    printf '%b' "${magenta}?${reset} ${1} [${green}y${reset}/${green}N${reset}] "
    read -r answer
    case "$answer" in
        [Yy]|[Yy][Ee][Ss]) return 0 ;;
        *) return 1 ;;
    esac
}

# @param $1 Description of the command
# @param $2 Command name
# @param $3... Arguments for the command
# @return Exit status of the executed command
execute_with_status() {
    local description=$1
    local error_message=$2
    shift 2
    local command_and_args=("$@")

    print_task "${description}"

    local stderr
    if stderr=$("${command_and_args[@]}" 2>&1 >/dev/null); then
        print_task_success_tag
    else
        local return_code=$?
        print_task_failure_tag
        if [ -n "$stderr" ]; then
            printf '\n%s\n' "$stderr" >&2
        fi
        if [ -n "$error_message" ]; then
            print_lf >&2
            print_error_message "$error_message" >&2
        fi
        return "$return_code"
    fi
}

get_uv_package_version() {
    uv tree --quiet --package "$1" | sed -En 's/^[^ ]+ v//p'
}

# Parentheses `()` rather than braces `{}` run this function in a subshell to prevent namespace pollution.
os_is_debian_like() (
    . "/etc/os-release" 2>/dev/null || return 1

    [ "${ID-}" = "debian" ] || [ "${ID_LIKE#*debian*}" != "${ID_LIKE}" ]
)

os_is_macos() {
    command_exists "sw_vers"
}

print_lf() {
    printf '\n'
}

print_error_message() {
    printf '%b\n' "${red}ERROR${reset}: $1" >&2
}

print_info_message() {
    printf '%b\n' "${blue}INFO${reset}: $1"
}

print_section() {
    printf '%b\n' "${cyan}${1}${reset}"
}

print_success_message() {
    printf '%b\n' "${green}SUCCESS${reset}: $1"
}

print_task() {
    printf '%b' "${cyan}→${reset} ${1}${cyan}...${reset} "
}

print_task_comment() {
    printf '%b\n' "  (${1})"
}

print_task_failure_tag() {
    printf '%b\n' "[${red}✗${reset}]"
}

print_task_success_tag() {
    printf '%b\n' "[${green}✓${reset}]"
}

print_usage() {
    printf '%b\n' "Usage: ${0##*/} ${usage}"
}

print_warning_message() {
    printf '%b\n' "${yellow}WARNING${reset}: $1"
}

systemd_service_is_installed() {
    systemctl --no-legend --no-pager list-unit-files "${1}.service" >/dev/null
}

raise_usage_error() {
    print_usage >&2
    return 1
}

uninstall_systemd_service() {
    systemctl disable --now "$1"
    rm -f "${project_dir}/${1}.service"
    systemctl daemon-reload
}

user_exists() {
    id "$1" >/dev/null 2>&1
}

user_is_member_of_group() {
    id -nG "$1" | grep -qw "$2"
}

verify_uv_availability() {
    if ! command_exists "uv"; then
        print_error_message "This script requires ${yellow}uv${reset} (https://docs.astral.sh/uv/) to be installed."
        return 1
    fi
}
