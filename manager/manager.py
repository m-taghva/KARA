import sys
import os
import select
import subprocess
import time
import yaml
import csv
import shutil
import argparse
import logging
from datetime import datetime
import mrbench
import config_gen
import status_reporter
import monstaver
import analyzer

# For font style
BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[1;33m"

kara_config_files = "/etc/KARA/"

def load_config(config_file):
    with open(config_file, "r") as stream:
        try:
            data_loaded = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"Error loading the configuration: {exc}")
            sys.exit(1)
    return data_loaded

def config_gen_agent(config_params):
    logging.info("Executing config_gen_agent function")
    input_files = config_params.get('conf_templates', [])
    config_output = config_params.get('output_path')
    while True:
        if not os.path.exists(config_output):
            os.makedirs(config_output)
        if os.listdir(config_output):
            print(f"Output directory {config_output} is not empty and includes these files and directories:")
            for item in os.listdir(config_output):
                logging.info(f"dir and file in {config_output}: {item}")
                print(f"\033[91m{item}\033[0m")
            # Ask user if they want to remove the contents
            print("Do you want to remove these files and directories? (yes/no): ", end='', flush=True)
            # Set up a timer for 30 seconds
            rlist, _, _ = select.select([sys.stdin], [], [], 30)
            if rlist:
                response = input().lower() 
                if response in ('y', 'yes'):
                    response = 'yes'
                elif response in ('n', 'no'):
                    response = 'no'
            else:
                current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                destination_dir = os.path.join(os.path.dirname(os.path.dirname(config_output)), os.path.dirname(config_output)+"_"+current_time)
                logging.info(f"user do not enter any answer so current files inside {config_output} moved to : {destination_dir}")
                os.makedirs(destination_dir)
                for item in os.listdir(config_output):
                    item_path = os.path.join(config_output, item)
                    shutil.move(item_path, destination_dir)
                response = "yes" # If no input after 20 seconds, consider it as "yes"
            if response == 'yes':
                logging.info("answer to config_gen_agent remove request is YES")
                # Remove all files and directories in the output directory
                rm_config_output_dir = subprocess.run(f"sudo rm -rf {config_output}/*", shell=True)
                print("\033[92mContents removed successfully.\033[0m")
                break
            elif response == 'no':
                print("\033[1;33mLeaving existing contents untouched.\033[0m")
                break
            else:
                print("\033[91mInvalid input. Please enter 'yes' or 'no'\033[0m")
        else:
            break
    print(f"{YELLOW}========================================{RESET}")  
    for input_file in input_files:
        if os.path.exists(input_file):
            logging.info(f"config_gen_agent input_files : {input_file}")
            firstConfNumber = 1
            # Create output directory for each input file
            workloads_configs = os.path.join(config_output, os.path.basename(input_file).split('__')[0])
            logging.debug(f"path to config_gen_agent output : {workloads_configs}")
            if os.path.isdir(workloads_configs): 
                firstConfNumber = len(os.listdir(workloads_configs))+1
                logging.debug(f"config_gen_agent firstConfNumber : {firstConfNumber}")
            config_gen.main(input_file_path=input_file, output_directory=workloads_configs, conf_num=firstConfNumber)
        else:
            print(f"this template doesn't exist: \033[91m{input_file}\033[0m")
            exit()
    print(f"{YELLOW}========================================{RESET}")
    return config_output

