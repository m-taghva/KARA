import datetime
import time
import os
import subprocess
import argparse
import sys
import logging
import pytz
import yaml
import json
import requests
import concurrent.futures
from alive_progress import alive_bar

config_file = "/etc/kara/monstaver.conf"

def load_config(config_file):
    with open(config_file, "r") as stream:
        try:
            data_loaded = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"Error loading the configuration: {exc}")
            sys.exit(1)
    return data_loaded

def tehran_time_to_utc(tehran_time_str):
    logging.info("monstaver - Executing tehran_time_to_utc function")
    tehran_tz = pytz.timezone('Asia/Tehran')
    utc_tz = pytz.utc
    tehran_time = tehran_tz.localize(tehran_time_str)
    utc_time = tehran_time.astimezone(utc_tz)
    return utc_time

def convert_time(start_time_str, end_time_str, margin_start, margin_end):
    logging.info("monstaver - Executing convert_time function")
    start_datetime = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
    end_datetime = datetime.datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
    # Convert Tehran time to UTC
    start_datetime_utc = tehran_time_to_utc(start_datetime)
    end_datetime_utc = tehran_time_to_utc(end_datetime)
    # Add the margins to datetime objects
    start_datetime_utc -= datetime.timedelta(seconds=margin_start)
    end_datetime_utc += datetime.timedelta(seconds=margin_end)
    # Convert the UTC datetime objects back to strings
    start_datetime_utc_str = start_datetime_utc.strftime("%Y-%m-%d %H:%M:%S")
    end_datetime_utc_str = end_datetime_utc.strftime("%Y-%m-%d %H:%M:%S")
    # Creating backup time format
    backup_start_date, backup_start_time = start_datetime_utc_str.split(" ")
    start_time_backup = backup_start_date + "T" + backup_start_time + "Z"
    backup_end_date, backup_end_time = end_datetime_utc_str.split(" ")
    end_time_backup = backup_end_date + "T" + backup_end_time + "Z"
    # Directory name creation
    dir_start_date, dir_start_time = start_time_str.split(" ")
    dir_start_date = dir_start_date[2:].replace("-", "")
    dir_start_time = dir_start_time.replace(":", "")
    dir_end_date, dir_end_time = end_time_str.split(" ")
    dir_end_date = dir_end_date[2:].replace("-", "")
    dir_end_time = dir_end_time.replace(":", "")
    time_dir_name = dir_start_date + "T" + dir_start_time + "_" + dir_end_date + "T" + dir_end_time
    logging.info(f"monstaver - UTC time range: {start_time_backup},{end_time_backup}")
    logging.info(f"monstaver - dir name of backup files: {time_dir_name}")
    return start_time_backup,end_time_backup,time_dir_name

