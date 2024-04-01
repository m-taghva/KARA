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

config_file = "/etc/KARA/mrbench.conf"
pre_test_script = "./../mrbench/pre_test_script.sh"

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

def copy_swift_conf(swift_configs):
    data_loaded = load_config(config_file)
    for key,value in data_loaded['swift'].items():
        container_name = key
        user = value['ssh_user']
        ip = value['ip_swift']
        port = value['ssh_port']
        key_to_extract = "com.docker.compose.project.working_dir"
        all_scp_file_successful = False
        # Run the docker inspect command and capture the output
        inspect_command = f"ssh -p {port} {user}@{ip} docker inspect {container_name}"
        inspect_result = subprocess.run(inspect_command, shell=True, capture_output=True, text=True)
        if inspect_result.returncode == 0:
            # Parse the JSON output
            container_info = json.loads(inspect_result.stdout)
            # Check if the key exists in the JSON structure
            if key_to_extract in container_info[0]['Config']['Labels']:
                inspect_value = container_info[0]['Config']['Labels'][key_to_extract]
                for filename, filepath in swift_configs.items(): 
                    each_scp_successful = False 
                    if filename.endswith(".gz"):
                        diff_ring_command = f"ssh -p {port} {user}@{ip} 'cat {inspect_value}/rings/{filename}' | diff - {filepath}"
                        diff_ring_result = subprocess.run(diff_ring_command, shell=True, capture_output=True, text=True)
                        print("")
                        print(f"please wait for checking ring file [ {filename} ] inside {container_name}")
                        if diff_ring_result.stderr == "":
                            if diff_ring_result.stdout != "":
                                copy_ring_command = f"scp -r -P {port} {filepath} {user}@{ip}:{inspect_value}/rings > /dev/null 2>&1"
                                copy_ring_process = subprocess.run(copy_ring_command, shell=True)
                                if copy_ring_process.returncode == 0:
                                    each_scp_successful = True
                                    print("")
                                    print(f"\033[92mcopy ring file [ {filename} ] to {container_name} successful\033[0m")
                                else: 
                                    print(f"\033[91mrings in {container_name} failed to sync\033[0m")
                        elif diff_ring_result.stderr != "":
                            print("")
                            print(f"\033[91mWARNING: your ring file naming is wrong [ {filename} ] or not exist inside {container_name}\033[0m")
                    elif filename.endswith(".conf"):
                        diff_conf_command = f"ssh -p {port} {user}@{ip} 'cat {inspect_value}/{filename}' | diff - {filepath}"
                        diff_conf_result = subprocess.run(diff_conf_command, shell=True, capture_output=True, text=True)
                        print("")
                        print(f"please wait for checking config file [ {filename} ] inside {container_name}")
                        if diff_conf_result.stderr == "":
                            if diff_conf_result.stdout != "":
                                copy_conf_command = f"scp -r -P {port} {filepath} {user}@{ip}:{inspect_value}/ > /dev/null 2>&1"
                                copy_conf_process = subprocess.run(copy_conf_command, shell=True)
                                if copy_conf_process.returncode == 0:
                                    each_scp_successful = True
                                    print("")
                                    print(f"\033[92mcopy config file [ {filename} ] to {container_name} successful\033[0m")
                                    base_name_changer = os.path.basename(filepath)
                                    name_changer = f"ssh -p {port} {user}@{ip} mv {inspect_value}/{base_name_changer} {inspect_value}/{filename} > /dev/null 2>&1" 
                                    name_changer_process = subprocess.run(name_changer, shell=True)
                                else:
                                    print(f"\033[91mconfigs in {container_name} failed to sync\033[0m")
                        elif diff_conf_result.stderr != "":
                            print("")
                            print(f"\033[91mWARNING: your config file naming is wrong [ {filename} ] or not exist inside {container_name}\033[0m")
                    if each_scp_successful: 
                        all_scp_file_successful = True  
        else:
            print("")
            print(f"\033[91mWARNING: there is a problem in your config file for SSH info inside \033[0m'\033[92m{container_name}\033[0m' \033[91msection so mrbench can't sync config and ring files !\033[0m") 
            print("")
            if inspect_result.stdout == '[]\n':
                print(f"\033[91mWARNING: your container name \033[0m'\033[92m{container_name}\033[0m' \033[91mis wrong !\033[0m")
            print("")
            print(f"{YELLOW}========================================{RESET}")

        if all_scp_file_successful is True:
            restart_cont_command = f"ssh -p {port} {user}@{ip} docker restart {container_name} > /dev/null 2>&1"
            restart_cont_command_process = subprocess.run(restart_cont_command, shell=True)
            if restart_cont_command_process.returncode == 0:
                print("")
                print(f"\033[92mcontainer {container_name} successfully restart\033[0m")
            else:
                print(f"\033[91mcontainer {container_name} failed to reatsrt\033[0m") 
       
