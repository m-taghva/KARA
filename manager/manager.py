import sys
import os
import select
import subprocess
import time
import yaml
import shutil
import argparse
import logging
import json
from datetime import datetime
from glob import glob
import mrbench
import config_gen
import status_reporter
import monstaver
import analyzer
report_path = os.path.abspath("./../report_recorder/")
if report_path not in sys.path:
    sys.path.append(report_path)
import report_recorder
pywiki_path = os.path.abspath("./../report_recorder/pywikibot/")
if pywiki_path not in sys.path:
    sys.path.append(pywiki_path)

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
    input_files = config_params.get('conf_templates', [])
    config_output = config_params.get('output_path')
    while True:
        if not os.path.exists(config_output):
            os.makedirs(config_output)
        if os.listdir(config_output):
            print(f"Output directory {config_output} is not empty and includes these files and directories:")
            for item in os.listdir(config_output):
                logging.info(f"manager - config_gen_agent: dir and file in {config_output}: {item}")
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
                logging.info(f"manager - config_gen_agent: user do not enter any answer so current files inside {config_output} moved to : {destination_dir}")
                os.makedirs(destination_dir)
                for item in os.listdir(config_output):
                    item_path = os.path.join(config_output, item)
                    shutil.move(item_path, destination_dir)
                response = "yes" # If no input after 30 seconds, consider it as "yes"
            if response == 'yes':
                logging.info("manager - config_gen_agent: answer to remove request is YES")
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
            logging.info(f"manager - config_gen_agent: input_files : {input_file}")
            firstConfNumber = 1
            # Create output directory for each input file
            workloads_configs = os.path.join(config_output, os.path.basename(input_file).split('__')[0])
            logging.debug(f"manager - config_gen_agent: path to output : {workloads_configs}")
            if os.path.isdir(workloads_configs):
                firstConfNumber = len(os.listdir(workloads_configs))+1
                logging.debug(f"manager - config_gen_agent: firstConfNumber : {firstConfNumber}")
            config_gen.main(input_file_path=input_file, output_directory=workloads_configs, conf_num=firstConfNumber)
        else:
            print(f"this template doesn't exist: \033[91m{input_file}\033[0m")
            exit()
    return config_output

