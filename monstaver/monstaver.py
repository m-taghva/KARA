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
from alive_progress import alive_bar

#logging.basicConfig(filename='/var/log/kara.log', level=logging.CRITICAL , format='%(asctime)s - %(levelname)s - %(message)s')

config_file = "/etc/KARA/monstaver.conf"

def load_config(config_file):
    with open(config_file, "r") as stream:
        try:
            data_loaded = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"Error loading the configuration: {exc}")
            sys.exit(1)
    return data_loaded

def tehran_time_to_utc(tehran_time_str):
    tehran_tz = pytz.timezone('Asia/Tehran')
    utc_tz = pytz.utc
    tehran_time = tehran_tz.localize(tehran_time_str)
    utc_time = tehran_time.astimezone(utc_tz)
    return utc_time

def convert_time(start_time_str, end_time_str, margin_start, margin_end):
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
    return start_time_backup,end_time_backup,time_dir_name

##### RESTORE PARTS #####
def restore(data_loaded):
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
                list_command = f"tar -tvf {location} | grep '^d'"
                output_bytes = subprocess.check_output(list_command, shell=True)
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
                print(f"Error: No suitable subdirectories found inside {location}")
                continue
            # Append the prefix to the extracted database name
            destination_db_name = prefix + source_db_name

            print()
            print(f"*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-* START OF RESTORE FOR\033[92m {mc_server} | {destination_db_name} \033[0m*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
       
            # Drop second_db
            drop_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} \"sudo docker exec -i -u root {container_name} influx -execute 'drop database {destination_db_name}'\""
            drop_process = subprocess.run(drop_command, shell=True)
            exit_code = drop_process.returncode
            if exit_code == 0:
                print()
                print(f"\033[92mDrop database {destination_db_name} successfully.\033[0m")
                print()
            else:
                print(f"\033[91mDrop database {destination_db_name} failed.\033[0m")
                print()

            # Create seconf_db
            create_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} \"sudo docker exec -i -u root {container_name} influx -execute 'create database {destination_db_name}'\""
            create_process = subprocess.run(create_command, shell=True)
            exit_code = create_process.returncode
            if exit_code == 0:
                print(f"\033[92mCreate database {destination_db_name} successfully.\033[0m")
                print()
            else:
                print(f"\033[91mCreate database {destination_db_name} failed.\033[0m")
                print()

            # Ensure the target restore directory exists
            create_dir_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i -u root {container_name} mkdir -p {influx_mount_point}/MPK_RESTORE/{mc_server}-{destination_db_name}/backup_tar && sudo docker exec -i -u root {container_name} mkdir -p {influx_mount_point}/MPK_RESTORE/{mc_server}-{destination_db_name}/backup_untar'"
            create_dir_process = subprocess.run(create_dir_command, shell=True)
            create_dir_exit_code = create_dir_process.returncode
            if create_dir_exit_code == 0:
                print("\033[92mRestore directory created successfully.\033[0m")
                print()
            else:
                print("\033[91mFailed to create restore directory.\033[0m")
                print()
                sys.exit(1)

            # Copy backup file to container mount point
            copy_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker cp {location} {container_name}:{influx_mount_point}/MPK_RESTORE/{mc_server}-{destination_db_name}/backup_tar'"
            copy_process = subprocess.run(copy_command, shell=True)
            exit_code = copy_process.returncode
            if exit_code == 0:
                print(f"\033[92mCopy to mount point successfully.\033[0m")
                print()
            else:
                print(f"\033[91mCopy to mount point failed.\033[0m")
                print()
    
            # Extract the backup.tar.gz
            extract_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i -u root {container_name} tar -xf {influx_mount_point}/MPK_RESTORE/{mc_server}-{destination_db_name}/backup_tar/{container_name}.tar.gz -C {influx_mount_point}/MPK_RESTORE/{mc_server}-{destination_db_name}/backup_untar/'"
            extract_process = subprocess.run(extract_command, shell=True)
            exit_code = extract_process.returncode
            if exit_code == 0:
                print("\033[92mBackup extracted successfully.\033[0m")
                print()
            else:
                print("\033[91mExtraction failed.\033[0m")
                print() 

            # Restore on influxdb phase - Ckeck if it is first backup or not - Define the command you want to run
            check_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} \"sudo docker exec -i -u root {container_name} influx -execute 'SHOW DATABASES'\""
            try:
                output_bytes = subprocess.check_output(check_command, shell=True)
                output = output_bytes.decode('utf-8')
            except subprocess.CalledProcessError as e:
                print(f"\033[91mChecking command failed with error : \033[0m: {e}")
                print()
                output = None

            # Restore backup to temporay database
            if output is not None and source_db_name in output:
                restore_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i -u root {container_name} influxd restore -portable -db {source_db_name} -newdb tempdb {influx_mount_point}/MPK_RESTORE/{mc_server}-{destination_db_name}/backup_untar/{source_db_name} > /dev/null 2>&1'"
                restore_process = subprocess.run(restore_command, shell=True)
                restore_exit_code = restore_process.returncode
                if restore_exit_code == 0:
                    print("\033[92mRestore data to temporary database successfully.\033[0m")
                    print()
                else:
                    print("\033[91mRestore data to temporary database failed.\033[0m")
                    print()
      
                # Merge phase
                merge_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} \"sudo docker exec -i -u root {container_name} influx -execute 'SELECT * INTO \"{destination_db_name}\".autogen.:MEASUREMENT FROM \"tempdb\".autogen./.*/ GROUP BY *'\" > /dev/null 2>&1 "
                merge_process = subprocess.run(merge_command, shell=True)
                merge_exit_code = merge_process.returncode
                if merge_exit_code == 0:
                    print("\033[92mMerging data to second database successfully.\033[0m")
                    print()
                else:
                    print("\033[91mFailure in merging data to second database.\033[0m")
                    print()

                # Drop tmp db
                drop_tmp_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} \"sudo docker exec -i -u root {container_name} influx -execute 'drop database tempdb'\""
                drop_tmp_process = subprocess.run(drop_tmp_command, shell=True)
                drop_tmp_exit_code = drop_tmp_process.returncode
                if drop_tmp_exit_code == 0:
                    print("\033[92mDropping temporary database successfully.\033[0m")
                    print()
                    print("\033[92mAll restore processes complete.\033[0m")
                    print()
                else:
                    print("\033[91mDropping temporary database failed.\033[0m")
                    print()
             
                # remove untar and tar file in container
                del_restore_cont = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec {container_name} rm -rf {influx_mount_point}'"
                del_restore_process = subprocess.run(del_restore_cont, shell=True)
                if del_restore_process.returncode == 0:
                    time.sleep(1)
                else:
                    print("\033[91mRemove time dir inside container failed.\033[0m")
                    sys.exit(1)

                print(f"*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-* END OF RESTORE FOR\033[92m {mc_server} | {destination_db_name} \033[0m*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
                print()

            # If main database does not exist 
            elif output is not None and databases not in output:
                    restore_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i -u root {container_name} influxd restore -portable -db {source_db_name} {influx_mount_point}/MPK_RESTORE/{mc_server}-{destination_db_name}/backup_untar'"
                    restore_process = subprocess.run(restore_command, shell=True)
                    restore_exit_code = restore_process.returncode
                    if restore_exit_code == 1:
                        print("\033[91mRestore failed.\033[0m")
                        print()
                    else:
                        print("\033[92mBackup restored successfully(First Time Backup!).\033[0m")
            else:
                print("error") 

##### BACKUP PARTS #####
def backup(time_range, inputs, delete, data_loaded, hardware_info, os_info, swift_info, influx_backup):
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
            
    backup_dir = data_loaded['default'].get('backup_output')
    start_time_str, end_time_str = time_range.split(',')
    margin_start, margin_end = map(int, data_loaded['default'].get('time_margin').split(',')) 
    start_time_backup, end_time_backup, time_dir_name = convert_time(start_time_str, end_time_str, margin_start, margin_end)
    influx_steps = 6 if influx_backup else 0
    total_steps = (len(data_loaded['db_sources']) * influx_steps + sum([len(data_loaded["db_sources"][x]["databases"]) for x in data_loaded["db_sources"]]) + len(data_loaded['swift']) * 6) - 1
    with alive_bar(total_steps, title=f'\033[1mProcessing Backup\033[0m:\033[92m {start_time_str} - {end_time_str}\033[0m') as bar:

        #create dbs-swif-other_info sub dirs in {time} directory 
        subprocess.run(f"sudo mkdir -p {backup_dir}", shell=True)
        os.makedirs(f"{backup_dir}/{time_dir_name}", exist_ok=True)
        os.makedirs(f"{backup_dir}/{time_dir_name}/dbs", exist_ok=True)
        os.makedirs(f"{backup_dir}/{time_dir_name}/other_info", exist_ok=True)
        os.makedirs(f"{backup_dir}/{time_dir_name}/monster_conf", exist_ok=True)
        subprocess.run(f"sudo chmod -R 777 {backup_dir}", shell=True)
        
        if influx_backup:
            database_names = [db_name for config in data_loaded.get('db_sources', {}).values() if isinstance(config, dict) and 'databases' in config for db_name in config['databases']]
            for mc_server, config in data_loaded.get('db_sources', {}).items(): 
                ip_influxdb = config.get('ip')
                ssh_port = config.get('ssh_port')
                ssh_user = config.get('ssh_user')
                container_name = config.get('container_name')
                influx_volume = config.get('influx_volume')
                for db_name in database_names:
                    # Perform backup using influxd backup command
                    start_time = time.time()
                    backup_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i -u root {container_name} influxd backup -portable -db {db_name} -start {start_time_backup} -end {end_time_backup} {influx_volume}/{time_dir_name}/{container_name}/{db_name} > /dev/null 2>&1'"
                    backup_process = subprocess.run(backup_command, shell=True)
                    end_time = time.time() 
                    response_time = end_time - start_time
                    if response_time > 120:  # Check if the time taken exceeds 2 minutes (120 seconds)
                        print("\033[Backup process took more than 2 minutes. Skipping this part. there is a problem in your influxdb\033[0m")
                        sys.exit(0)  # Skip further execution
                    if backup_process.returncode == 0:
                        print("backup successful")
                        bar()
                    else:
                        print("\033[91mBackup failed.\033[0m")
                        sys.exit(1)
            
                    # New_location_backup_in_host = value['temporary_location_backup_host']
                    tmp_backup = "/tmp/influxdb-backup-tmp"
                    mkdir_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo mkdir -p {tmp_backup} && sudo chmod -R 777 {tmp_backup}'"
                    mkdir_process = subprocess.run(mkdir_command, shell=True)
                    if mkdir_process.returncode == 0:
                        time.sleep(1)
                    else:
                        print("\033[91mDirectory creation and permission setting failed.\033[0m")
                        sys.exit(1)

                    # copy backup to temporary dir 
                    cp_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker cp {container_name}:{influx_volume}/{time_dir_name}/{container_name} {tmp_backup}'"
                    cp_process = subprocess.run(cp_command, shell=True)
                    if cp_process.returncode == 0:
                        bar()
                    else:
                        print("\033[91mcopy failed.\033[0m")
                        sys.exit(1)

                    # tar all backup
                    tar_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo tar -cf {tmp_backup}/{container_name}.tar.gz -C {tmp_backup}/{container_name}/ .'"
                    tar_process = subprocess.run(tar_command, shell=True)
                    if tar_process.returncode == 0:
                        bar()
                    else:
                        print("\033[91mTar failed.\033[0m")
                        sys.exit(1)

                    # move tar file to dbs dir inside your server
                    mv_command = f"scp -r -P {ssh_port} {ssh_user}@{ip_influxdb}:{tmp_backup}/*.tar.gz {backup_dir}/{time_dir_name}/dbs/ > /dev/null 2>&1"
                    mv_process = subprocess.run(mv_command, shell=True)
                    if mv_process.returncode == 0:
                        print("all backup moved to your server")
                        bar()
                    else:
                        print("\033[91mMoving files failed.\033[0m")
                        sys.exit(1)

                    # remove temporary location of backup in host
                    del_command_tmp_loc = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo rm -rf {tmp_backup}'"
                    del_process = subprocess.run(del_command_tmp_loc, shell=True)
                    if del_process.returncode == 0:
                        bar()
                    else:
                        print("\033[91mRemove temp dir failed.\033[0m")

                    # delete {time_dir} inside container
                    del_time_cont = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec {container_name} rm -rf {influx_volume}'"
                    del_time_process = subprocess.run(del_time_cont, shell=True)
                    if del_time_process.returncode == 0:
                        bar()
                    else:
                        print("\033[91mRemove time dir inside container failed.\033[0m")

        #copy other files
        for path in inputs:
            other_dir = f"sudo cp -rp {path} {backup_dir}/{time_dir_name}/other_info/"
            other_dir_process = subprocess.run(other_dir, shell=True)
            if other_dir_process.returncode == 0:
                print("all input_paths copy to other_info dir")
            else:
                print("\033[91mCopy input_paths failed.\033[0m")

        # copy monstaver config file in backup
        monstaver_conf = f"sudo cp {config_file} {backup_dir}/{time_dir_name}/other_info/"
        monstaver_conf_process =  subprocess.run(monstaver_conf, shell=True)
        if monstaver_conf_process.returncode == 0:
            time.sleep(1)
        else:
            print("\033[91mCopy monstaver config failed.\033[0m")

        # copy ring and config to output
        for key,value in data_loaded['swift'].items():
            container_name = key
            user = value['ssh_user']
            ip = value['ip_swift']
            port = value['ssh_port']
         
            # make hardware/os/swift sub directories
            mkdir_hwoss_output = f"ssh -p {port} {user}@{ip} sudo mkdir -p {backup_dir}-tmp/{time_dir_name}/monster_conf/{container_name}/os/{container_name}-etc-container/ ; "
            mkdir_hwoss_output += f"sudo mkdir -p {backup_dir}/{time_dir_name}/monster_conf/{container_name}/swift/ ; "
            mkdir_hwoss_output += f"sudo mkdir -p {backup_dir}/{time_dir_name}/monster_conf/{container_name}/hardware ; " 
            mkdir_hwoss_output += f"sudo mkdir -p {backup_dir}/{time_dir_name}/monster_conf/{container_name}/os/{container_name}-etc-host/ ; " 
            mkdir_hwoss_output += f"sudo mkdir -p  {backup_dir}/{time_dir_name}/monster_conf/{container_name}/os/{container_name}-etc-container/ " 
            mkdir_hwoss_process = subprocess.run(mkdir_hwoss_output, shell=True)
            if mkdir_hwoss_process.returncode == 0:
                bar()
            else:
                print("\033[91mmkdir of hardware/os/swift failed.\033[0m")
                sys.exit(1)

            # get swift config files and monster services
            if swift_info:
                get_swift_conf = f"ssh -p {port} {user}@{ip} 'docker exec {container_name} swift-init all status' > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/swift/{container_name}-swift-status.txt ; "
                get_swift_conf += f"ssh -p {port} {user}@{ip} 'docker exec {container_name} service --status-all' > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/os/{container_name}-services-container.txt 2>&1 ; "
                get_swift_conf += f"ssh -p {port} {user}@{ip} docker exec {container_name} cat /etc/swift/container-server.conf > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/swift/{container_name}-container-server.conf ; "
                get_swift_conf += f"ssh -p {port} {user}@{ip} docker exec {container_name} cat /etc/swift/account-server.conf > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/swift/{container_name}-account-server.conf ; "
                get_swift_conf += f"ssh -p {port} {user}@{ip} docker exec {container_name} cat /etc/swift/proxy-server.conf > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/swift/{container_name}-proxy-server.conf ; "
                get_swift_conf += f"ssh -p {port} {user}@{ip} docker exec {container_name} swift-ring-builder /rings/account.builder > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/swift/{container_name}-account-ring.txt ; "
                get_swift_conf += f"ssh -p {port} {user}@{ip} docker exec {container_name} swift-ring-builder /rings/container.builder > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/swift/{container_name}-container-ring.txt ; "
                get_swift_conf += f"ssh -p {port} {user}@{ip} docker exec {container_name} swift-ring-builder /rings/object.builder > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/swift/{container_name}-object-ring.txt ; "
                get_swift_conf += f"ssh -p {port} {user}@{ip} docker exec {container_name} cat /etc/swift/object-server.conf > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/swift/{container_name}-object-server.conf ; "
                get_swift_conf += f"ssh -p {port} {user}@{ip} docker inspect {container_name} > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/os/{container_name}-docker-inspect.txt "
                get_swift_conf_process = subprocess.run(get_swift_conf, shell=True)
                if get_swift_conf_process.returncode == 0:
                    print("all swift configs copy to swift dir")
                    time.sleep(1)
                else:
                    print("\033[91mget swift configs and monster services failed.\033[0m")

            # extract docker compose file path and copy it
            docker_compose = f"ssh -p {port} {user}@{ip} docker inspect {container_name}"
            docker_compose_process = subprocess.run(docker_compose, shell=True, capture_output=True, text=True)
            if docker_compose_process.returncode == 0:
                inspect_result = json.loads(docker_compose_process.stdout)
                docker_compose_file = inspect_result[0]['Config']['Labels'].get('com.docker.compose.project.config_files')
                docker_compose_path = inspect_result[0]['Config']['Labels'].get('com.docker.compose.project.working_dir')
                docker_compose_result = os.path.join(docker_compose_path,docker_compose_file)
            copy_compose_file = f"scp -r -P {port} {user}@{ip}:{docker_compose_result} {backup_dir}/{time_dir_name}/monster_conf/{container_name}/os/ > /dev/null 2>&1"
            copy_compose_file_process = subprocess.run(copy_compose_file, shell=True)
            if copy_compose_file_process.returncode == 0:
                bar()
            else: 
                print("\033[91mFailure in copy compose file\033[0m")

            # copy etc dir from container to host
            get_etc_command =  f"ssh -p {port} {user}@{ip} 'sudo docker cp {container_name}:/etc  {backup_dir}-tmp/{time_dir_name}/monster_conf/{container_name}/os/{container_name}-etc-container/'"
            get_etc_process = subprocess.run(get_etc_command, shell=True)
            if get_etc_process.returncode == 0:
                bar()
            else: 
                print("\033[91mFailure in copy monster etc\033[0m")

            # copy container etc dir from host to your server
            mv_etc_cont_command = f"scp -r -P {port} {user}@{ip}:{backup_dir}-tmp/{time_dir_name}/monster_conf/{container_name}/os/{container_name}-etc-container/etc/*  {backup_dir}/{time_dir_name}/monster_conf/{container_name}/os/{container_name}-etc-container/ > /dev/null 2>&1"
            mv_etc_cont_process = subprocess.run(mv_etc_cont_command, shell=True)
            if mv_etc_cont_process.stderr is None:
                bar()
            else: 
                print("\033[91mFailure in copy container etc dir from host to your server\033[0m")
            
            # copy host etc dir from host to your server
            mv_etc_host_command = f"scp -r -P {port} {user}@{ip}:/etc/*  {backup_dir}/{time_dir_name}/monster_conf/{container_name}/os/{container_name}-etc-host/ > /dev/null 2>&1"
            mv_etc_host_process = subprocess.run(mv_etc_host_command, shell=True)
            if mv_etc_host_process.stderr is None:
                bar()
            else: 
                print("\033[91mFailure in copy host etc dir from host to your server\033[0m")

            #### Execute commands to gather hardware information ####
            if hardware_info:
                lshw_command = f"ssh -p {port} {user}@{ip} sudo lshw > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/hardware/{container_name}-lshw-host.txt"
                lshw_process = subprocess.run(lshw_command, shell=True, capture_output=True, text=True)
                if lshw_process.returncode == 0:
                    time.sleep(1)
                elif "command not found" in lshw_process.stderr:
                    print("\033[91mlshw is not installed. Please install it.\033[0m")
                else:
                    print("\033[91m lshw failed.\033[0m")

                lscpu_command = f"ssh -p {port} {user}@{ip} sudo lscpu > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/hardware/{container_name}-lscpu-host.txt"
                lscpu_process = subprocess.run(lscpu_command, shell=True)
                if lscpu_process.returncode == 0:
                    time.sleep(1)
                elif "command not found" in lscpu_process.stderr:
                    print("\033[91mlscpu is not installed. Please install it.\033[0m")
                else:
                    print("\033[91m lscpu failed.\033[0m")

                lsmem_command = f"ssh -p {port} {user}@{ip} sudo lsmem > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/hardware/{container_name}-lsmem-host.txt"
                lsmem_process = subprocess.run(lsmem_command, shell=True)
                if lsmem_process.returncode == 0:
                    time.sleep(1)
                elif "command not found" in lsmem_process.stderr:
                    print("\033[91mlsmem is not installed. Please install it.\033[0m")
                else:
                    print("\033[91m lamem failed.\033[0m")

                lspci_command = f"ssh -p {port} {user}@{ip} sudo lspci > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/hardware/{container_name}-lspci-host.txt"
                lspci_process = subprocess.run(lspci_command, shell=True)
                if lspci_process.returncode == 0:
                    time.sleep(1)
                elif "command not found" in lspci_process.stderr:
                    print("\033[91mlspci is not installed. Please install it.\033[0m")
                else:
                    print("\033[91m lspci failed.\033[0m")
         
            #### Execute commands to gather OS information ####
            if os_info:
                sysctl_command = f"ssh -p {port} {user}@{ip} sudo sysctl -a > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/os/{container_name}-sysctl-host.txt"
                sysctl_process = subprocess.run(sysctl_command, shell=True)
                if sysctl_process.returncode == 0:
                    time.sleep(1)
                elif "command not found" in sysctl_process.stderr:
                    print("\033[91msysctl is not installed. Please install it.\033[0m")
                else:
                    print("\033[91m sysctl failed.\033[0m")

                ps_aux_command = f"ssh -p {port} {user}@{ip} sudo ps -aux > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/os/{container_name}-ps-aux-host.txt"
                ps_aux_process = subprocess.run(ps_aux_command, shell=True)
                if ps_aux_process.returncode == 0:
                    time.sleep(1)
                else:
                    print("\033[91m ps_aux failed.\033[0m")

                list_unit_command = f"ssh -p {port} {user}@{ip} sudo systemctl list-units > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/os/{container_name}-list-units-host.txt"
                list_unit_process = subprocess.run(list_unit_command, shell=True)
                if list_unit_process.returncode == 0:
                    time.sleep(1)
                else:
                    print("\033[91m list_unit failed.\033[0m")

                lsmod_command = f"ssh -p {port} {user}@{ip} sudo lsmod > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/os/{container_name}-lsmod-host.txt"
                lsmod_process = subprocess.run(lsmod_command, shell=True)
                if lsmod_process.returncode == 0:
                    time.sleep(1)
                elif "command not found" in lsmod_process.stderr:
                    print("\033[91mlsmod is not installed. Please install it.\033[0m")
                else:
                    print("\033[91m lsmod failed.\033[0m")
                
                lsof_command = f"ssh -p {port} {user}@{ip} sudo lsof > {backup_dir}/{time_dir_name}/monster_conf/{container_name}/os/{container_name}-lsof-host.txt 2>&1"
                lsof_process = subprocess.run(lsof_command, shell=True)
                if lsof_process.returncode == 0:
                    time.sleep(1)
                elif "command not found" in lsof_process.stderr:
                    print("\033[91mlsof is not installed. Please install it.\033[0m")
                else:
                    print("\033[91m lsof failed.\033[0m")
            
            # remove /influxdb-backup/time_dir from container and host
            rm_cont_host_dir_command =  f"ssh -p {port} {user}@{ip} sudo rm -rf {backup_dir}-tmp/* ; ssh -p {port} {user}@{ip} sudo docker exec {container_name} rm -rf {backup_dir}-tmp/* "
            rm_cont_host_dir_process = subprocess.run(rm_cont_host_dir_command, shell=True)
            if rm_cont_host_dir_process.returncode == 0:
                bar()
            else: 
                print("\033[91mFailure in remove tmp dir in cont and host\033[0m")
                sys.exit(1)
                 
        # tar all result inside output dir
        tar_output = f"sudo tar -C {backup_dir} -cf {backup_dir}/{time_dir_name}.tar.gz {time_dir_name}"
        tar_output_process = subprocess.run(tar_output, shell=True)
        if tar_output_process.returncode == 0:
            print(f"all files compressed in : {backup_dir}/{time_dir_name}.tar.gz")
            time.sleep(1)
        else:
            print("\033[91mTar time dir inside output dir failed.\033[0m")
            sys.exit(1)
        
        # delete orginal time dir inside output dir use -d switch        
        if delete:
            time_del = f"sudo rm -rf {backup_dir}/{time_dir_name}"
            time_del_process = subprocess.run(time_del, shell=True)
            if time_del_process.returncode == 0:
                time.sleep(1)
            else:
                print("\033[91mRemove time dir inside output dir failed.\033[0m")
                sys.exit(1)

        # upload backup to monster
        token_url = data_loaded['default'].get('token_url')
        username = data_loaded['default'].get('username')
        password = data_loaded['default'].get('password')
        cont_name = data_loaded['default'].get('cont_name')
        public_url = data_loaded['default'].get('public_url')
        if token_url and username and password and cont_name and public_url:
            heads = {f"X-Storage-User":username,"X-Storage-Pass":password}
            response = requests.get(token_url,headers=heads)
            if response.status_code == "200" or "201" or "202":
                token = response.headers["X-Auth-Token"]
                headers = {"X-Auth-Token": token}
                create_container = requests.put(f"{public_url}/{cont_name}", headers=headers)
                if create_container.status_code == "200" or "201" or "202":
                    upload_backup = f"curl -X PUT -T {backup_dir}/{time_dir_name}.tar.gz -H 'X-Auth-Token:{token}' {public_url}/{cont_name}/{time_dir_name}.tar.gz"
                    upload_backup_process = subprocess.run(upload_backup, shell=True)
                    if upload_backup_process.returncode == 0:
                        print("bckup tar file upload to monster cloud storage")
                        time.sleep(1)
                    else:
                        print("\033[91mupload backup to monster failed.\033[0m")
                else:
                    print("\033[91mcreate container in monster cloud storage fail before upload backup.\033[0m")
            else:
                print("\033[91mMonstaver can't connect to monster cloud storage\033[0m")

def main(time_range, inputs, delete, backup_restore, hardware_info, os_info, swift_info, influx_backup):
    data_loaded = load_config(config_file)
    if backup_restore: 
        restore(data_loaded)
    else:
        backup(time_range, inputs, delete, data_loaded, hardware_info, os_info, swift_info, influx_backup)

if __name__ == "__main__":
    # Command-line argument parsing
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-t", "--time_range", help="Start and end times for backup (format: 'start_time,end_time')")
    argParser.add_argument("-d", "--delete", action="store_true", help="Remove the original time dir inside output dir")
    argParser.add_argument("-i", "--inputs", help="Input paths for copying to result")
    argParser.add_argument("-r", "--restore", action="store_true", help="run restore function")
    argParser.add_argument("-hw", "--hardware_info", action="store_true", help="take hardware info from monster")
    argParser.add_argument("-os", "--os_info", action="store_true", help="take os info from monster")
    argParser.add_argument("-sw", "--swift_info", action="store_true", help="take swift info from monster")
    argParser.add_argument("-ib", "--influx_backup", action="store_true", help="take backup from influxdb")
    args = argParser.parse_args()
    main(time_range=args.time_range, inputs=args.inputs.split(',') if args.inputs is not None else args.inputs, delete=args.delete, backup_restore=args.restore, hardware_info=args.hardware_info, os_info=args.os_info, swift_info=args.swift_info, influx_backup=args.influx_backup)