def submit(workload_config_path, output_path):
    if not os.path.exists(output_path):
       os.makedirs(output_path) 
    run_pre_test_process = subprocess.run(f"bash {pre_test_script}", shell=True)
    cosbenchBin = shutil.which("cosbench")
    if not(cosbenchBin):
        print("Command 'cosbench' not found, but can be add with:\n\n\t ln -s {cosbench-dir}/cli.sh /usr/bin/cosbench\n")
        return None, None, -1
    archive_path = os.readlink(cosbenchBin).split("cli.sh")[0]+"archive/"
    if os.path.exists(workload_config_path):
        print("Sending workload ...")
        # Start workload
        cosbench_active_workload = subprocess.run(['cosbench', 'info'], capture_output=True, text=True)
        if "Total: 0 active workloads" in cosbench_active_workload.stdout:
            Cos_bench_command = subprocess.run(["cosbench", "submit", workload_config_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            if Cos_bench_command.returncode == 1:
                print("\033[91mStarting workload failed.\033[0m")
                return None, None, -1
            # Extract ID of workload
            output_lines = Cos_bench_command.stdout.splitlines()
            workload_id_regex = re.search('(?<=ID:\s)(w\d+)', output_lines[0])
            workload_name = workload_config_path.split('/')[-1].replace('.xml','')
            if workload_id_regex:
                workload_id = workload_id_regex.group()
                print(f"\033[1mWorkload Info:\033[0m ID: {workload_id} Name: {workload_name}")
            else:
                print("\033[91mStarting workload failed.\033[0m")
                return None, None, -1
            # Check every second if the workload has ended or not
            archive_file_path = f"{archive_path}{workload_id}-swift-sample"
            while True:
                if os.path.exists(archive_file_path):
                    time.sleep(5) 
                    break
                time.sleep(5)
            result_path = create_test_dir(output_path, workload_name)
            archive_workload_dir_name = f"{workload_id}-swift-sample"
            print(f"Result Path: {result_path}")
            cosbench_info = f"cosbench info > {result_path}/cosbench.info"
            cosbench_info_result = subprocess.run(cosbench_info, shell=True, capture_output=True, text=True)
            # run other functions 
            start_time, end_time = save_time(f"{archive_path}{archive_workload_dir_name}/{archive_workload_dir_name}.csv", result_path)
            copy_bench_files(archive_path, archive_workload_dir_name, result_path)
            return  start_time, end_time, result_path
        else:
            print(f"\033[91mYou have actived workload so new workload can't run\033[0m")
            return None, None, -1
    else:
        print(f"\033[91mWARNING: workload file doesn't exist !\033[0m")

def create_test_dir(result_path, workload_name):
    result_file_path = os.path.join(result_path, workload_name)
    if os.path.exists(result_file_path):
        i = 1
        while os.path.exists(result_file_path + f"_{i}"):
            i += 1
        result_file_path += f"_{i}"
    os.mkdir(result_file_path)
    return result_file_path

def save_time(file, result_path):
    start_time = None
    end_time = None
    try:
        # Find start of first main and end of last main
        with open(file, 'r') as csv_file:
            reader = csv.reader(csv_file)
            first_main_launching_time = None
            last_main_completed_time = None
            for row in reader:
                if row and row[0].endswith('main'):
                    if first_main_launching_time is None:
                        first_main_launching_time = row[21]
                        last_main_completed_time = row[24]
        if first_main_launching_time and last_main_completed_time:
            start_time = first_main_launching_time.split('@')[1].strip()
            end_time = last_main_completed_time.split('@')[1].strip()
            time_file = open(f"{result_path}/time", "w")
            start_end_time = f"{start_time},{end_time}"
            time_file.write(start_end_time)
            time_file.close()
            #return start_time,end_time
            print(f"Start Time: {start_time}")
            print(f"End Time: {end_time}")     
        return start_time, end_time        
    except Exception as e:
        print(f"\033[91mAn error occurred: {str(e)}\033[0m")
        return -1

def copy_bench_files(archive_path, archive_workload_dir_name, result_path):
    time.sleep(5)
    copylistfiles = ["/workload.log","/workload-config.xml",'/'+ archive_workload_dir_name + '.csv']
    print("Copying Cosbench source files ...")
    for fileName in copylistfiles:
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
    if swift_configs:
       copy_swift_conf(swift_configs)

    if os.path.exists(workload_config_path):
        if output_path is not None:
            start_time, end_time, result_file_path = submit(workload_config_path, output_path)
            return start_time, end_time, result_file_path  
        else:
            print(f"\033[91mWARNING: output dir doesn't define !\033[0m")
    else:
        print(f"\033[91mWARNING: workload file doesn't exist !\033[0m")

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
