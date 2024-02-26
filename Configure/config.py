import os
import subprocess
import json

# this is for test
# Define Pathes
InfluxdbConfig_file_path = "./../conf/Software/InfluxdbConfig.json"

# Load data from InfluxdbConfig json file
with open (InfluxdbConfig_file_path, 'r') as file:
    file_data = json.load(file)

default_influxdb_container_name = file_data["Main_influxdb_container_name"]
default_db_name = file_data["Main_influxdb_DB_name"]
default_rp_name = file_data["Main_influxdb_database_rp_name"]
db_port = file_data["Main_influxdb_container_port"]
db_host = file_data["Main_influxdb_host_in_container"]

# Deifne some functions
# Clear the Page
clear_command = "clear"
os.system(clear_command)

# Define attention message function
def print_attention_message():
    print("\033[93m\033[1m" + " *-*-*-*-*-*-*-*-*-*-*-*-*-* ATTENTION *-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
    print(" DO NOT USE influxDB after running this script for at least 2 HOURS ")
    print(" *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
    print("\033[0m")

# Call the function to print the attention message
print_attention_message()

# Give some neccessary argumants from input
influxdb_container_name = input(f"Please enter your InfluxDB container name (Default : {default_influxdb_container_name}): ")
if influxdb_container_name == "":
    influxdb_container_name = default_influxdb_container_name
db_name = input (f"Please enter your database name (Default : {default_db_name}): ")
if db_name == "" :
    db_name = default_db_name
rp_name = input(f"Please enter your active retention policy name (Default : {default_rp_name}): ")
if rp_name == "" :
    rp_name = default_rp_name

# Clear the Page
os.system(clear_command)

# Call the function to print the attention message
print_attention_message()

# Install pip and it dependencies
# Install pip
pip_installer_command = "apt install python3-pip > /dev/null  2>&1"
pip_installer_process = subprocess.run(pip_installer_command, shell=True)
pip_installer_exit_code = pip_installer_process.returncode

# Upgrade pip
pip_updater_command = "pip3 install --upgrade pip > /dev/null  2>&1" 
pip_updater_process = pip_installer_process = subprocess.run(pip_updater_command, shell=True)
pip_updater_process_exit_code = pip_updater_process.returncode

# Install pytz
pytz_installer_command = "pip install pytz > /dev/null  2>&1"
pytz_installer_process = subprocess.run(pytz_installer_command, shell=True)
pytz_installer_process_exit_code = pytz_installer_process.returncode

# Intsall alive-progress
alive_progress_installer_command = "pip install alive-progress > /dev/null  2>&1"
alive_progress_installer_process = subprocess.run(alive_progress_installer_command, shell=True)
alive_progress_installer_process_exit_code = alive_progress_installer_process.returncode

# Check all exit codes and print output
if pip_installer_exit_code & pip_updater_process_exit_code & pytz_installer_process_exit_code & alive_progress_installer_process_exit_code == 0:
   print("\033[92mAll dependencies installed successfully\033[0m")
elif pip_installer_exit_code == 1:
    print("\033[91mfailed in installing pip\033[0m")
elif pip_updater_process_exit_code == 1:
    print("\033[91mpip updateing failed\033[0m")
elif pytz_installer_process_exit_code == 1:
    print("\033[91mpytz installing failed\033[0m")
elif alive_progress_installer_process_exit_code == 1:
    print("\033[91malive-progress installing failed\033[0m")

# Change rp part
policy_changer_command = f"docker exec -it {influxdb_container_name} influx -execute 'alter retention policy {default_rp_name} on {default_db_name} shard duration 1h default'"
policy_changer_process = subprocess.run(policy_changer_command, shell=True)
policy_changer_exit_code = policy_changer_process.returncode
if policy_changer_exit_code == 0:
    print(f"\033[92mSHard group duration in {default_rp_name} changed to 1h successfully\033[0m")
else :
    print("\033[91mChaing RP failed\033[0m")

# Start controllers
start_command = "cd ../../ && bash start-controller.sh > /dev/null && bash start-driver.sh > /dev/null"
start_process = subprocess.run(start_command,shell=True)
start_exit_code = start_process.returncode
if start_exit_code == 0:
    print(f"\033[92mDrivers started successfully\033[0m")
else:
    print("\033[91mStarting drivers failed\033[0m")
