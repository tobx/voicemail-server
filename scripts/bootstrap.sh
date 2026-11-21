# Set terminal output colors
black=$(tput setaf 0)
red=$(tput setaf 1)
green=$(tput setaf 2)
yellow=$(tput setaf 3)
blue=$(tput setaf 4)
magenta=$(tput setaf 5)
cyan=$(tput setaf 6)
white=$(tput setaf 7)
reset=$(tput sgr0)

# Set essential project variables
scripts_dir=$(CDPATH= cd -- "${0%/*}" && pwd -P)
project_dir=$(dirname -- "$scripts_dir")
project_name=$(basename -- "$project_dir")

# Default usage message (can be overridden by sourcing scripts)
usage=""

# Source helper functions
. "${scripts_dir}/helpers.sh"
