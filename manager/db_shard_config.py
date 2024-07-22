import subprocess
import yaml
import sys

# Define Pathes
config_file = "/etc/kara/monstaver.conf"
def load_config(config_file):
    with open(config_file, "r") as stream:
        try:
            data_loaded = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"Error loading the configuration: {exc}")
            sys.exit(1)
    return data_loaded

def print_attention_message():
    print("")
    print("\033[93m\033[1m" + " *-*-*-*-*-*-*-*-*-*-*-*-*-* ATTENTION *-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
    print(" DO NOT USE influxDB after running this script for at least 2 HOURS ")
    print(" *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
    print("\033[0m")

print_attention_message()
data_loaded = load_config(config_file)
default_rp_name = "autogen"
database_names = [db_name for config in data_loaded.get('db_sources', {}).values() if isinstance(config, dict) and 'databases' in config for db_name in config['databases']]
for mc_server, config in data_loaded.get('db_sources', {}).items(): 
    ip_influxdb = config.get('ip')
    ssh_port = config.get('ssh_port')
    ssh_user = config.get('ssh_user')
    container_name = config.get('container_name')
    for db_name in database_names:
        # Change rp part         
        policy_changer_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} \"sudo docker exec -i -u root {container_name} influx -execute 'alter retention policy {default_rp_name} on {db_name} shard duration 1h default'\""
        policy_changer_process = subprocess.run(policy_changer_command, shell=True)
        if policy_changer_process.returncode == 0:
            print(f"\033[92mShard group duration in {db_name} changed to 1h successfully\033[0m")
        else :
            print(f"\033[91mChaing shard of {db_name} failed, please check /etc/kara/monstaver.conf for database config\033[0m")
