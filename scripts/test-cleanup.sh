# ---- Execution Validation ----

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    . "${0%/*}/bootstrap.sh"

    print_error_message "This script must not be run directly. Cleanup the test directory with ${magenta}test.sh --cleanup${reset}."
    exit 1
fi


# ---- Header Display ----

printf '%b\n\n' "${yellow}${project_name}${reset} test cleanup"


# ---- Test Cleanup ----

rm -rf "${test_dir}/mail"
find "$data_dir" ! -path "$data_dir" ! -path "${data_dir}/.gitignore" -exec rm -rf {} +


# ---- Success Confirmation ----

print_success_message "${yellow}${project_name}${reset} test cleanup completed."
