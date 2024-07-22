#!/bin/bash

# for bold font
BOLD="\e[1m"
RESET="\e[0m"
YELLOW="\033[1;33m"
RED="\033[91m"

#### make soft link for tools
# Find the Python directory under /usr/local/lib/
PYTHON_DIR=$(find /usr/local/lib/ -maxdepth 1 -type d -name "python*" -exec basename {} \; | sort -V | tail -n 1)
if [ -z "$PYTHON_DIR" ]; then
    echo -e "${RED}Error: Python directory not found under /usr/local/lib/${RESET}"
    exit 1
fi
echo -e "${BOLD}Python directory found: ${RESET}${YELLOW}/usr/local/lib/$PYTHON_DIR${RESET}"
# Find the "kara" directory starting from the current directory
KARA_DIR=$(dirname "$(pwd)")
while [ "$KARA_DIR" != "/" ]; do
    if [ -d "$KARA_DIR/kara" ]; then
        break
    fi
    KARA_DIR=$(dirname "$KARA_DIR")
done
if [ "$KARA_DIR" == "/" ]; then
    echo "Error: kara directory not found"
    exit 1
fi
echo -e "${BOLD}kara directory found at: ${RESET}${YELLOW}$KARA_DIR/kara${RESET}"
# Array of script names
SCRIPTS=("mrbench" "config_gen" "status_reporter" "monstaver" "analyzer" "report_recorder")
# Loop through each script and create a symbolic link in the destination directory
for ((i=0; i<${#SCRIPTS[@]}; i++)); do
    SCRIPT="${SCRIPTS[i]}"
    SCRIPT_DIR="${SCRIPTS[i]}"
    FULL_SCRIPT_PATH="$KARA_DIR/kara/$SCRIPT_DIR/$SCRIPT.py"
    if [ ! -f "$FULL_SCRIPT_PATH" ]; then
        echo -e "${RED}Error: Script $SCRIPT not found in directory $SCRIPT_DIR${RESET}"
        continue
    fi   
    ln_result=$(ln -s "$FULL_SCRIPT_PATH" "/usr/local/lib/$PYTHON_DIR/dist-packages/$SCRIPT.py" 2>&1)
    if [ $? -eq 0 ]; then
        echo -e "${BOLD}Created symbolic link for $SCRIPT${RESET}"
    elif [[ $ln_result == *"File exists"* ]]; then
        echo -e "${BOLD}Symbolic link for $SCRIPT already exists${RESET}"
    else
        echo -e "${RED}Failed to create symbolic link for $SCRIPT: $ln_result${RESET}"
    fi
done

#### copy config files to /etc/kara
# Source directory where your files are located
source_dir="./sample_configs"
# Destination directory where you want to move the files
destination_dir="/etc/kara"
mkdir -p "$destination_dir"
mv "$source_dir"/* "$destination_dir"/
# Check if files are successfully moved
if [ $? -eq 0 ]; then
    echo -e "${YELLOW}Config files moved successfully to $destination_dir${RESET}"
else
    echo -e "${RED}Failed to move config files${RESET}"
fi

#### unzip pywikibot
zip_file="$KARA_DIR/kara/report_recorder/report_recorder_bot.zip"
zip_destination="$KARA_DIR/kara/report_recorder/"
if unzip "$zip_file" -d "$zip_destination"  > /dev/null 2>&1; then
  if mv "$KARA_DIR/kara/report_recorder/report_recorder_bot"/* "$zip_destination" > /dev/null 2>&1; then
    echo -e "${YELLOW}Unzip and move report_recoder_bot to /resport_recorder dir successful${RESET}"
  else
    echo -e "${YELLOW}Unzip successful${RESET} ${RED}but move failed for report_recoder_bot${RESET}"
  fi
else
  echo -e "${RED}report_recoder_bot unzip failed${RESET}"
fi
 
#### copy user-config.py to manager dir
if [ ! -f "$KARA_DIR/kara/manager/user-config.py" ]; then
    sudo cp -r $KARA_DIR/kara/report_recorder/user-config.py $KARA_DIR/kara/manager/
elif [ -f "$KARA_DIR/kara/manager/user-config.py" ]; then
    user_conf_diff=$(diff $KARA_DIR/kara/manager/user-config.py $KARA_DIR/kara/report_recorder/user-config.py)
    if [ $? -eq 0 ] && [ ! -z "$user_conf_diff" ]; then
        sudo cp -r $KARA_DIR/kara/report_recorder/user-config.py $KARA_DIR/kara/manager/
    fi
else
    echo -e "${RED}user-config.py is required for run report_recorder${RESET}"
fi

#### install dependency
sudo apt update
sudo apt install -y xfsprogs
# Install Python libraries using pip
sudo apt install -y pip
pip install pytz datetime matplotlib pandas alive_progress BeautifulSoup4 wikitextparser
if [ $? -eq 0 ]; then
  echo -e "${YELLOW}All installations were successful${RESET}"
else
  echo -e "${RED}There was an error during the installations${RESET}"
fi

#### run shard script
python3 ./db_shard_config.py
