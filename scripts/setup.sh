#!/usr/bin/env bash

set -euo pipefail


# ---- Configuration ----

. "${0%/*}/bootstrap.sh"

pjsip_version=$(<"${project_dir}/.pjsip-version")
pjsip_version="${pjsip_version%$'\n'}"
vendor_lib_dir="${project_dir}/vendor/lib"
vendor_src_dir="${project_dir}/vendor/src"

usage="[OPTIONS]

Options:
      --embed          Disable header and footer output
      --parallel       Enable parallel compilation
      --skip-uv-check  Skip uv availability check
  -h, --help           Print help"

umask 022


# ---- Argument Parser ----

while [ "$#" -gt 0 ]; do
    case "$1" in
        --embed)
            embed="true"
            shift
            ;;
        --install-python)
            install_python="true"
            shift
            ;;
        --parallel)
            parallel="true"
            shift
            ;;
        --skip-uv-check)
            skip_uv_check="true"
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


# ---- Header Display ----

if [ "${embed-}" != "true" ]; then
    printf '%b\n\n' "${yellow}${project_name}${reset} setup"
fi


# ---- Environment Validation ----

print_section "Environment Validation"

print_task "Detecting operating system"
if os_is_debian_like; then
    os="debian"
    full_os_name="Debian-based Linux"
elif os_is_macos; then
    os="macos"
    full_os_name="macOS"
else
    print_task_failure_tag
    print_lf
    print_error_message "Cannot detect operating system."
    print_lf
    print_info_message "Supported operating systems: ${yellow}Debian-based Linux${reset}, ${yellow}macOS${reset}"
    exit 1
fi
print_task_success_tag
print_task_comment "${yellow}${full_os_name}${reset} detected"

if [ "${skip_uv_check-}" != "true" ]; then
    description="Verifying that ${yellow}uv${reset} is installed"
    error_message="This script requires ${yellow}uv${reset} to be installed. See: ${blue}https://docs.astral.sh/uv/${reset}"
    execute_with_status "$description" "$error_message" command -v "uv"
fi

description="Ensuring that ${yellow}pyproject.toml${reset} exists"
error_message="${yellow}pyproject.toml${reset} could not be created."
ensure_pyproject_toml_exists() {
    if [ ! -e "${project_dir}/pyproject.toml" ]; then
        cp "${project_dir}/pyproject.template.toml" "${project_dir}/pyproject.toml"
    fi
}
execute_with_status "$description" "$error_message" ensure_pyproject_toml_exists


# ---- Dependency Installation ----

print_lf
print_section "Dependency Installation"

description="Setup uv environment"
error_message="uv environment setup failed."
setup_uv_environment() {
    if [ -n "${UV_CACHE_DIR-}" ]; then
        mkdir -p "$UV_CACHE_DIR"
    fi
    if [ -n "${UV_PYTHON_INSTALL_DIR-}" ]; then
        mkdir -p "$UV_PYTHON_INSTALL_DIR"
    fi
    if [ "${install_python-}" = "true" ]; then
        uv python install
    fi
}
execute_with_status "$description" "$error_message" setup_uv_environment

print_task "Verify installed PJSIP version"
installed_pjsip_version="$(cat "${vendor_lib_dir}/pjsip/.version" 2>/dev/null)" || true
if [ "$pjsip_version" = "$installed_pjsip_version" ]; then
    print_task_success_tag