def mrbench_agent(config_params, config_file, config_output):
    logging.info("Executing mrbench_agent function")
    all_start_times = [] ; all_end_times = []
    result_dir = config_params.get('output_path')
    run_status_reporter = config_params.get('Status_Reporter', None)
    run_monstaver = config_params.get('monstaver', None)
    ring_dirs = config_params.get('ring_dirs', [])
    logging.info(f"ring directories in mrbench_agent : {ring_dirs}")
    while True:
        if not os.path.exists(result_dir):
            os.makedirs(result_dir)
        if os.listdir(result_dir):
            print(f"Results directory {result_dir} is not empty and includes these files and directories:")
            for item in os.listdir(result_dir):
                logging.info(f"dir and file in {result_dir}: {item}")
                print(f"\033[91m{item}\033[0m")
            # Ask user if they want to remove the contents
            print("Do you want to remove these files and directories? (yes/no): ", end='', flush=True)
            # Set up a timer for 30 seconds
            rlist, _, _ = select.select([sys.stdin], [], [], 30)
            if rlist:
                response = input().lower() 
                if response in ('y', 'yes'):
                    response = 'yes'
                elif response in ('n', 'no'):
                    response = 'no'
            else:
                current_time_results = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                destination_dir_results = os.path.join(os.path.dirname(os.path.dirname(result_dir)), os.path.dirname(result_dir)+"_"+current_time_results)
                logging.info(f"user do not enter any answer so current files inside {result_dir} moved to : {destination_dir_results}")
                os.makedirs(destination_dir_results)
                for item in os.listdir(result_dir):
                    item_path = os.path.join(result_dir, item)
                    shutil.move(item_path, destination_dir_results)
                response = "yes" # If no input after 20 seconds, consider it as "yes"
            if response == 'yes':
                logging.info("answer to mrbench_agent remove request is YES")
                # Remove all files and directories in the output directory
                rm_result_dir = subprocess.run(f"sudo rm -rf {result_dir}/*", shell=True)
                print("\033[92mContents removed successfully.\033[0m")
                break
            elif response == 'no':
                print("\033[1;33mLeaving existing contents untouched.\033[0m")
                break
            else:
                print("\033[91mInvalid input. Please enter 'yes' or 'no'\033[0m")
        else:
            break 
    print(f"{YELLOW}========================================{RESET}") 
    if config_output is None:
        if(config_params.get('conf_dir')):
            config_output = config_params.get('conf_dir')
        else:
            logging.critical("There isn't any conf_dir in scenario file")
            print(f"\033[91mThere isn't any conf_dir in scenario file !\033[0m")
            exit()
    conf_dict = {}  
    for dir_name in os.listdir(config_output):
        dir_path = os.path.join(config_output, dir_name)
        conf_dict[dir_name] = dir_path
    Total_index = 1
    conf_exist = 0
    swift_rings = {}
    swift_configs = {}
    if '.xml' not in os.path.basename(dir_path):
        logging.critical("There isn't any workload in mrbench_agent input config dictionary")
        print(f"\033[91mThere isn't any workload !\033[0m")
        exit()
    if len(conf_dict)>1:
        conf_exist = 1
    ring_exist = 0
    total_ring_index = 1
    if len(ring_dirs):
        total_ring_index = len(ring_dirs)
        ring_exist = 1
    for ri in range(total_ring_index):
        if ring_exist:
            for filename in os.listdir(ring_dirs[ri]):
                file_path = os.path.join(ring_dirs[ri], filename)
                swift_rings[filename] = file_path
        for key in conf_dict:
            if key != ".xml" and key is not None and os.listdir(conf_dict[key]):
                Total_index *=len(os.listdir(conf_dict[key]))
                swift_configs[key]=""
        for i in range(Total_index):
            if conf_exist:
                m=1
                for key in swift_configs:
                    list_dir = sorted(os.listdir(conf_dict[key]))
                    swift_configs[key] = os.path.join(config_output,key,list_dir[(i//m)%len(list_dir)])
                    m *= len(list_dir)
            if conf_exist or ring_exist:
                merged_conf_ring = {**swift_rings, **swift_configs}
                logging.info(f"rings and configs dictionary is : {merged_conf_ring}")
                mrbench.copy_swift_conf(merged_conf_ring)
            for test_config in sorted(os.listdir(conf_dict["workloads.xml"])):
                test_config_path = os.path.join(conf_dict["workloads.xml"], test_config)
                logging.info(f"test config path in mrbench_agent submit function is : {test_config_path}")
                start_time, end_time, result_file_path = mrbench.submit(test_config_path, result_dir)
                copy_test_config = f"sudo cp {test_config_path} {result_file_path}"
                copy_test_config_process = subprocess.run(copy_test_config, shell=True)
                copy_ring_conf_files = f"sudo cp {swift_configs[key]} {result_file_path} && sudo cp {swift_rings[filename]} {result_file_path}"
                copy_ring_conf_files_process = subprocess.run(copy_ring_conf_files, shell=True)
                if '#' in os.path.basename(swift_configs[key]) and '#' in test_config:
                    with open(os.path.join(result_file_path, 'info.csv'), mode='w', newline='') as file:
                        writer = csv.writer(file)
                        swift_keys = []
                        swift_values = []
                        for key in swift_configs:
                            pairs = swift_configs[key].split('#')
                            for pair in pairs:
                                if ':' in pair:
                                    pair_split = pair.split(':')
                                    if len(pair_split) == 2:
                                        swift_keys.append(pair_split[0])
                                        swift_values.append(pair_split[1])  
                        test_keys = []
                        test_values = []
                        pairs = test_config.split('#')
                        for pair in pairs:
                            if ':' in pair:
                                pair_split = pair.split(':')
                                if len(pair_split) == 2:
                                    test_keys.append(pair_split[0])
                                    test_values.append(pair_split[1])
                        writer.writerow(['workload_configs'] + test_keys)
                        writer.writerow(['workload_values'] + test_values)
                        writer.writerow(['swift_configs'] + swift_keys)
                        writer.writerow(['swift_values'] + swift_values)
                all_start_times.append(start_time) ; all_end_times.append(end_time)
                if run_status_reporter is not None:
                    if run_status_reporter == 'csv':
                        status_reporter.main(metric_file=None, path_dir=result_file_path, time_range=f"{start_time},{end_time}", img=False)  
                    if run_status_reporter == 'csv,img':
                        status_reporter.main(metric_file=None, path_dir=result_file_path, time_range=f"{start_time},{end_time}", img=True) 
                if  run_monstaver is not None:
                    if run_monstaver == 'backup,info':
                        monstaver.main(time_range=f"{start_time},{end_time}", inputs=[result_file_path,config_file,kara_config_files], delete=True, backup_restore=None, hardware_info=True, os_info=True, swift_info=True, influx_backup=True) 
                    if run_monstaver == 'backup':
                        monstaver.main(time_range=f"{start_time},{end_time}", inputs=[result_file_path,config_file,kara_config_files], delete=True, backup_restore=None, hardware_info=False, os_info=False, swift_info=False, influx_backup=True) 
                    if run_monstaver == 'info':
                        monstaver.main(time_range=f"{start_time},{end_time}", inputs=[result_file_path,config_file,kara_config_files], delete=True, backup_restore=None, hardware_info=True, os_info=True, swift_info=True, influx_backup=False)
    # Extract first start time and last end time
    first_start_time = all_start_times[0] ; last_end_time = all_end_times[-1] 
    logging.debug(first_start_time,last_end_time)
    return first_start_time, last_end_time

def monstaver_agent(config_params, config_file, first_start_time, last_end_time):
    logging.info("Executing monstaver_agent function")
    operation = config_params.get('operation')
    batch_mode = config_params.get('batch_mode', False)
    times_file = config_params.get('times')
    input_path = config_params.get('input_path')
    if times_file:
       with open(times_file, 'r') as file:
            times = file.readlines()
            for time_range in times:
                start_time, end_time = time_range.strip().split(',')
                if operation == "backup,info":
                    monstaver.main(time_range=f"{start_time},{end_time}", inputs=[input_path,config_file,kara_config_files], delete=True,  backup_restore=None, hardware_info=True, os_info=True, swift_info=True, influx_backup=True)
                elif operation == 'backup':
                        monstaver.main(time_range=f"{start_time},{end_time}", inputs=[input_path,config_file,kara_config_files], delete=True, backup_restore=None, hardware_info=False, os_info=False, swift_info=False, influx_backup=True) 
                elif operation == 'info':
                        monstaver.main(time_range=f"{start_time},{end_time}", inputs=[input_path,config_file,kara_config_files], delete=True, backup_restore=None, hardware_info=True, os_info=True, swift_info=True, influx_backup=False)
                elif operation == "restore":
                    monstaver.main(time_range=None, inputs=None, delete=None, backup_restore=True)   
    elif batch_mode:       
        if operation == "backup,info":
            monstaver.main(time_range=f"{start_time},{end_time}", inputs=[input_path,config_file,kara_config_files], delete=True,  backup_restore=None, hardware_info=True, os_info=True, swift_info=True, influx_backup=True)
        elif operation == 'backup':
            monstaver.main(time_range=f"{start_time},{end_time}", inputs=[input_path,config_file,kara_config_files], delete=True, backup_restore=None, hardware_info=False, os_info=False, swift_info=False, influx_backup=True) 
        elif operation == 'info':
            monstaver.main(time_range=f"{start_time},{end_time}", inputs=[input_path,config_file,kara_config_files], delete=True, backup_restore=None, hardware_info=True, os_info=True, swift_info=True, influx_backup=False)
    elif operation == "restore":
        monstaver.main(time_range=None, inputs=None, delete=None, backup_restore=True)

def status_reporter_agent(config_params):
    logging.info("Executing status_reporter_agent function")
    result_dir = config_params.get('output_path')
    times_file = config_params.get('times')
    image_generate = config_params.get('image', False)
    if times_file:
       with open(times_file, 'r') as file:
            times = file.readlines()
            for time_range in times:
                start_time, end_time = time_range.strip().split(',')
                status_reporter.main(path_dir=result_dir, time_range=f"{start_time},{end_time}", img=image_generate)

def status_analyzer_agent(config_params):
    logging.info("Executing status_analyzer_agent function")
    result_dir = config_params.get('input_path')
    merge = config_params.get('merge', False)
    merge_csv = config_params.get('merge_csv')
    analyze = config_params.get('analyze', False)
    analyze_csv = config_params.get('analyze_csv')
    transform_dir = config_params.get('transform')
    if merge:
        analyzer.main(merge=True, io_directory=result_dir, selected_csv=merge_csv)
        time.sleep(10)
    if analyze:
        analyzer.main(analyze=True, csv_original=f"{result_dir}/{analyze_csv}", transformation_directory=transform_dir)

def report_recorder_agent(config_params):
    logging.info("Executing report_recorder_agent function")
    input_template = config_params.get('input_template')
    output_html = config_params.get('output_html')
    kateb_title = config_params.get('kateb_title')
    pybot = f"python3 ./../../pywikibot/report_recorder.py -it {input_template} -oh {output_html} -kt {kateb_title}"
    subprocess.call(pybot, shell=True)

def main(config_file):
    log_level = load_config(config_file)['log'].get('level')
    if log_level is not None:
        log_level_upper = log_level.upper()
        if log_level_upper == "DEBUG" or "INFO" or "WARNING" or "ERROR" or "CRITICAL":
            log_dir = f"sudo mkdir /var/log/kara/ > /dev/null 2>&1 && sudo chmod -R 777 /var/log/kara/"
            log_dir_run = subprocess.run(log_dir, shell=True)
            logging.basicConfig(filename= '/var/log/kara/all.log', level=log_level_upper, format='%(asctime)s - %(levelname)s - %(message)s')
        else:
            print(f"\033[91mInvalid log level:{log_level}\033[0m")  
    else:
        print(f"\033[91mPlease enter log_level in the configuration file.\033[0m")

    logging.info("\033[92m****** Manager_main function start ******\033[0m")
    data_loaded = load_config(config_file)
    if 'scenario' in data_loaded:
        config_output = None
        first_start_time = None
        last_end_time = None
        for task in data_loaded['scenario']:            
            try:
                if 'Config_gen' in task:
                    config_params = task['Config_gen']
                    config_output = config_gen_agent(config_params)
                elif 'Mrbench' in task:
                    config_params = task['Mrbench']
                    first_start_time, last_end_time = mrbench_agent(config_params, config_file, config_output)
                elif 'Status-Reporter' in task:
                    config_params = task['Status-Reporter']
                    status_reporter_agent(config_params)
                elif 'Monstaver' in task:
                    config_params = task['Monstaver']
                    monstaver_agent(config_params, config_file, first_start_time, last_end_time)
                elif 'Status_Analyzer' in task:
                    config_params = task['Status_Analyzer']
                    status_analyzer_agent(config_params)
                elif 'Report_Recorder' in task:
                    config_params = task['Report_Recorder']
                    report_recorder_agent(config_params)
                else:
                    print(f"Unknown task: {task}")
            except Exception as e:
                print(f"Error executing task: {task}. Error: {str(e)}")
    else:
        print(f"\033[91mNo scenario found in the configuration file.\033[0m")
    logging.info("\033[92m****** Manager_main function end ******\033[0m")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='kara tools manager')
    parser.add_argument('-sn', '--scenario_name', help='input scenario path')
    args = parser.parse_args()
    config_file = args.scenario_name
    main(config_file)
