import os
import subprocess
import re
import csv
import shutil
import time
import argparse
import sys
import yaml
import json
import select
import logging
import concurrent.futures

# variables
config_file = "/etc/kara/mrbench.conf"
pre_test_script = "./../mrbench/pre_test_script.sh"
log_path = "/var/log/kara/"

# For font style
BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[1;33m"
print(f"{YELLOW}========================================{RESET}")

def load_config(config_file):
    with open(config_file, "r") as stream:
        try:
           data_loaded = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
           print(f"Error loading the configuration: {exc}")
           sys.exit(1)
    return data_loaded

def conf_ring_thread(swift_configs, port, user, ip, container_name, key_to_extract): 
    logging.info("mrbench - Executing conf_ring_thread function")   
    ring_dict = {}
    all_scp_file_successful = False
    # Run the docker inspect command and capture the output
    inspect_result = subprocess.run(f"ssh -p {port} {user}@{ip} 'sudo docker inspect {container_name}'", shell=True, capture_output=True, text=True)
    if inspect_result.returncode == 0:
        # Parse the JSON output
        container_info = json.loads(inspect_result.stdout)
        # Check if the key exists in the JSON structure
        if key_to_extract in container_info[0]['Config']['Labels']:
            inspect_value = container_info[0]['Config']['Labels'][key_to_extract]
            logging.info(f"mrbench - mount point path in container: {inspect_value}")
            for filename, filepath in swift_configs.items(): 
                each_scp_successful = False 
                if filename.endswith(".gz") or filename.endswith(".builder"):
                    logging.info(f"mrbench - diff ring files: {filename} and {filepath}")
                    diff_ring_result = subprocess.run(f"ssh -p {port} {user}@{ip} 'sudo cat {inspect_value}/rings/{filename}' | diff - {filepath}", shell=True, capture_output=True, text=True)
                    print("")
                    print(f"please wait for checking ring file [ {filename} ] inside {container_name}")
                    if diff_ring_result.stderr == "" and diff_ring_result.stdout != "":
                        mkdir_tmp_rings_process = subprocess.run(f"ssh -p {port} {user}@{ip} 'sudo mkdir -p /tmp/rings/ > /dev/null 2>&1 && sudo chmod -R 777 /tmp/rings/'", shell=True)
                        copy_ring_command_process = subprocess.run(f"scp -r -P {port} {filepath} {user}@{ip}:/tmp/rings > /dev/null 2>&1", shell=True)
                        move_tmp_root_rings_process = subprocess.run(f"ssh -p {port} {user}@{ip} 'sudo mv /tmp/rings/{filename} {inspect_value}/rings/ > /dev/null 2>&1'", shell=True)
                        if move_tmp_root_rings_process.returncode == 0 and copy_ring_command_process.stderr is None:
                            each_scp_successful = True
                            print("")
                            logging.info(f"mrbench - copy ring file [ {filename} ] to {container_name} successful")
                            print(f"\033[92mcopy ring file [ {filename} ] to {container_name} successful\033[0m")
                        else: 
                            logging.info(f"mrbench - rings in {container_name} failed to sync")
                            print(f"\033[91mrings in {container_name} failed to sync\033[0m")
                    elif diff_ring_result.stderr != "":
                        print("")
                        logging.info(f"mrbench - WARNING: your ring file naming is wrong [ {filename} ] or not exist inside {container_name}")
                        print(f"\033[91mWARNING: your ring file naming is wrong [ {filename} ] or not exist inside {container_name}\033[0m")
                        #exit(1)
                    if "account" in filename:
                        ring_command = f"ssh -p {port} {user}@{ip} 'sudo docker exec {container_name} swift-ring-builder /rings/account.builder'"
                        ring_dict['account'] = subprocess.run(ring_command, shell=True, capture_output=True, text=True).stdout
                        logging.info(f"mrbench - /rings/account.builder of {container_name} append to ring_dict")
                    elif "container" in filename:
                        ring_command = f"ssh -p {port} {user}@{ip} 'sudo docker exec {container_name} swift-ring-builder /rings/container.builder'"
                        ring_dict['container'] = subprocess.run(ring_command, shell=True, capture_output=True, text=True).stdout
                        logging.info(f"mrbench - /rings/container.builder of {container_name} append to ring_dict")
                    else:
                        ring_command = f"ssh -p {port} {user}@{ip} 'sudo docker exec {container_name} swift-ring-builder /rings/object.builder'"
                        ring_dict['object'] = subprocess.run(ring_command, shell=True, capture_output=True, text=True).stdout
                        logging.info(f"mrbench - /rings/object.builder of {container_name} append to ring_dict")
                        
                elif filename.endswith(".conf"):
                    logging.info(f"mrbench - conf files: {filename} and {filepath}")
                    diff_conf_result = subprocess.run(f"ssh -p {port} {user}@{ip} 'sudo cat {inspect_value}/{filename}' | diff - {filepath}", shell=True, capture_output=True, text=True)
                    print("")
                    print(f"please wait for checking config file [ {filename} ] inside {container_name}")
                    if diff_conf_result.stderr == "" and diff_conf_result.stdout != "":
                            mkdir_tmp_configs_process = subprocess.run(f"ssh -p {port} {user}@{ip} 'sudo mkdir -p /tmp/configs/ > /dev/null 2>&1 && sudo chmod -R 777 /tmp/configs/'", shell=True)
                            copy_conf_command_process = subprocess.run(f"scp -r -P {port} {filepath} {user}@{ip}:/tmp/configs > /dev/null 2>&1", shell=True)
                            base_name_changer = os.path.basename(filepath)
                            move_tmp_root_configs_process = subprocess.run(f"ssh -p {port} {user}@{ip} 'sudo mv /tmp/configs/{base_name_changer} {inspect_value}/ > /dev/null 2>&1'", shell=True)
                            if move_tmp_root_configs_process.returncode == 0 and copy_conf_command_process.stderr is None:
                                each_scp_successful = True
                                print("")
                                logging.info(f"mrbench - copy config file [ {filename} ] to {container_name} successful")
                                print(f"\033[92mcopy config file [ {filename} ] to {container_name} successful\033[0m")
                                name_changer_process = subprocess.run(f"ssh -p {port} {user}@{ip} 'sudo mv {inspect_value}/{base_name_changer} {inspect_value}/{filename} > /dev/null 2>&1'", shell=True)
                            else:
                                logging.info(f"mrbench - configs in {container_name} failed to sync")
                                print(f"\033[91mconfigs in {container_name} failed to sync\033[0m")
                    elif diff_conf_result.stderr != "":
                        print("")
                        logging.info(f"mrbench - WARNING: your config file naming is wrong [ {filename} ] or not exist inside {container_name}")
                        print(f"\033[91mWARNING: your config file naming is wrong [ {filename} ] or not exist inside {container_name}\033[0m")
                        #exit(1)
                if each_scp_successful: 
                    all_scp_file_successful = True  
    else:
        print("")
        logging.info(f"mrbench - WARNING: there is a problem in your config file for SSH info inside {container_name} section so mrbench can't sync config and ring files!")
        print(f"\033[91mWARNING: there is a problem in your config file for SSH info inside \033[0m'\033[92m{container_name}\033[0m' \033[91msection so mrbench can't sync config and ring files !\033[0m") 
        print("")
        if inspect_result.stdout == '[]\n':
            logging.info(f"mrbench - WARNING: your container name {container_name} is wrong !")
            print(f"\033[91mWARNING: your container name \033[0m'\033[92m{container_name}\033[0m' \033[91mis wrong !\033[0m")
    if all_scp_file_successful is True:
        restart_cont_command_process = subprocess.run(f"ssh -p {port} {user}@{ip} 'sudo docker restart {container_name}' > /dev/null 2>&1", shell=True)
        if restart_cont_command_process.returncode == 0:
            while True:
                check_container_result = subprocess.run(f"ssh -p {port} {user}@{ip} 'sudo docker ps -f name={container_name}'", shell=True, capture_output=True, text=True, check=True)
                if "Up" in check_container_result.stdout and "healthy" in check_container_result.stdout:
                    check_services_result = subprocess.run(f"ssh -p {port} {user}@{ip} 'sudo docker exec {container_name} service --status-all'", shell=True, capture_output=True, text=True, check=True)
                    if "[ + ]  swift-account\n" or "[ + ]  swift-container\n" or "[ + ]  swift-object\n" or "[ + ]  swift-proxy\n" in check_services_result:
                        time.sleep(30)
                        print("")
                        logging.info(f"mrbench - container {container_name} successfully restart")
                        print(f"\033[92mcontainer {container_name} successfully restart\033[0m")
                        break
        else:
            logging.info(f"mrbench - container {container_name} failed to reatsrt")
            print(f"\033[91mcontainer {container_name} failed to reatsrt\033[0m")
    print(f"{YELLOW}========================================{RESET}")
    return ring_dict

def copy_swift_conf(swift_configs):
    logging.info("mrbench - Executing copy_swift_conf function")
    ring_dict = {}
    data_loaded = load_config(config_file)
    if not 'swift' in data_loaded:
        logging.info("mrbench - Error there isn't swift section in mrbench.conf so ring and conf can't set.")
        print(f"Error there isn't \033[91mswift\033[0m section in mrbench.conf so ring and conf can't set.")
        exit(1)
    if not data_loaded['swift']:
        logging.info("mrbench - Error there isn't any item in swift section (mrbench.conf) so ring and conf can't set.")
        print(f"Error there isn't any item in \033[91mswift\033[0m section (mrbench.conf) so ring and conf can't set.")
        exit(1)
    
    futures = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for key,value in data_loaded['swift'].items():
            container_name = key
            user = value['ssh_user']
            ip = value['ip_swift']
            port = value['ssh_port']
            key_to_extract = "com.docker.compose.project.working_dir"
            # run in multithread 
            future = executor.submit(conf_ring_thread, swift_configs, port, user, ip, container_name, key_to_extract)
            futures.append(future)
        for future in concurrent.futures.as_completed(futures):
            try:
                ring_dict = future.result()
            except Exception as exc:
                print(f"Task generated an exception: {exc}")
    return ring_dict

def submit(workload_config_path, output_path):
    logging.info("mrbench - Executing submit function")
    if not os.path.exists(output_path):
       os.makedirs(output_path) 
    print("")
    run_pre_test_process = subprocess.run(f"bash {pre_test_script}", shell=True)
    cosbenchBin = shutil.which("cosbench")
    if not(cosbenchBin):
        logging.info("mrbench - Command 'cosbench' not found")
        print("Command 'cosbench' not found, but can be add with:\n\n\t ln -s {cosbench-dir}/cli.sh /usr/bin/cosbench\n")
        return None, None, -1
    archive_path = os.readlink(cosbenchBin).split("cli.sh")[0]+"archive/"
    if os.path.exists(workload_config_path):
        print(f"{YELLOW}========================================{RESET}")
        print("Sending workload ...")
        active_workload = 1
        while active_workload:
            cosbench_check_workload = subprocess.run(['cosbench', 'info'], capture_output=True, text=True).stdout
            pattern = r'(w\d+)\s+.*'
            match = re.search(pattern, cosbench_check_workload)
            if match:
                logging.info(f"mrbench - You have actived workload so new workload can't run")
                print(f"\033[91mYou have actived workload so new workload can't run\033[0m")
                print("")                      
                w_id = match.group(1)
                print(f"Do you want to cancel the current {w_id} workload? (yes/no): ", end='', flush=True)
                # Set up a timer for 20 seconds
                rlist, _, _ = select.select([sys.stdin], [], [], 20)
                if rlist:
                    response = input().lower() 
                    if response in ('y', 'yes'):
                        response = 'yes'
                    elif response in ('n', 'no'):
                        response = 'no'
                else:
                    response = "yes"
                if response == 'yes':
                    cosbench_cancel_workload = subprocess.run(["cosbench", "cancel", w_id], capture_output=True, text=True)
                    if cosbench_cancel_workload.returncode == 0:
                        logging.info(f"mrbench - user cancel this workload manually: {w_id}")
                        print(f"Workload {w_id} canceled and new workload starting please wait ...")
                        time.sleep(10)
                        submit(workload_config_path, output_path)
                return None, None, -1
            else:
                active_workload = 0
        # Start workload
        logging.info(f"mrbench - this workload send to cosbench: {workload_config_path}")
        Cos_bench_command = subprocess.run(["cosbench", "submit", workload_config_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if Cos_bench_command.returncode == 1:
            logging.info(f"mrbench - Starting workload failed: {workload_config_path}")
            print(f"Starting workload failed: \033[91m{workload_config_path}\033[0m")
            return None, None, -1
        # Extract ID of workload
        output_lines = Cos_bench_command.stdout.splitlines()
        workload_id_regex = re.search('(?<=ID:\s)(w\d+)', output_lines[0])
        workload_name = workload_config_path.split('/')[-1].replace('.xml','')
        if workload_id_regex:
            workload_id = workload_id_regex.group()
            logging.info(f"mrbench - Workload Info - ID: {workload_id} Name: {workload_name}")
            print(f"\033[1mWorkload Info:\033[0m ID: {workload_id} Name: {workload_name}")
        else:
            logging.info(f"mrbench - Starting workload failed: {workload_config_path}")
            print(f"Starting workload failed: \033[91m{workload_config_path}\033[0m")
            return None, None, -1
        # Check every second if the workload has ended or not
        archive_file_path = f"{archive_path}{workload_id}-swift-sample"
        time.sleep(5)
        while True:
            active_workload_check = subprocess.run(['cosbench', 'info'], capture_output=True, text=True)
            if "Total: 0 active workloads" in active_workload_check.stdout:
                time.sleep(5) 
                break
        if os.path.exists(archive_file_path):
            archive_workload_dir_name = f"{workload_id}-swift-sample"  
            cosbench_data = save_cosinfo(f"{archive_path}{archive_workload_dir_name}/{archive_workload_dir_name}.csv")
            if cosbench_data and cosbench_data['start_time'] and cosbench_data['end_time']:
                test_time_dir = f"{cosbench_data['start_time']}_{cosbench_data['end_time']}"
                result_path = os.path.join(output_path, test_time_dir.replace(" ","_"))
                if not os.path.exists(result_path):
                    os.mkdir(result_path) 
                print(f"Result Path: {result_path}")
                cosbench_info_result = subprocess.run(f"cosbench info > {result_path}/cosbench.info", shell=True, capture_output=True, text=True)
                copy_bench_files(archive_path, archive_workload_dir_name, result_path)
                return  cosbench_data, result_path
        else:
            logging.info(f"mrbench - Test: {workload_name} can't run correctly so archive path {archive_file_path} doesn't exists.")
            print(f"\033[91mTest: {workload_name} can't run correctly so archive path {archive_file_path} doesn't exists.\033[0m")
            return None, None, -1
    else:
        logging.info(f"mrbench - WARNING: workload file doesn't exist: {workload_config_path}")
        print(f"\033[91mWARNING: workload file doesn't exist: {workload_config_path}\033[0m")

def save_cosinfo(file):
    logging.info("mrbench - Executing save_time function")
    cosbench_data = {'start_time': None,'end_time': None,'throughput': None,'bandwidth': None,'avg_restime': None}
    try:
        # Find start of first main and end of last main
        with open(file, 'r') as csv_file:
            reader = csv.reader(csv_file)
            first_main_launching_time = None
            last_main_completed_time = None
            for row in reader:
                if row and row[0].endswith('main'):
                    if first_main_launching_time is None:
                        if len(row) > 24:
                            first_main_launching_time = row[21]
                            last_main_completed_time = row[24]
                            cosbench_data['throughput'] = row[13]
                            cosbench_data['bandwidth'] = row[14]
                            cosbench_data['avg_restime'] = row[5]
                            if first_main_launching_time and last_main_completed_time:
                                cosbench_data['start_time'] = first_main_launching_time.split('@')[1].strip()
                                cosbench_data['end_time'] = last_main_completed_time.split('@')[1].strip()
                                if cosbench_data['start_time'] and cosbench_data['end_time']:
                                    print(f"Start & End Time: {cosbench_data['start_time']},{cosbench_data['end_time']}")
                                    logging.info(f"mrbench - test time range: {cosbench_data['start_time']},{cosbench_data['end_time']}")
                                    return cosbench_data
                                else:
                                    logging.info(f"mrbench - can't extract test time range from cosbench csv file!")
                                    print("\033[91m mrbench can't extract test time range from cosbench csv file!\033[0m")
                                    exit()
                        else:
                            logging.info(f"mrbench - your workload template is not correct so mrbench can't extract test time range from cosbench csv file: {file}")
                            print("\033[91myour workload template is not correct so mrbench can't extract test time range from cosbench csv file!\033[0m")
                            exit()
    except Exception as e:
        print(f"\033[91mAn error occurred: {str(e)}\033[0m")
        return -1

def copy_bench_files(archive_path, archive_workload_dir_name, result_path):
    logging.info("mrbench - Executing copy_bench_files function")
    time.sleep(5)
    copylistfiles = ["/workload.log","/workload-config.xml",'/'+ archive_workload_dir_name + '.csv']
    print("Copying Cosbench source files ...")
    for fileName in copylistfiles:
        logging.info(f"mrbench - copy cosbench result file: {fileName}")
        archive_file_path = archive_path + archive_workload_dir_name + fileName
        retry=3
        while retry>0:
            try:
                shutil.copy2(archive_file_path, result_path + fileName)
                break # Exit the loop if copying is successful
            except Exception as e:
                print(f"\033[91mAn error occurred: {e}\033[0m")
                # Sleep for a short duration before retrying
            time.sleep(1)
            retry-=1
        if retry == 0 :
            print(f"\033[91mMaximum retries reached ({retry}). File {archive_file_path} copy failed.\033[0m")
  
def main(workload_config_path, output_path, swift_configs):
    log_level = load_config(config_file)['log'].get('level')
    if log_level is not None:
        log_level_upper = log_level.upper()
        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if log_level_upper in valid_log_levels:
            log_dir = f"sudo mkdir {log_path} > /dev/null 2>&1 && sudo chmod -R 777 {log_path}"
            logging.basicConfig(filename= f'{log_path}all.log', level=log_level_upper, format='%(asctime)s - %(levelname)s - %(message)s')
        else:
            print(f"\033[91mInvalid log level:{log_level}\033[0m")  
    else:
        print(f"\033[91mPlease enter log_level in the configuration file.\033[0m")
    logging.info("\033[92m****** mrbench main function start ******\033[0m")
    ring_dict = {}
    cosbench_data = {}
    if swift_configs:
        ring_dict = copy_swift_conf(swift_configs)
    if workload_config_path is not None:
        if os.path.exists(workload_config_path):
            if output_path is not None:
                cosbench_data, result_path = submit(workload_config_path, output_path)
                if ring_dict or cosbench_data and not os.path.exists(f"{result_path}/info.yaml"):
                    cosinfo = {}
                    cosinfo['run_time'] = f"{cosbench_data['start_time'].replace(' ','_')}_{cosbench_data['end_time'].replace(' ','_')}"
                    cosinfo['throughput'] = f"{cosbench_data['throughput']}"
                    cosinfo['bandwidth'] = f"{cosbench_data['bandwidth']}"
                    cosinfo['avg_res_time'] = f"{cosbench_data['avg_restime']}"
                    cosinfo_data = {'cosbench': cosinfo}
                    logging.info(f"mrbench - main: making info.yaml file")
                    with open(os.path.join(result_path, 'info.yaml'), 'w') as yaml_file:
                        yaml.dump(cosinfo_data, yaml_file, default_flow_style=False)
                    ring_item = {}
                    for rkey,rvalue in ring_dict.items(): 
                        ring_item[rkey+"_nodes"]=len(set([v.split()[3] for v in rvalue.splitlines()[6:]]))
                        ring_item.update({"Ring."+rkey+"."+item.split(" ")[1]:int(float(item.split(" ")[0])) for item in rvalue.splitlines()[1].split(", ")[:5]})
                    ring_formated = {'ring': ring_item}
                    with open(os.path.join(result_path, 'info.yaml'), 'a') as yaml_file:
                        yaml.dump(ring_formated, yaml_file, default_flow_style=False)
                return cosbench_data, result_path
            else:
                print(f"\033[91mWARNING: output dir doesn't define !\033[0m")
        else:
            print(f"\033[91mWARNING: workload file doesn't exist !\033[0m")
    logging.info("\033[92m****** mrbench main function end ******\033[0m")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Monster Benchmark')
    parser.add_argument('-i', '--input', help='Input file path')
    parser.add_argument('-o', '--output', help='Output directory')
    parser.add_argument('-cr', '--conf_and_ring', help='ring directory')
    args = parser.parse_args()
    swift_configs = {}
    if args.conf_and_ring:
        for filename in os.listdir(args.conf_and_ring):
            swift_configs[filename] = os.path.join(args.conf_and_ring, filename)
    main(workload_config_path=args.input, output_path=args.output, swift_configs=swift_configs)