def backup_data_collector(ssh_port, ssh_user, ip_influxdb, container_name, influx_volume, time_dir_name, bar, backup_dir):
    # New_location_backup_in_host = value['temporary_location_backup_host']
    tmp_backup = "/tmp/influxdb-backup-tmp"
    mkdir_process = subprocess.run(f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo mkdir -p {tmp_backup} && sudo chmod -R 777 {tmp_backup}'", shell=True)
    if mkdir_process.returncode == 0:
        logging.info(f"monstaver - create {tmp_backup} successful")
        time.sleep(1)
    else:
        logging.critical(f"monstaver - create {tmp_backup} and permission setting failed")
        print(f"\033[91mDirectory {tmp_backup} creation and permission setting failed.\033[0m")

    # copy backup to temporary dir 
    cp_process = subprocess.run(f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker cp {container_name}:{influx_volume}/{time_dir_name}/{container_name} {tmp_backup}'", shell=True)
    if cp_process.returncode == 0:
        logging.info(f"monstaver - copy backup to {tmp_backup} successful")
        bar()
    else:
        logging.critical(f"monstaver - copy backup to {tmp_backup} failed")
        print(f"\033[91mcopy backup to {tmp_backup} failed\033[0m")

    # tar all backup
    tar_process = subprocess.run(f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo tar -cf {tmp_backup}/{container_name}.tar.gz -C {tmp_backup}/{container_name}/ .'", shell=True)
    if tar_process.returncode == 0:
        logging.info(f"monstaver - create {tmp_backup}/{container_name}.tar.gz successful")
        bar()
    else:
        logging.critical(f"monstaver - create {tmp_backup}/{container_name}.tar.gz failed")
        print(f"\033[91mcreate {tmp_backup}/{container_name}.tar.gz  failed.\033[0m")

    # move tar file to dbs dir inside your server
    mv_process = subprocess.run(f"scp -r -P {ssh_port} {ssh_user}@{ip_influxdb}:{tmp_backup}/*.tar.gz {backup_dir}/{time_dir_name}/dbs/ > /dev/null 2>&1", shell=True)
    if mv_process.returncode == 0:
        logging.info(f"monstaver - all backup moved to your server: {backup_dir}/{time_dir_name}/dbs/")
        print("all backup moved to your server")
        bar()
    else:
        logging.critical(f"moving backup files to {backup_dir}/{time_dir_name}/dbs/ failed")
        print(f"\033[91mmoving backup files to {backup_dir}/{time_dir_name}/dbs/ failed.\033[0m")

    # remove temporary location of backup in host
    del_process = subprocess.run(f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo rm -rf {tmp_backup}'", shell=True)
    if del_process.returncode == 0:
        logging.info(f"monstaver - remove temporary location of backup in host: {tmp_backup}")
        bar()
    else:
        logging.error(f"monstaver - Remove temp dir failed: {tmp_backup}")
        print("\033[91mremove temp dir failed.\033[0m")

    # delete {time_dir} inside container
    del_time_process = subprocess.run(f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec {container_name} rm -rf {influx_volume}'", shell=True)
    if del_time_process.returncode == 0:
        logging.info(f"monstaver - Remove time dir inside container: {influx_volume}")
        bar()
    else:
        logging.error(f"monstaver - Remove time dir inside container failed: {influx_volume}")
        print("\033[91mremove time dir inside container failed.\033[0m")

def info_collector(port, user, ip, backup_dir, time_dir_name, container_name, bar, swift_info, hardware_info, software_info):
    # make hardware/os/swift sub directories
    mkdir_hwoss_output = f"ssh -p {port} {user}@{ip} sudo mkdir -p {backup_dir}-tmp/{time_dir_name}/configs/{container_name}/software/system/{container_name}-etc-container/ ; "
    mkdir_hwoss_output += f"sudo mkdir -p {backup_dir}/{time_dir_name}/configs/{container_name}/software/swift/services/ ; "
    mkdir_hwoss_output += f"sudo mkdir -p {backup_dir}/{time_dir_name}/configs/{container_name}/software/swift/server-confs/ ; "
    mkdir_hwoss_output += f"sudo mkdir -p {backup_dir}/{time_dir_name}/configs/{container_name}/software/swift/rings/ ; "
    mkdir_hwoss_output += f"sudo mkdir -p {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/cpu/ ; "
    mkdir_hwoss_output += f"sudo mkdir -p {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/memory/ ; "
    mkdir_hwoss_output += f"sudo mkdir -p {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/net/ ; "
    mkdir_hwoss_output += f"sudo mkdir -p {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/pci/ ; "
    mkdir_hwoss_output += f"sudo mkdir -p {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/disk/ ; "
    mkdir_hwoss_output += f"sudo mkdir -p {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/motherboard/ ; "
    mkdir_hwoss_output += f"sudo mkdir -p {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/server-manufacturer ; "
    mkdir_hwoss_output += f"sudo mkdir -p {backup_dir}/{time_dir_name}/configs/{container_name}/software/system/{container_name}-etc-host/ ; " 
    mkdir_hwoss_output += f"sudo mkdir -p {backup_dir}/{time_dir_name}/configs/{container_name}/software/system/{container_name}-etc-container/ "
    mkdir_hwoss_process = subprocess.run(mkdir_hwoss_output, shell=True)
    if mkdir_hwoss_process.returncode == 0:
        logging.info("monstaver - make hardware/software sub directories successful")
        bar()
    else:
        logging.critical("mkdir hardware/software sub directories failed")
        print("\033[91mmkdir hardware/software sub directories failed.\033[0m")
        sys.exit(1)

    # get swift config files and monster services
    if swift_info:
        logging.info(f"monstaver - user select switch -sw for swift info") 
        get_swift_conf = f"ssh -p {port} {user}@{ip} 'sudo docker exec {container_name} swift-init all status' > {backup_dir}/{time_dir_name}/configs/{container_name}/software/swift/services/{container_name}-swift-status.txt ; "
        get_swift_conf += f"ssh -p {port} {user}@{ip} 'sudo docker exec {container_name} service --status-all' > {backup_dir}/{time_dir_name}/configs/{container_name}/software/swift/services/{container_name}-services-container.txt 2>&1 ; "
        get_swift_conf += f"ssh -p {port} {user}@{ip} 'sudo docker exec {container_name} cat /etc/swift/container-server.conf' > {backup_dir}/{time_dir_name}/configs/{container_name}/software/swift/server-confs/{container_name}-container-server.conf ; "
        get_swift_conf += f"ssh -p {port} {user}@{ip} 'sudo docker exec {container_name} cat /etc/swift/account-server.conf' > {backup_dir}/{time_dir_name}/configs/{container_name}/software/swift/server-confs/{container_name}-account-server.conf ; "
        get_swift_conf += f"ssh -p {port} {user}@{ip} 'sudo docker exec {container_name} cat /etc/swift/proxy-server.conf' > {backup_dir}/{time_dir_name}/configs/{container_name}/software/swift/server-confs/{container_name}-proxy-server.conf ; "
        get_swift_conf += f"ssh -p {port} {user}@{ip} 'sudo docker exec {container_name} swift-ring-builder /etc/swift/account.builder' > {backup_dir}/{time_dir_name}/configs/{container_name}/software/swift/rings/{container_name}-account-ring.txt ; "
        get_swift_conf += f"ssh -p {port} {user}@{ip} 'sudo docker exec {container_name} swift-ring-builder /etc/swift/container.builder' > {backup_dir}/{time_dir_name}/configs/{container_name}/software/swift/rings/{container_name}-container-ring.txt ; "
        get_swift_conf += f"ssh -p {port} {user}@{ip} 'sudo docker exec {container_name} swift-ring-builder /etc/swift/object.builder' > {backup_dir}/{time_dir_name}/configs/{container_name}/software/swift/rings/{container_name}-object-ring.txt ; "
        get_swift_conf += f"ssh -p {port} {user}@{ip} 'sudo docker exec {container_name} cat /etc/swift/object-server.conf' > {backup_dir}/{time_dir_name}/configs/{container_name}/software/swift/server-confs/{container_name}-object-server.conf ; "
        get_swift_conf += f"ssh -p {port} {user}@{ip} 'sudo docker inspect {container_name}' > {backup_dir}/{time_dir_name}/configs/{container_name}/software/system/{container_name}-docker-inspect.txt ; "
        get_swift_conf += f"ssh -p {port} {user}@{ip} sudo docker container ls -a | awk '{{if(NR>1) print $2}}' > {backup_dir}/{time_dir_name}/configs/{container_name}/software/system/images-version.txt "
        get_swift_conf_process = subprocess.run(get_swift_conf, shell=True)
        if get_swift_conf_process.returncode == 0:
            logging.info("monstaver - all swift configs copy to swift dir")
            print("all swift configs copy to swift dir")
            time.sleep(1)
        else:
            logging.error("monstaver - get swift configs and monster services failed")
            print("\033[91mget swift configs and monster services failed.\033[0m")

    # extract docker compose file path and copy it
    docker_compose = f"ssh -p {port} {user}@{ip} 'sudo docker inspect {container_name}'"
    docker_compose_process = subprocess.run(docker_compose, shell=True, capture_output=True, text=True)
    if docker_compose_process.returncode == 0:
        inspect_result = json.loads(docker_compose_process.stdout)
        docker_compose_file = inspect_result[0]['Config']['Labels'].get('com.docker.compose.project.config_files')
        docker_compose_path = inspect_result[0]['Config']['Labels'].get('com.docker.compose.project.working_dir')
        docker_compose_result = os.path.join(docker_compose_path,docker_compose_file)
    copy_compose_file_process = subprocess.run(f"scp -r -P {port} {user}@{ip}:{docker_compose_result} {backup_dir}/{time_dir_name}/configs/{container_name}/software/system/ > /dev/null 2>&1", shell=True)
    if copy_compose_file_process.returncode == 0:
        logging.info("monstaver - extract docker compose file path and copy to os dir successful")
        bar()
    else: 
        logging.error("monstaver - failure in copy compose file to os dir")
        print("\033[91mfailure in copy compose file\033[0m")

    # copy etc dir from container to host
    get_etc_process = subprocess.run(f"ssh -p {port} {user}@{ip} 'sudo docker cp {container_name}:/etc  {backup_dir}-tmp/{time_dir_name}/configs/{container_name}/software/system/{container_name}-etc-container/'", shell=True)
    if get_etc_process.returncode == 0:
        logging.info(f"monstaver - copy monster etc of {container_name} to hos successful")
        bar()
    else: 
        logging.error(f"monstaver - failure in copy monster etc of {container_name} to host")
        print(f"\033[91mfailure in copy monster etc of {container_name} to host\033[0m")

    # copy container etc dir from host to your server
    mv_etc_cont_process = subprocess.run(f"scp -r -P {port} {user}@{ip}:{backup_dir}-tmp/{time_dir_name}/configs/{container_name}/software/system/{container_name}-etc-container/etc/*  {backup_dir}/{time_dir_name}/configs/{container_name}/software/system/{container_name}-etc-container/ > /dev/null 2>&1", shell=True)
    if mv_etc_cont_process.stderr is None:
        logging.info(f"monstaver - copy container etc dir from host {container_name} to your server successful")
        bar()
    else: 
        logging.error(f"monstaver - failure in copy container etc dir from host {container_name} to your server")
        print(f"\033[91mfailure in copy container etc dir from host {container_name} to your server\033[0m")
    
    # copy host etc dir from host to your server
    mv_etc_host_process = subprocess.run(f"scp -r -P {port} {user}@{ip}:/etc/*  {backup_dir}/{time_dir_name}/configs/{container_name}/software/system/{container_name}-etc-host/ > /dev/null 2>&1", shell=True)
    if mv_etc_host_process.stderr is None:
        logging.info(f"monstaver - copy host etc from host {container_name} to your server successful")
        bar()
    else: 
        logging.error(f"monstaver - failure in copy host etc from host {container_name} to your server")
        print(f"\033[91mfailure in copy host etc dir from host {container_name} to your server\033[0m")

    #### Execute commands to gather hardware information ####
    if hardware_info:
        logging.info(f"monstaver - user select switch -hw for hardware info") 
        lshw_command = f"ssh -p {port} {user}@{ip} sudo lshw -C cpu > {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/cpu/lshw.txt ; "
        lshw_command += f"ssh -p {port} {user}@{ip} sudo lshw -C memory > {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/memory/lshw.txt ; "
        lshw_command += f"ssh -p {port} {user}@{ip} sudo lshw -C memory -short > {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/memory/lshw-brief.txt ; "
        lshw_command += f"ssh -p {port} {user}@{ip} sudo lshw -C net > {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/net/lshw.txt ; "
        lshw_command += f"ssh -p {port} {user}@{ip} sudo lshw -C net -json > {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/net/lshw-json.txt ; "
        lshw_command += f"ssh -p {port} {user}@{ip} sudo lshw -short -C disk > {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/disk/lshw-brief.txt ; "
        lshw_command += f"ssh -p {port} {user}@{ip} sudo lshw -C disk > {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/disk/lshw.txt "
        lshw_process = subprocess.run(lshw_command, shell=True, capture_output=True, text=True)
        if lshw_process.returncode == 0:
            logging.info(f"monstaver - lshw successful on {container_name} host")
            time.sleep(1)
        elif "command not found" in lshw_process.stderr:
            logging.info(f"monstaver - lshw is not installed. Please install it on {container_name} host")
            print("\033[91mlshw is not installed. Please install it.\033[0m")
        else:
            logging.error(f"monstaver - lshw failed on {container_name} host")
            print(f"\033[91m lshw failed on {container_name} host\033[0m")

        lscpu_process = subprocess.run(f"ssh -p {port} {user}@{ip} sudo lscpu > {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/cpu/lscpu.txt", shell=True)
        if lscpu_process.returncode == 0:
            logging.info(f"monstaver - lscpu successful on {container_name} host")
            time.sleep(1)
        elif "command not found" in lscpu_process.stderr:
            logging.info(f"monstaver - lscpu is not installed. Please install it on {container_name} host")
            print("\033[91mlscpu is not installed. Please install it.\033[0m")
        else:
            logging.error(f"monstaver - lscpu failed on {container_name} host")
            print(f"\033[91m lscpu failed on {container_name} host\033[0m")

        lsmem_process = subprocess.run(f"ssh -p {port} {user}@{ip} sudo lsmem > {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/memory/lsmem.txt", shell=True)
        if lsmem_process.returncode == 0:
            logging.info(f"monstaver - lsmem successful on {container_name} host")
            time.sleep(1)
        elif "command not found" in lsmem_process.stderr:
            logging.info(f"monstaver - lsmem is not installed. Please install it on {container_name} host")
            print("\033[91mlsmem is not installed. Please install it.\033[0m")
        else:
            logging.error(f"monstaver - lsmem failed on {container_name} host")
            print(f"\033[91m lamem failed on {container_name} host\033[0m")

        lspci_process = subprocess.run(f"ssh -p {port} {user}@{ip} sudo lspci > {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/pci/lspci.txt", shell=True)
        if lspci_process.returncode == 0:
            logging.info(f"monstaver - lspci successful on {container_name} host")
            time.sleep(1)
        elif "command not found" in lspci_process.stderr:
            logging.info(f"monstaver - lspci is not installed. Please install it on {container_name} host")
            print("\033[91m lspci is not installed. Please install it.\033[0m")
        else:
            logging.error(f"monstaver - lspci failed on {container_name} host")
            print(f"\033[91m lspci failed on {container_name} host\033[0m")
        
        dmidecode_command = f"ssh -p {port} {user}@{ip} sudo dmidecode -t 1 > {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/server-manufacturer/dmidecode.txt ; "
        dmidecode_command += f"ssh -p {port} {user}@{ip} sudo dmidecode -t 2 > {backup_dir}/{time_dir_name}/configs/{container_name}/hardware/motherboard/dmidecode.txt"
        dmidecode_process = subprocess.run(dmidecode_command, shell=True)
        if dmidecode_process.returncode == 0:
            logging.info(f"monstaver - dmidecode successful on {container_name} host")
            time.sleep(1)
        elif "command not found" in dmidecode_process.stderr:
            logging.info(f"monstaver - dmidecode is not installed. Please install it on {container_name} host")
            print("\033[91m dmidecode is not installed. Please install it.\033[0m")
        else:
            logging.error(f"monstaver - dmidecode failed on {container_name} host")
            print(f"\033[91m dmidecode failed on {container_name} host\033[0m")
        
    #### Execute commands to gather OS information ####
    if software_info:
        logging.info(f"monstaver - user select switch -os for software info") 
        sysctl_process = subprocess.run(f"ssh -p {port} {user}@{ip} sudo sysctl -a > {backup_dir}/{time_dir_name}/configs/{container_name}/software/system/sysctl.txt", shell=True)
        if sysctl_process.returncode == 0:
            logging.info(f"monstaver - sysctl -a successful on {container_name}")
            time.sleep(1)
        else:
            logging.error(f"monstaver - sysctl failed on {container_name}")
            print(f"\033[91m sysctl failed on {container_name}\033[0m")

        ps_aux_process = subprocess.run(f"ssh -p {port} {user}@{ip} sudo ps -aux > {backup_dir}/{time_dir_name}/configs/{container_name}/software/system/ps-aux.txt", shell=True)
        if ps_aux_process.returncode == 0:
            logging.info(f"monstaver - ps -aux successful on {container_name}")
            time.sleep(1)
        else:
            logging.error(f"monstaver - ps_aux failed on {container_name}")          
            print(f"\033[91m ps_aux failed on {container_name}\033[0m")

        list_unit_process = subprocess.run(f"ssh -p {port} {user}@{ip} sudo systemctl list-units > {backup_dir}/{time_dir_name}/configs/{container_name}/software/system/systemctl.txt", shell=True)
        if list_unit_process.returncode == 0:
            logging.info(f"monstaver - systemctl list-units successful on {container_name}")
            time.sleep(1)
        else:
            logging.error(f"monstaver - systemctl list-units failed on {container_name}")           
            print(f"\033[91msystemctl list-units failed on {container_name}\033[0m")

        lsmod_process = subprocess.run(f"ssh -p {port} {user}@{ip} sudo lsmod > {backup_dir}/{time_dir_name}/configs/{container_name}/software/system/lsmod.txt", shell=True)
        if lsmod_process.returncode == 0:
            logging.info(f"monstaver - lsmod successful on {container_name}")
            time.sleep(1)
        elif "command not found" in lsmod_process.stderr:
            logging.info(f"monstaver - lsmod is not installed. Please install it on {container_name}")
            print("\033[91mlsmod is not installed. Please install it.\033[0m")
        else:
            logging.error(f"monstaver - lsmod failed on {container_name}")
            print(f"\033[91mlsmod failed on {container_name}\033[0m")
        
        lsof_command = f"ssh -p {port} {user}@{ip} sudo lsof 2>/dev/null | wc -l > {backup_dir}/{time_dir_name}/configs/{container_name}/software/system/lsof.txt ; "
        lsof_command += f"ssh -p {port} {user}@{ip} sudo lsof 2>/dev/null > {backup_dir}/{time_dir_name}/configs/{container_name}/software/system/lsof_full.txt"
        lsof_process = subprocess.run(lsof_command, shell=True)
        if lsof_process.returncode == 0:
            logging.info(f"monstaver - lsof successful on {container_name}")
            time.sleep(1)
        elif "command not found" in lsof_process.stderr:
            logging.info(f"monstaver - lsof is not installed. Please install it on {container_name}")
            print("\033[91mlsof is not installed. Please install it.\033[0m")
        else:
            logging.error(f"monstaver - lsof failed on {container_name}")
            print(f"\033[91mlsof failed on {container_name}\033[0m")

        proc_mount = subprocess.run(f"ssh -p {port} {user}@{ip} sudo cat /proc/mounts > {backup_dir}/{time_dir_name}/configs/{container_name}/software/system/proc_mounts.txt", shell=True)
        if proc_mount.returncode == 0:
            logging.info(f"monstaver - proc_mount collect successful on {container_name}")
            time.sleep(1)
        else:
            logging.error(f"monstaver - proc_mount collect failed on {container_name}")
            print(f"\033[91m proc_mount collect failed on {container_name}\033[0m")

        lsblk = subprocess.run(f"ssh -p {port} {user}@{ip} sudo lsblk -o NAME,SCHED,FSTYPE > {backup_dir}/{time_dir_name}/configs/{container_name}/software/system/lsblk.txt", shell=True)
        if lsblk.returncode == 0:
            logging.info(f"monstaver - lsblk successful on {container_name}")
            time.sleep(1)
        elif "command not found" in lsblk.stderr:
            logging.info(f"monstaver - lsblk is not installed. Please install it on {container_name}")
            print("\033[91m lsblk is not installed. Please install it.\033[0m")
        else:
            logging.error(f"monstaver - lsblk failed on {container_name}")
            print(f"\033[91m lsblk failed on {container_name}\033[0m")

        xfs_info = subprocess.run(f"ssh -p {port} {user}@{ip} sudo lsblk -o name,fstype | grep -oP '\\w+.*(?=\\s+xfs)' | sed 's/\\(.*\\)-/mapper\\/\\1-/' | xargs -I {{}} bash -c 'echo --------------------; sudo xfs_info /dev/{{}};' > {backup_dir}/{time_dir_name}/configs/{container_name}/software/system/xfs_info.txt", shell=True)
        if xfs_info.returncode == 0:                              
            logging.info(f"monstaver - lsblk_xfs_info successful on {container_name}")
            time.sleep(1)
        elif "command not found" in xfs_info.stderr:
            logging.info(f"monstaver - lsblk/sed/xargs is not installed. Please install it on {container_name}")
            print("\033[91m lsblk/sed/xargs is not installed. Please install it.\033[0m")
        else:
            logging.error(f"monstaver - lsblk_xfs_info failed on {container_name}")
            print(f"\033[91m lsblk_xfs_info failed on {container_name}\033[0m")

    # remove /influxdb-backup/time_dir from container and host
    rm_cont_host_dir_process = subprocess.run(f"ssh -p {port} {user}@{ip} sudo rm -rf {backup_dir}-tmp/* ; ssh -p {port} {user}@{ip} sudo docker exec {container_name} rm -rf {backup_dir}-tmp/* ", shell=True)
    if rm_cont_host_dir_process.returncode == 0:
        logging.info(f"monstaver - remove /influxdb-backup/time_dir from container and host successful for {ip} and {container_name}")
        bar()
    else: 
        logging.error(f"monstaver - failure in remove tmp dir in cont and host for {ip} and {container_name}")
        print(f"\033[91mfailure in remove tmp dir in cont and host for {ip} and {container_name}\033[0m")
                 
##### RESTORE PARTS #####
def restore(data_loaded):
    logging.info("Executing monstaver restore function")
    for mc_server, config in data_loaded.get('influxdbs_restore', {}).items(): 
        ip_influxdb = config.get('ip')
        ssh_port = config.get('ssh_port')
        ssh_user = config.get('ssh_user')
        container_name = config.get('container_name')
        influx_mount_point = config.get('influx_volume')
        databases = config.get('databases')
        for db_info in databases:
            prefix = db_info.get('prefix')
            location = db_info.get('location') 
            try:
                output_bytes = subprocess.check_output(f"tar -tvf {location} | grep '^d'", shell=True)
                output = output_bytes.decode('utf-8')
                # Filter out directories that start with a dot
                directories = [line.split()[-1] for line in output.split('\n') if line.startswith('d') and not line.endswith('./')]
                source_db_name = None
                for line in directories:
                    # Extract the directory name
                    source_db_name = line.split()[-1].split('/')[1]
            except subprocess.CalledProcessError as e:
                print(f"Error reading: {location} {e}")
                continue
            if source_db_name is None:
                logging.critical(f"monstaver - Error: No suitable subdirectories found inside {location}")
                print(f"Error: No suitable subdirectories found inside {location}")
                continue
            # Append the prefix to the extracted database name
            destination_db_name = prefix + source_db_name
            logging.info(f"monstaver - new DB name :{destination_db_name}")

            print()
            print(f"*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-* START OF RESTORE FOR\033[92m {mc_server} | {destination_db_name} \033[0m*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
       
            # Drop second_db
            drop_process = subprocess.run(f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} \"sudo docker exec -i -u root {container_name} influx -execute 'drop database {destination_db_name}'\"", shell=True)
            exit_code = drop_process.returncode
            if exit_code == 0:
                print()
                logging.info(f"monstaver - Drop database {destination_db_name} successfully")
                print(f"\033[92mDrop database {destination_db_name} successfully.\033[0m")
                print()
            else:
                logging.error(f"monstaver - Drop database {destination_db_name} failed")
                print(f"\033[91mDrop database {destination_db_name} failed.\033[0m")
                print()

            # Create second_db
            create_process = subprocess.run(f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} \"sudo docker exec -i -u root {container_name} influx -execute 'create database {destination_db_name}'\"", shell=True)
            exit_code = create_process.returncode
            if exit_code == 0:
                logging.info(f"monstaver - Create database {destination_db_name} successfully")
                print(f"\033[92mCreate database {destination_db_name} successfully.\033[0m")
                print()
            else:
                logging.error(f"monstaver - Create database {destination_db_name} failed")
                print(f"\033[91mCreate database {destination_db_name} failed.\033[0m")
                print()

            # Ensure the target restore directory exists
            create_dir_process = subprocess.run(f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i -u root {container_name} mkdir -p {influx_mount_point}/MPK_RESTORE/{mc_server}-{destination_db_name}/backup_tar && sudo docker exec -i -u root {container_name} mkdir -p {influx_mount_point}/MPK_RESTORE/{mc_server}-{destination_db_name}/backup_untar'", shell=True)
            create_dir_exit_code = create_dir_process.returncode
            if create_dir_exit_code == 0:
                logging.info(f"monstaver - Restore directory created successfully: {create_dir_process}")
                print("\033[92mRestore directory created successfully.\033[0m")
                print()
            else:
                logging.critical(f"monstaver - Failed to create restore directory: {create_dir_process}")
                print("\033[91mFailed to create restore directory.\033[0m")
                print()
                sys.exit(1)

            # Copy backup file to container mount point
            copy_process = subprocess.run(f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker cp {location} {container_name}:{influx_mount_point}/MPK_RESTORE/{mc_server}-{destination_db_name}/backup_tar'", shell=True)
            exit_code = copy_process.returncode
            if exit_code == 0:
                logging.info(f"monstaver - Copy to mount point successfully: {copy_process}")
                print(f"\033[92mCopy to mount point successfully.\033[0m")
                print()
            else:
                logging.error(f"monstaver - Copy to mount point failed: {copy_process}")
                print(f"\033[91mCopy to mount point failed.\033[0m")
                print()
    
            # Extract the backup.tar.gz
            extract_process = subprocess.run(f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i -u root {container_name} tar -xf {influx_mount_point}/MPK_RESTORE/{mc_server}-{destination_db_name}/backup_tar/{container_name}.tar.gz -C {influx_mount_point}/MPK_RESTORE/{mc_server}-{destination_db_name}/backup_untar/'", shell=True)
            exit_code = extract_process.returncode
            if exit_code == 0:
                logging.info(f"monstaver - Backup extracted successfully: {extract_process}")
                print("\033[92mBackup extracted successfully.\033[0m")
                print()
            else:
                logging.critical(f"monstaver - Extraction failed: {extract_process}")
                print("\033[91mExtraction failed.\033[0m")
                print()
                sys.exit(1)

            # Restore on influxdb phase - Ckeck if it is first backup or not - Define the command you want to run
            check_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} \"sudo docker exec -i -u root {container_name} influx -execute 'SHOW DATABASES'\""
            try:
                output_bytes = subprocess.check_output(check_command, shell=True)
                output = output_bytes.decode('utf-8')
            except subprocess.CalledProcessError as e:
                logging.error(f"monstaver - Checking command failed with error: {e}")
                print(f"\033[91mChecking command failed with error : \033[0m: {e}")
                print()
                output = None

            # Restore backup to temporay database
            if output is not None and source_db_name in output:
                restore_process = subprocess.run(f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i -u root {container_name} influxd restore -portable -db {source_db_name} -newdb tempdb {influx_mount_point}/MPK_RESTORE/{mc_server}-{destination_db_name}/backup_untar/{source_db_name} > /dev/null 2>&1'", shell=True)
                restore_exit_code = restore_process.returncode
                if restore_exit_code == 0:
                    logging.info(f"monstaver - Restore data to temporary database successfully: {restore_process}")
                    print("\033[92mRestore data to temporary database successfully.\033[0m")
                    print()
                else:
                    logging.critical(f"monstaver - Restore data to temporary database failed: {restore_process}")
                    print("\033[91mRestore data to temporary database failed.\033[0m")
                    print()
                    sys.exit(1)
      
                # Merge phase
                merge_process = subprocess.run(f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} \"sudo docker exec -i -u root {container_name} influx -execute 'SELECT * INTO \"{destination_db_name}\".autogen.:MEASUREMENT FROM \"tempdb\".autogen./.*/ GROUP BY *'\" > /dev/null 2>&1 ", shell=True)
                merge_exit_code = merge_process.returncode
                if merge_exit_code == 0:
                    logging.info(f"monstaver - Merging data to second database successfully: {merge_process}")
                    print("\033[92mMerging data to second database successfully.\033[0m")
                    print()
                else:
                    logging.critical(f"monstaver - Failure in merging data to second database: {merge_process}")
                    print("\033[91mFailure in merging data to second database.\033[0m")
                    print()
                    sys.exit(1)

                # Drop tmp db
                drop_tmp_process = subprocess.run(f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} \"sudo docker exec -i -u root {container_name} influx -execute 'drop database tempdb'\"", shell=True)
                if drop_tmp_process.returncode == 0:
                    logging.info("monstaver - Dropping temporary database successfully")
                    print("\033[92mDropping temporary database successfully.\033[0m")
                    print()
                    logging.info("monstaver - All restore processes complete")
                    print("\033[92mAll restore processes complete.\033[0m")
                    print()
                else:
                    logging.error("monstaver - Dropping temporary database failed")
                    print("\033[91mDropping temporary database failed.\033[0m")
                    print()
             
                # remove untar and tar file in container
                del_restore_process = subprocess.run(f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec {container_name} rm -rf {influx_mount_point}'", shell=True)
                if del_restore_process.returncode == 0:
                    logging.info("monstaver - remove untar and tar file in container successfully")
                    time.sleep(1)
                else:
                    logging.error("monstaver - Remove time dir inside container failed")
                    print("\033[91mRemove time dir inside container failed.\033[0m")
                    sys.exit(1)

                print(f"*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-* END OF RESTORE FOR\033[92m {mc_server} | {destination_db_name} \033[0m*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
                print()

            # If main database does not exist 
            elif output is not None and databases not in output:
                    restore_process = subprocess.run(f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i -u root {container_name} influxd restore -portable -db {source_db_name} {influx_mount_point}/MPK_RESTORE/{mc_server}-{destination_db_name}/backup_untar'", shell=True)
                    if restore_process.returncode == 1:
                        logging.critical(f"monstaver - Restore failed:{output} is not None and {databases} not in {output}")
                        print("\033[91mRestore failed.\033[0m")
                        print()
                    else:
                        logging.info("monstaver - Backup restored successfully(First Time Backup!)")
                        print("\033[92mBackup restored successfully(First Time Backup!).\033[0m")

##### BACKUP PARTS #####
def backup(time_range, inputs, delete, data_loaded, hardware_info, software_info, swift_info, influx_backup):
    logging.info("Executing monstaver backup function")
    if time_range is None:
        time_range = data_loaded['default'].get('time')
    if inputs is not None:
        if ',' in inputs:
            inputs = inputs.split(',')
        else:
            inputs
    else:
        default_input_paths = data_loaded['default'].get('input_paths')
        if default_input_paths:
            inputs = default_input_paths
        else:
            inputs = []
    if not hardware_info:
        hardware_info = data_loaded['default'].get('hardware_backup', False)
    if not software_info:
        software_info = data_loaded['default'].get('software_backup', False)
    if not swift_info:
        swift_info = data_loaded['default'].get('swift_backup', False)
    logging.info(f"monstaver - hardware / software / swift backup options: {hardware_info}/{software_info}/{swift_info}")
    backup_dir = data_loaded['default'].get('backup_output')
    start_time_str, end_time_str = time_range.split(',')
    logging.info(f"monstaver - start time & end time of backup: {start_time_str}, {end_time_str}")
    margin_start, margin_end = map(int, data_loaded['default'].get('time_margin').split(',')) 
    start_time_backup, end_time_backup, time_dir_name = convert_time(start_time_str, end_time_str, margin_start, margin_end)
    logging.debug(f"monstaver - converted time to utc and dir name: {start_time_backup}, {end_time_backup}, {time_dir_name}")
    influx_steps = 6 if influx_backup else 0
    total_steps = (len(data_loaded['db_sources']) * influx_steps + sum([len(data_loaded["db_sources"][x]["databases"]) for x in data_loaded["db_sources"]]) + len(data_loaded['swift']) * 6) - 1
    with alive_bar(total_steps, title=f'\033[1mProcessing Backup\033[0m:\033[92m {start_time_str} - {end_time_str}\033[0m') as bar:
        #create dbs-swif-other_info sub dirs in {time} directory 
        subprocess.run(f"sudo mkdir -p {backup_dir}", shell=True)
        os.makedirs(f"{backup_dir}/{time_dir_name}", exist_ok=True)
        os.makedirs(f"{backup_dir}/{time_dir_name}/dbs", exist_ok=True)
        os.makedirs(f"{backup_dir}/{time_dir_name}/other_info", exist_ok=True)
        os.makedirs(f"{backup_dir}/{time_dir_name}/configs", exist_ok=True)
        subprocess.run(f"sudo chmod -R 777 {backup_dir}", shell=True)
        if influx_backup:
            logging.info(f"monstaver - user select switch -ib for backup") 
            database_names = [db_name for config in data_loaded.get('db_sources', {}).values() if isinstance(config, dict) and 'databases' in config for db_name in config['databases']]
            logging.debug(f"monstaver - db name: {database_names}")
            for mc_server, config in data_loaded.get('db_sources', {}).items(): 
                ip_influxdb = config.get('ip')
                ssh_port = config.get('ssh_port')
                ssh_user = config.get('ssh_user')
                container_name = config.get('container_name')
                influx_volume = config.get('influx_volume')
                for db_name in database_names:
                    # Perform backup using influxd backup command
                    start_time = time.time()
                    backup_process = subprocess.run(f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i -u root {container_name} influxd backup -portable -db {db_name} -start {start_time_backup} -end {end_time_backup} {influx_volume}/{time_dir_name}/{container_name}/{db_name} > /dev/null 2>&1'", shell=True, check=True, timeout=240)
                    end_time = time.time() 
                    response_time = end_time - start_time
                    if response_time > 120:  # Check if the time taken exceeds 2 minutes (120 seconds)
                        print("\033[91mBackup process took more than 2 minutes. let me check something,there is a problem in your influxdb\033[0m")
                        # ping MC server
                        ping_process = subprocess.Popen(["ping", "-c", "1", ip_influxdb], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        ping_output, ping_error = ping_process.communicate()
                        if ping_process.returncode == 0:
                            logging.info(f"monstaver - Server {ip_influxdb} is reachable")
                            print(f"Server {ip_influxdb} is reachable.")
                            # check influxdb container
                            check_container = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker ps -f name={container_name}'"
                            try:
                                check_container_result = subprocess.run(check_container, shell=True, capture_output=True, text=True, check=True)
                                if check_container_result.stdout:
                                    if "Up" in check_container_result.stdout:
                                        logging.info(f"monstaver - Container: {container_name} is up and running")
                                        print(f"Container: {container_name} is up and running.")
                                        # check influxdb service
                                        check_influx_service_result = subprocess.run(f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec {container_name} service influxdb status'", shell=True, check=True, capture_output=True, text=True)
                                        if "is running [ OK ]" in check_influx_service_result.stdout:
                                            logging.info("monstaver - influxdb service is up and running")
                                            print("influxdb service is up and running")
                                             # check database inside influx
                                            check_db_command_result = subprocess.run(f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} \"sudo docker exec -i -u root {container_name} influx -execute 'SHOW DATABASES'\"", shell=True, check=True, capture_output=True, text=True)
                                            if db_name in check_db_command_result.stdout:
                                                logging.info(f"monstaver - database: {db_name} exists in influxdb")
                                                print(f"database: {db_name} exists in influxdb")
                                            else:
                                                logging.error(f"monstaver - database: {db_name} didn't exists in influxdb")
                                                print(f"database: {db_name} didn't exists in influxdb")
                                        else:
                                            logging.error("monstaver - influxdb service is down or not exists")
                                            print("influxdb service is down or not exists")
                                    else:
                                        logging.critical(f"monstaver - Container: {container_name} is not running or exists")
                                        print(f"Container: {container_name} is not running or exists.")
                            except subprocess.CalledProcessError as e:
                                logging.critical(f"monstaver - Error executing SSH command")
                                print(f"Error executing SSH command: {e}")
                        else:
                            logging.critical(f"monstaver - Server {ip_influxdb} is unreachable")
                            print(f"Server {ip_influxdb} is unreachable.")
                    if backup_process.returncode == 0:
                        logging.info("monstaver - backup successful")
                        print("backup successful")
                        bar()
                    else:
                        logging.critical("monstaver - backup failed")
                        print("\033[91mBackup failed.\033[0m")

                    # run in multithread 
                    backup_futures_list = []
                    backup_executor = concurrent.futures.ThreadPoolExecutor()
                    #with concurrent.futures.ThreadPoolExecutor() as backup_executor:
                    backup_future = backup_executor.submit(backup_data_collector, ssh_port, ssh_user, ip_influxdb, container_name, influx_volume, time_dir_name, bar, backup_dir)
                    backup_futures_list.append(backup_future)
            backup_results_list = []
            for backup_future in concurrent.futures.as_completed(backup_futures_list):
                try:
                    backup_result = backup_future.result()
                    backup_results_list.append(backup_result)
                except Exception as exc:
                    print(f"Task generated an exception: {exc}")
            backup_executor.shutdown()
            
        #copy other files
        for path in inputs:
            other_dir_process = subprocess.run(f"sudo cp -rp {path} {backup_dir}/{time_dir_name}/other_info/", shell=True)
            if other_dir_process.returncode == 0:
                logging.info(f"monstaver - all input_paths copy to other_info dir: {inputs}")
                print("all input_paths copy to other_info dir")
            else:
                logging.error(f"monstaver - copy input_paths failed: {inputs}")
                print("\033[91mcopy input_paths failed.\033[0m")

        # copy monstaver config file to backup
        monstaver_conf_process =  subprocess.run(f"sudo cp {config_file} {backup_dir}/{time_dir_name}/other_info/", shell=True)
        if monstaver_conf_process.returncode == 0:
            logging.info(f"monstaver - copy monstaver config file to {backup_dir}/{time_dir_name}/other_info/")
            time.sleep(1)
        else:
            logging.error(f"monstaver - copy monstaver config file to {backup_dir}/{time_dir_name}/other_info/ failed")
            print("\033[91mcopy monstaver config failed.\033[0m")
        
        # run in multithread 
        info_futures_list = []
        with concurrent.futures.ThreadPoolExecutor() as info_executor:
            # copy ring and config to output
            for key,value in data_loaded['swift'].items():
                container_name = key
                user = value['ssh_user']
                ip = value['ip_swift']
                port = value['ssh_port']
                future = info_executor.submit(info_collector, port, user, ip, backup_dir, time_dir_name, container_name, bar, swift_info, hardware_info, software_info)
                info_futures_list.append(future)
            info_results_list = []
            for future in concurrent.futures.as_completed(info_futures_list):
                try:
                    info_result = future.result()
                    info_results_list.append(info_result)
                except Exception as exc:
                    print(f"Task generated an exception: {exc}")
        
        # tar all result inside output dir
        tar_output_process = subprocess.run(f"sudo tar -C {backup_dir} -cf {backup_dir}/{time_dir_name}.tar.gz {time_dir_name}", shell=True)
        if tar_output_process.returncode == 0:
            logging.info(f"monstaver - all files compressed in : {backup_dir}/{time_dir_name}.tar.gz")
            print(f"all files compressed in : {backup_dir}/{time_dir_name}.tar.gz")
            time.sleep(1)
        else:
            logging.error(f"monstaver - tar time dir inside output dir failed: {backup_dir}/{time_dir_name}.tar.gz")
            print("\033[91mtar time dir inside output dir failed.\033[0m")
            sys.exit(1)
        
        # delete orginal time dir inside output dir use -d switch        
        if delete:
            logging.info(f"monstaver - user select switch -d for delete final backup") 
            time_del_process = subprocess.run(f"sudo rm -rf {backup_dir}/{time_dir_name}", shell=True)
            if time_del_process.returncode == 0:
                logging.info(f"monstaver - delete orginal backup dir inside {backup_dir}/{time_dir_name} successful")
                time.sleep(1)
            else:
                logging.error(f"monstaver - delete orginal backup dir inside {backup_dir}/{time_dir_name} failed")
                print("\033[91mremove orginal backup dir inside output dir failed.\033[0m")
                sys.exit(1)

        # upload backup to monster
        token_url = data_loaded['default'].get('token_url')
        username = data_loaded['default'].get('username')
        password = data_loaded['default'].get('password')
        cont_name = data_loaded['default'].get('cont_name')
        public_url = data_loaded['default'].get('public_url')
        if token_url and username and password and cont_name and public_url:
            logging.info("upload backup to monster run")
            heads = {f"X-Storage-User":username,"X-Storage-Pass":password}
            response = requests.get(token_url,headers=heads)
            if response.status_code in [200, 201, 202]:
                token = response.headers["X-Auth-Token"]
                headers = {"X-Auth-Token": token}
                logging.debug(f"token get from monster: {token}")
                create_container = requests.put(f"{public_url}/{cont_name}", headers=headers)
                if create_container.status_code in [200, 201, 202]:
                    logging.info(f"contaner {cont_name} created on  monster")
                    upload_backup_process = subprocess.Popen(f"curl -X PUT -T {backup_dir}/{time_dir_name}.tar.gz -H 'X-Auth-Token:{token}' {public_url}/{cont_name}/{time_dir_name}.tar.gz", shell=True)                  
                else:
                    logging.info("create container in monster cloud storage fail before upload backup")
                    print("\033[91mcreate container in monster cloud storage fail before upload backup\033[0m") 
            else:
                logging.info("monstaver can't connect to monster cloud storage")
                print("\033[91mmonstaver can't connect to monster cloud storage\033[0m") 

    backup_to_report = f"{backup_dir}/{time_dir_name}/"
    return backup_to_report

def main(time_range, inputs, delete, backup_restore, hardware_info, software_info, swift_info, influx_backup):
    log_level = load_config(config_file)['log'].get('level')
    if log_level is not None:
        log_level_upper = log_level.upper()
        if log_level_upper == "DEBUG" or log_level_upper == "INFO" or log_level_upper == "WARNING" or log_level_upper == "ERROR" or log_level_upper == "CRITICAL":
            os.makedirs('/var/log/kara/', exist_ok=True)
            logging.basicConfig(filename= '/var/log/kara/all.log', level=log_level_upper, format='%(asctime)s - %(levelname)s - %(message)s')
        else:
            print(f"\033[91mInvalid log level:{log_level}\033[0m")  
    else:
        print(f"\033[91mPlease enter log_level in the configuration file.\033[0m")

    logging.info("****** Monstaver main function start ******")
    data_loaded = load_config(config_file)
    if backup_restore: 
        restore(data_loaded)
        return None
    else:
        return backup(time_range, inputs, delete, data_loaded, hardware_info, software_info, swift_info, influx_backup)
    
if __name__ == "__main__":
    # Command-line argument parsing
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-t", "--time_range", help="Start and end times for backup (format: 'start_time,end_time')")
    argParser.add_argument("-d", "--delete", action="store_true", help="Remove the original time dir inside output dir")
    argParser.add_argument("-i", "--inputs", help="Input paths for copying to result")
    argParser.add_argument("-r", "--restore", action="store_true", help="run restore function")
    argParser.add_argument("-hw", "--hardware_info", action="store_true", help="take hardware info from monster")
    argParser.add_argument("-sw", "--software_info", action="store_true", help="take os/software info from monster")
    argParser.add_argument("-s", "--swift_info", action="store_true", help="take swift info from monster")
    argParser.add_argument("-ib", "--influx_backup", action="store_true", help="take backup from influxdb")
    args = argParser.parse_args()
    main(time_range=args.time_range, inputs=args.inputs.split(',') if args.inputs is not None else args.inputs, delete=args.delete, backup_restore=args.restore, hardware_info=args.hardware_info, software_info=args.software_info, swift_info=args.swift_info, influx_backup=args.influx_backup)
