#!/bin/bash

# for bold font
BOLD="\e[1m"
RESET="\e[0m"
YELLOW="\033[1;33m"

#### make soft link for tools
# Find the Python directory under /usr/local/lib/
PYTHON_DIR=$(find /usr/local/lib/ -maxdepth 1 -type d -name "python*" -exec basename {} \; | sort -V | tail -n 1)
if [ -z "$PYTHON_DIR" ]; then
    echo "Error: Python directory not found under /usr/local/lib/"
    exit 1
fi
echo -e "${BOLD}Python directory found: ${RESET}${YELLOW}$PYTHON_DIR${RESET}"
# Find the "KARA" directory starting from the current directory
KARA_DIR=$(dirname "$(pwd)")
while [ "$KARA_DIR" != "/" ]; do
    if [ -d "$KARA_DIR/KARA" ]; then
        break
    fi
    KARA_DIR=$(dirname "$KARA_DIR")
done
if [ "$KARA_DIR" == "/" ]; then
    echo "Error: KARA directory not found"
    exit 1
fi
echo -e "${BOLD}KARA directory found at: ${RESET}${YELLOW}$KARA_DIR/KARA${RESET}"
# Array of script names
SCRIPTS=("mrbench" "config_gen" "status_reporter" "monstaver" "analyzer" "report_recorder")
# Loop through each script and create a symbolic link in the destination directory
for ((i=0; i<${#SCRIPTS[@]}; i++)); do
    SCRIPT="${SCRIPTS[i]}"
    SCRIPT_DIR="${SCRIPTS[i]}"
    FULL_SCRIPT_PATH="$KARA_DIR/KARA/$SCRIPT_DIR/$SCRIPT.py"
    if [ ! -f "$FULL_SCRIPT_PATH" ]; then
        echo "Error: Script $SCRIPT not found in directory $SCRIPT_DIR"
        continue
    fi   
    ln_result=$(ln -s "$FULL_SCRIPT_PATH" "/usr/local/lib/$PYTHON_DIR/dist-packages/$SCRIPT.py" 2>&1)
    if [ $? -eq 0 ]; then
        echo -e "${BOLD}Created symbolic link for $SCRIPT${RESET}"
    elif [[ $ln_result == *"File exists"* ]]; then
        echo -e "${BOLD}Symbolic link for $SCRIPT already exists${RESET}"
    else
        echo -e "${BOLD}Failed to create symbolic link for $SCRIPT: $ln_result${RESET}"
    fi
done

#### copy config files to /etc/KARA
# Source directory where your files are located
source_dir="./sample_configs"
# Destination directory where you want to move the files
destination_dir="/etc/KARA"
mkdir -p "$destination_dir"
mv "$source_dir"/* "$destination_dir"/
# Check if files are successfully moved
if [ $? -eq 0 ]; then
    echo -e "${YELLOW}Config files moved successfully to $destination_dir${RESET}"
else
    echo -e "${BOLD}Failed to move config files${RESET}"
fi

#### unzip pywikibot
zip_file="$KARA_DIR/KARA/report_recorder/report_recorder_bot.zip"
zip_destination="$KARA_DIR/KARA/report_recorder"
unzip "$zip_file" -d "$zip_destination"

#### copy user-config.py to manager dir
if [ ! -f "$KARA_DIR/KARA/manager/user-config.py" ]; then
    sudo cp -r $KARA_DIR/KARA/report_recorder/user-config.py $KARA_DIR/KARA/manager/
elif [ -f "$KARA_DIR/KARA/manager/user-config.py" ]; then
    user_conf_diff=$(diff $KARA_DIR/KARA/manager/user-config.py $KARA_DIR/KARA/report_recorder/user-config.py)
    if [ $? -eq 0 ] && [ ! -z "$user_conf_diff" ]; then
        sudo cp -r $KARA_DIR/KARA/report_recorder/user-config.py $KARA_DIR/KARA/manager/
    fi
else
    echo -e "\033[91muser-config.py is required for run report_recorder\033[0m"
fi