def mrbench_agent(config_params, config_file, config_output):
    all_start_times = [] ; all_end_times = []
    result_dir = config_params.get('output_path')
    run_status_reporter = config_params.get('Status_Reporter', None)
    run_monstaver = config_params.get('monstaver', None)
    ring_dirs = config_params.get('ring_dirs', [])
    logging.info(f"manager - mrbench_agent: ring directories: {ring_dirs}")
    while True:
        if not os.path.exists(result_dir):
            os.makedirs(result_dir)
        if os.listdir(result_dir):
            print(f"Results directory {result_dir} is not empty and includes these files and directories:")
            for item in os.listdir(result_dir):
                logging.info(f"manager - mrbench_agent: dir and file in {result_dir}: {item}")
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
                logging.info(f"manager - mrbench_agent: user do not enter any answer so current files inside {result_dir} moved to : {destination_dir_results}")
                os.makedirs(destination_dir_results)
                for item in os.listdir(result_dir):
                    item_path = os.path.join(result_dir, item)
                    shutil.move(item_path, destination_dir_results)
                response = "yes" # If no input after 30 seconds, consider it as "yes"
            if response == 'yes':
                logging.info("manager - mrbench_agent: answer to remove request is YES")
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
    # make empty dir for merging csv
    if not os.path.exists(f"{result_dir}/analyzed/"):
        make_analyzed_dir = subprocess.run(f"sudo mkdir {result_dir}/analyzed/ > /dev/null 2>&1", shell=True)
        logging.info(f"manager - mrbench_agent: analyzed dir made {result_dir}/analyzed/")
    if config_output is None:
        if(config_params.get('conf_dir')):
            config_output = config_params.get('conf_dir')
        else:
            logging.critical("manager - mrbench_agent: There isn't any conf_dir in scenario file")
            print(f"\033[91mThere isn't any conf_dir in scenario file !\033[0m")
            exit()
    conf_dict = {}
    for dir_name in os.listdir(config_output):
        dir_path = os.path.join(config_output, dir_name)
        conf_dict[dir_name] = dir_path
    logging.debug(f"manager - mrbench_agent: conf_dict: {conf_dict}")
    conf_exist = 0
    swift_configs = {}
    if conf_dict["workloads.xml"] is None:
        logging.critical("manager - mrbench_agent: There isn't any workload in mrbench_agent input config dictionary")
        print(f"\033[91mThere isn't any workload !\033[0m")
        exit()
    if len(conf_dict)>1:
        conf_exist = 1
    ring_exist = 0
    total_ring_index = 1
    if len(ring_dirs):
        total_ring_index = len(ring_dirs)
        logging.debug(f"manager - mrbench_agent: total_ring_index {total_ring_index}")
        ring_exist = 1
    for ri in range(total_ring_index):
        swift_rings = {}
        if ring_exist:
            for filename in os.listdir(ring_dirs[ri]):
                file_path = os.path.join(ring_dirs[ri], filename)
                swift_rings[filename] = file_path
                logging.debug(f"manager - mrbench_agent: swift_rings {swift_rings}")
        Total_index = 1
        for key in conf_dict:
            if key != "workloads.xml" and key is not None and os.listdir(conf_dict[key]):
                Total_index *=len(os.listdir(conf_dict[key]))
                logging.debug(f"manager - mrbench_agent: Total_index {Total_index}")
                swift_configs[key]=""
        for i in range(Total_index):
            if conf_exist:
                m=1
                for key in swift_configs:
                    list_dir = sorted(os.listdir(conf_dict[key]))
                    swift_configs[key] = os.path.join(config_output,key,list_dir[(i//m)%len(list_dir)])
                    logging.debug(f"manager - mrbench_agent: swift_configs {swift_configs}")
                    m *= len(list_dir)
            if conf_exist or ring_exist:
                merged_conf_ring = {**swift_rings, **swift_configs}
                logging.info(f"manager - mrbench_agent: rings and configs dictionary is : {merged_conf_ring}")
                ring_dict = mrbench.copy_swift_conf(merged_conf_ring) 
                time.sleep(20)
            for test_config in sorted(os.listdir(conf_dict["workloads.xml"])):
                test_config_path = os.path.join(conf_dict["workloads.xml"], test_config)
                logging.info(f"manager - mrbench_agent: test config path in mrbench_agent submit function is : {test_config_path}")
                start_time, end_time, result_path = mrbench.submit(test_config_path, result_dir)
                logging.info(f"manager - mrbench_agent: result_path of mrbench_agent submit function is: {result_path}")
                logging.info(f"manager - mrbench_agent: start time and end time of test in mrbench_agent submit function is: {start_time},{end_time}")
                subprocess.run(f"sudo cp -r {test_config_path} {result_path}", shell=True)
                if '#' in test_config or ':' in test_config:
                    logging.info(f"manager - mrbench_agent: making info.yaml file")
                    data_time = {'Time': f"{start_time.replace(' ','_')}_{end_time.replace(' ','_')}"}
                    with open(os.path.join(result_path, 'info.yaml'), 'w') as yaml_file:
                        yaml.dump(data_time, yaml_file, default_flow_style=False)
                    data_swift = {}
                    if conf_exist:
                        subprocess.run(f"sudo cp -r {swift_configs[key]} {result_path}", shell=True)
                        for key in swift_configs:
                            swift_keys = []
                            swift_values = []
                            swift_pairs = os.path.basename(swift_configs[key]).split('#')
                            key_split = key.split('.')[0]
                            for swift_pair in swift_pairs:
                                if ':' in swift_pair:
                                    swift_keys.append(swift_pair.split(':')[0])
                                    swift_values.append(swift_pair.split(':')[1])
                                    data_swift[key_split] = dict(zip(swift_keys,swift_values))
                        with open(os.path.join(result_path, 'info.yaml'), 'a') as yaml_file:
                            yaml.dump(data_swift, yaml_file, default_flow_style=False)
                        logging.debug(f"manager - mrbench_agent: data_swift {data_swift}")
                    data_workload = {}
                    test_keys = []
                    test_values = []
                    test_pairs = test_config.split('#')
                    for test_pair in test_pairs:
                        if ':' in test_pair:
                            test_pair_split = test_pair.split(':')
                            test_keys.append(test_pair_split[0])
                            test_values.append(test_pair_split[1])
                    data_workload['workload'] = dict(zip(test_keys, test_values))
                    with open(os.path.join(result_path, 'info.yaml'), 'a') as yaml_file:
                        yaml.dump(data_workload, yaml_file, default_flow_style=False)
                    logging.debug(f"manager - mrbench_agent: data_workload {data_workload}")
                    data = {**data_time, **data_swift, **data_workload}
                if ring_exist:
                    data_ring = {'ring': ring_dict}
                    subprocess.run(f"sudo cp -r {swift_rings[filename]} {result_path}", shell=True)
                    with open(os.path.join(result_path, 'ring-info.yaml'), 'w') as yaml_file:
                        yaml.dump(data_ring, yaml_file, default_flow_style=False)
                    ring_item = {}
                    for rkey,rvalue in ring_dict.items(): 
                        ring_item[rkey+"_nodes"]=len(set([v.split()[3] for v in rvalue.splitlines()[6:]]))
                        ring_item.update({"Ring."+rkey+"."+item.split(" ")[1]:int(float(item.split(" ")[0])) for item in rvalue.splitlines()[1].split(", ")[:5]})
                    ring_formated = {'ring': ring_item}
                    with open(os.path.join(result_path, 'info.yaml'), 'a') as yaml_file:
                        yaml.dump(ring_formated, yaml_file, default_flow_style=False)
                    logging.debug(f"manager - mrbench_agent: ring_item {ring_item}")
                    data = {**data_time, **data_swift, **data_workload, **ring_item}
                all_start_times.append(start_time) ; all_end_times.append(end_time)
                if run_status_reporter != 'none':
                    if run_status_reporter == 'csv':
                        output_csv  = status_reporter.main(metric_file=None, path_dir=result_path, time_range=f"{start_time},{end_time}", img=False)
                    if run_status_reporter == 'csv,img':
                        output_csv = status_reporter.main(metric_file=None, path_dir=result_path, time_range=f"{start_time},{end_time}", img=True)
                    if os.path.exists(output_csv): 
                        formatted_data = {}
                        for section_name, section_data in data.items():
                            if isinstance(section_data, dict):
                                for name, val in section_data.items():
                                    formatted_data[f"{section_name}.{name}"] = val
                            else:
                                formatted_data[section_name] = section_data
                        logging.debug(f"manager - mrbench_agent: formatted_data for merged csv {formatted_data}")
                        analyzer.merge_csv(csv_file=output_csv, output_directory=f"{result_dir}/analyzed", pairs_dict=formatted_data)
                if run_monstaver != 'none':
                    if run_monstaver == 'backup,info':
                        backup_to_report = monstaver.main(time_range=f"{start_time},{end_time}", inputs=[result_path,config_file,kara_config_files], delete=False, backup_restore=None, hardware_info=None, software_info=None, swift_info=None, influx_backup=True)
                    if run_monstaver == 'backup':
                        monstaver.main(time_range=f"{start_time},{end_time}", inputs=[result_path,config_file,kara_config_files], delete=True, backup_restore=None, hardware_info=False, software_info=False, swift_info=False, influx_backup=None)
                    if run_monstaver == 'info':
                        backup_to_report = monstaver.main(time_range=f"{start_time},{end_time}", inputs=[result_path,config_file,kara_config_files], delete=False, backup_restore=None, hardware_info=None, software_info=None, swift_info=None, influx_backup=False)
                else:
                    backup_to_report = None
    # Extract first start time and last end time
    first_start_time = all_start_times[0] ; last_end_time = all_end_times[-1]
    logging.debug(f"manager - mrbench_agent: first_start_time,last_end_time: {first_start_time},{last_end_time}")
    logging.debug(f"manager - mrbench_agent: backup_to_report: {backup_to_report}")
    return first_start_time, last_end_time, backup_to_report, result_dir

def status_reporter_agent(config_params):
    result_dir = config_params.get('output_path')
    times_file = config_params.get('times')
    image_generate = config_params.get('image', False)
    if times_file:
       with open(times_file, 'r') as file:
            times = file.readlines()
            for time_range in times:
                logging.debug(f"manager - status_reporter_agent: time is {time_range}")
                start_time, end_time = time_range.strip().split(',')
                output_csv = status_reporter.main(path_dir=result_dir, time_range=f"{start_time},{end_time}", img=image_generate)
    logging.debug(f"manager - status_reporter_agent: result dir: {result_dir}")
    return result_dir

def monstaver_agent(config_params, config_file, first_start_time, last_end_time):
    operation = config_params.get('operation')
    batch_mode = config_params.get('batch_mode', False)
    times_file = config_params.get('times')
    input_path = config_params.get('input_path')
    backup_to_report = None
    if times_file:
       with open(times_file, 'r') as file:
            times = file.readlines()
            for time_range in times:
                logging.debug(f"manager - monstaver_agent: time range is {time_range}")
                start_time, end_time = time_range.strip().split(',')
                if operation == "backup,info":
                    backup_to_report = monstaver.main(time_range=f"{start_time},{end_time}", inputs=[input_path,config_file,kara_config_files], delete=False,  backup_restore=None, hardware_info=None, software_info=None, swift_info=None, influx_backup=True)
                elif operation == 'backup':
                    monstaver.main(time_range=f"{start_time},{end_time}", inputs=[input_path,config_file,kara_config_files], delete=True, backup_restore=None, hardware_info=False, software_info=False, swift_info=False, influx_backup=True)
                elif operation == 'info':
                    backup_to_report = monstaver.main(time_range=f"{start_time},{end_time}", inputs=[input_path,config_file,kara_config_files], delete=False, backup_restore=None, hardware_info=None, software_info=None, swift_info=None, influx_backup=False)
                elif operation == "restore":
                    monstaver.main(time_range=None, inputs=None, delete=None, backup_restore=True, hardware_info=False, software_info=False, swift_info=False, influx_backup=False)
    elif batch_mode:
        if operation == "backup,info":
           backup_to_report = monstaver.main(time_range=f"{first_start_time},{last_end_time}", inputs=[input_path,config_file,kara_config_files], delete=False,  backup_restore=None, hardware_info=None, software_info=None, swift_info=None, influx_backup=True)
        elif operation == 'backup':
            monstaver.main(time_range=f"{first_start_time},{last_end_time}", inputs=[input_path,config_file,kara_config_files], delete=True, backup_restore=None, hardware_info=False, software_info=False, swift_info=False, influx_backup=True)
        elif operation == 'info':
            backup_to_report = monstaver.main(time_range=f"{first_start_time},{last_end_time}", inputs=[input_path,config_file,kara_config_files], delete=False, backup_restore=None, hardware_info=None, software_info=None, swift_info=None, influx_backup=False)
    elif operation == "restore":
        monstaver.main(time_range=None, inputs=None, delete=None, backup_restore=True, hardware_info=False, software_info=False, swift_info=False, influx_backup=False)
    if backup_to_report is not None:
       logging.debug(f"manager - monstaver_agent: backup_to_report: {backup_to_report}")
       return backup_to_report, input_path

def status_analyzer_agent(config_params):
    result_dir = config_params.get('input_path')
    merge = config_params.get('merge', True)
    merge_csv = config_params.get('merge_csv')
    analyze = config_params.get('analyze', True)
    analyze_csv = config_params.get('analyze_csv')
    transform_dir = config_params.get('transform')
    if merge:
        analyzer.main(merge=True, analyze=False, graph=False, csv_original=None, transformation_directory=None, output_directory=result_dir, selected_csv=merge_csv, x_column=None, y_column=None)
        time.sleep(10)
    if analyze:
        analyzer.main(merge=False, analyze=True, graph=False, csv_original=analyze_csv, transformation_directory=transform_dir, output_directory=None, selected_csv=None, x_column=None, y_column=None)

def report_recorder_agent(config_params, backup_to_report, result_dir):
    if not os.path.exists(f"./user-config.py"):
        print(f"\033[91muser-config.py is required for run report_recorder\033[0m")
        exit(1)
    create_html = config_params.get('create_html', True)
    html_templates_path = config_params.get('html_templates_path')
    output_path = config_params.get('output_path')
    upload_to_kateb = config_params.get('upload_to_kateb', True)
    cluster_name = config_params.get('cluster_name')
    scenario_name = config_params.get('scenario_name')
    if backup_to_report is None:
        backup_to_report = config_params.get('configs_dir')
    if result_dir is None:
        result_dir = "./../results"
    # for HW report
    report_recorder.main(input_template=f"{html_templates_path}/hardware.html", htmls_path=output_path, cluster_name=cluster_name, scenario_name=scenario_name, configs_directory=backup_to_report, upload_operation=upload_to_kateb, create_html_operation=create_html, merged_file=None, merged_info_file=None, all_test_dir=None)
    # for SW report
    report_recorder.main(input_template=f"{html_templates_path}/software.html", htmls_path=output_path, cluster_name=cluster_name, scenario_name=scenario_name, configs_directory=backup_to_report, upload_operation=upload_to_kateb, create_html_operation=create_html, merged_file=None, merged_info_file=None, all_test_dir=None) 
    # for test report
    report_recorder.main(input_template=None, htmls_path=output_path, cluster_name=cluster_name, scenario_name=scenario_name, configs_directory=None, upload_operation=upload_to_kateb, create_html_operation=create_html, merged_file=f"{result_dir}/analyzed/merged.csv", merged_info_file=f"{result_dir}/analyzed/merged_info.csv", all_test_dir=result_dir)
   
def main(config_file):
    log_level = load_config(config_file)['log'].get('level')
    if log_level is not None:
        log_level_upper = log_level.upper()
        if log_level_upper == "DEBUG" or log_level_upper == "INFO" or log_level_upper == "WARNING" or log_level_upper == "ERROR" or log_level_upper == "CRITICAL":
            log_dir = f"sudo mkdir /var/log/kara/ > /dev/null 2>&1 && sudo chmod -R 777 /var/log/kara/"
            log_dir_run = subprocess.run(log_dir, shell=True)
            logging.basicConfig(filename= '/var/log/kara/all.log', level=log_level_upper, format='%(asctime)s - %(levelname)s - %(message)s')
        else:
            print(f"\033[91mInvalid log level:{log_level}\033[0m")
    else:
        print(f"\033[91mPlease enter log_level in the configuration file.\033[0m")

    logging.info("****** Manager_main function start ******")
    data_loaded = load_config(config_file)
    if 'scenario' in data_loaded:
        config_output = None
        first_start_time = None
        last_end_time = None
        backup_to_report = None
        result_dir = None
        for task in data_loaded['scenario']:
            try:
                if 'Config_gen' in task:
                    config_params = task['Config_gen']
                    logging.info("**manager - main: Executing config_gen_agent function**")
                    config_output = config_gen_agent(config_params)
                elif 'Mrbench' in task:
                    config_params = task['Mrbench']
                    logging.info("**manager - main: Executing mrbench_agent function**")
                    first_start_time, last_end_time, backup_to_report, result_dir = mrbench_agent(config_params, config_file, config_output)
                elif 'Status-Reporter' in task:
                    config_params = task['Status-Reporter']
                    logging.info("**manager - main: Executing status_reporter_agent function**")
                    result_dir = status_reporter_agent(config_params)
                elif 'Monstaver' in task:
                    config_params = task['Monstaver']
                    logging.info("**manager - main: Executing monstaver_agent function**")
                    backup_to_report, input_path = monstaver_agent(config_params, config_file, first_start_time, last_end_time)
                elif 'Status_Analyzer' in task:
                    config_params = task['Status_Analyzer']
                    logging.info("**manager - main: Executing status_analyzer_agent function**")
                    status_analyzer_agent(config_params)
                elif 'Report_Recorder' in task:
                    config_params = task['Report_Recorder']
                    logging.info("**manager - main: Executing report_recorder_agent function**")
                    report_recorder_agent(config_params, backup_to_report, result_dir)
                else:
                    print(f"Unknown task: {task}")
            except Exception as e:
                print(f"Error executing task: {task}. Error: {str(e)}")
    else:
        print(f"\033[91mNo scenario found in the configuration file.\033[0m")
    logging.info("****** Manager_main function end ******")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='kara tools manager')
    parser.add_argument('-sn', '--scenario_name', help='input scenario path')
    args = parser.parse_args()
    config_file = args.scenario_name
    main(config_file)