else
    print_task_failure_tag
    print_task_comment "required: ${green}${pjsip_version}${reset}, installed: ${red}${installed_pjsip_version:-none}${reset}"


    # ---- System Dependency Installation ----

    description="Installing system dependencies"
    error_message="System dependency installation failed."
    install_system_dependencies() {
        if [ "$os" = "debian" ]; then
            packages=(build-essential libssl-dev pkg-config python3-dev swig uuid-dev)
            if ! debian_packages_are_installed "${packages[@]}"; then
                su - -c '
                    apt update
                    apt install "${packages[@]}"
                '
            fi
        else
            xcode-select -p >/dev/null 2>&1 || xcode-select --install
            for formula in "git" "swig" "pkg-config"; do
                brew list "${formula}" >/dev/null 2>&1 || brew install "${formula}"
            done
        fi
    }
    execute_with_status "$description" "$error_message" install_system_dependencies


    # ---- Vendor Directory Creation  ----

    description="Creating vendor directories"
    error_message="Vendor directory creation failed."
    execute_with_status "$description" "$error_message" mkdir -p \
        "${vendor_lib_dir}" "${vendor_src_dir}"


    # ---- PJSIP Building  ----

    description="Updating PJSIP repository to version ${pjsip_version}"
    error_message="PJSIP repository update failed."
    update_pjsip() {
        cd "${vendor_src_dir}"
        if [ ! -d "pjproject/.git" ]; then
            git clone https://github.com/pjsip/pjproject.git
        fi
        cd "pjproject"
        git fetch --tags
        git checkout "refs/tags/${pjsip_version}"
    }
    execute_with_status "$description" "$error_message" update_pjsip

    description="Configuring PJSIP"
    error_message="PJSIP configuration failed."
    configure_pjsip() {
        cd "${vendor_src_dir}/pjproject"
        ./configure --prefix="${vendor_lib_dir}/pjsip" CFLAGS="-fPIC"
    }
    execute_with_status "$description" "$error_message" configure_pjsip

    description="Generating PJSIP dependency information"
    error_message="PJSIP dependency information generation failed."
    generate_pjsip_dependency_information() {
        cd "${vendor_src_dir}/pjproject"
        make dep
    }
    execute_with_status "$description" "$error_message" generate_pjsip_dependency_information

    description="Building PJSIP"
    error_message="Building PJSIP failed."
    build_pjsip() {
        cd "${vendor_src_dir}/pjproject"
        if [ "${parallel-}" = "true" ]; then
            if [ "$os" = "debian" ]; then
                make -j"$(nproc)"
            else
                make -j"$(sysctl -n hw.ncpu)"
            fi
        else
            make
        fi
    }
    execute_with_status "$description" "$error_message" build_pjsip

    description="Installing PJSIP"
    error_message="PJSIP installation failed."
    install_pjsip() {
        cd "${vendor_src_dir}/pjproject"
        make install
    }
    execute_with_status "$description" "$error_message" install_pjsip

    description="Pin PJSIP version ${pjsip_version}"
    error_message="Pinning PJSIP version failed."
    pin_pjsip_version() {
        printf '%s' "${pjsip_version}" > "${vendor_lib_dir}/pjsip/.version"
    }
    execute_with_status "$description" "$error_message" pin_pjsip_version

fi

print_task "Verify installed PJSUA2 version"
if ls "${project_dir}/wheels"/pjsua2-*.whl >/dev/null 2>&1; then
    installed_pjsua2_version="$(cat "${vendor_src_dir}/pjproject/pjsip-apps/src/swig/python/.version" 2>/dev/null)" || true
fi
if [ "$pjsip_version" = "${installed_pjsua2_version-}" ]; then
    print_task_success_tag
else
    print_task_failure_tag
    print_task_comment "required: ${green}${pjsip_version}${reset}, installed: ${red}${installed_pjsua2_version:-none}${reset}"


    # ---- PJSUA2 Building  ----

    description="Building PJSUA2"
    error_message="Building PJSUA2 failed."
    build_pjsua2() {
        cd "${vendor_src_dir}/pjproject/pjsip-apps/src/swig/python"
        uv run --no-sync --with pip,setuptools make
    }
    execute_with_status "$description" "$error_message" build_pjsua2

    description="Building PJSUA2 Python wheel"
    error_message="Building PJSUA2 Python wheel failed."
    build_pjsua2_python_wheel() {
        cd "${vendor_src_dir}/pjproject/pjsip-apps/src/swig/python"
        uv build --clear --wheel --out-dir "${project_dir}/wheels/"
    }
    execute_with_status "$description" "$error_message" build_pjsua2_python_wheel

    description="Pin PJSUA2 version ${pjsip_version}"
    error_message="Pinning PJSUA2 version failed."
    pin_pjsua2_version() {
        cd "${vendor_src_dir}/pjproject/pjsip-apps/src/swig/python"
        printf '%s' "${pjsip_version}" > ".version"
    }
    execute_with_status "$description" "$error_message" pin_pjsua2_version

fi


# ---- Project synchronization  ----

description="Synchronize project"
error_message="Project synchronization failed."
synchronize_project() {
    cd "$project_dir"
    uv add "wheels"/*.whl
}
execute_with_status "$description" "$error_message" synchronize_project


# ---- Success Confirmation ----

if [ "${embed-}" != "true" ]; then
    print_lf
    print_success_message "${yellow}${project_name}${reset} setup completed."
fi
