import sys
import os
import subprocess
import time
import yaml
import argparse
import mrbench
import config_gen
import status_reporter
import monstaver
import analyzer

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
    for input_file in input_files:
        # Create output directory for each input file
        workloads_configs = os.path.join(config_output, os.path.basename(input_file))
        config_gen.main(input_file, workloads_configs)
    return config_output

def mrbench_agent(config_params, config_output):
    all_start_times = [] ; all_end_times = []
    result_dir = config_params.get('output_path')
    run_status_reporter = config_params.get('Status_Reporter', False)
    image_generate = config_params.get('image_generate', False)
    run_monstaver = config_params.get('monstaver', False)
    ring_dirs = config_params.get('ring_dirs', [])
    if config_output is None:
        if(config_params.get('conf_dir')):
            config_output = config_params.get('conf_dir')
        else:
            print(f"\033[91mThere isn't any conf_dir in scenario file !\033[0m")
            exit()
    else:
        conf_dict = {}  
        for dir_name in os.listdir(config_output):
            dir_path = os.path.join(config_output, dir_name)
            conf_dict[dir_name] = dir_path
        Total_index = 1
        conf_exist = 0
        swift_rings = {}
        swift_configs = {}
        if conf_dict["workloads.xml"] is None:
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
                if key != "workloads.xml" and key is not None:
                    Total_index *=len(os.listdir(conf_dict[key]))
                    swift_configs[key]=""
            for i in range(Total_index):
                if conf_exist:
                    m=1
                    for key in swift_configs:
                        list_dir = os.listdir(conf_dict[key])
                        swift_configs[key] = os.path.join(config_output,key,list_dir[(i//m)%len(list_dir)])
                        m *= len(list_dir)
                    merged_conf_ring = {**swift_rings, **swift_configs}
                    mrbench.copy_swift_conf(merged_conf_ring)
                    time.sleep(40)
                for test_config in sorted(os.listdir(conf_dict["workloads.xml"])):
                    test_config_path = os.path.join(conf_dict["workloads.xml"], test_config)
                    start_time, end_time, result_file_path = mrbench.submit(test_config_path, result_dir)
                    all_start_times.append(start_time) ; all_end_times.append(end_time)
                    if run_status_reporter:
                        status_reporter.main(path_dir=result_file_path, time_range=f"{start_time},{end_time}", img=image_generate)  
                    if run_monstaver:
                        monstaver.main(time_range=f"{start_time},{end_time}", inputs=[result_file_path], delete=True, backup_restore=None) 
    
    # Extract first start time and last end time
    first_start_time = all_start_times[0] ; last_end_time = all_end_times[-1] 
    return first_start_time, last_end_time

def monstaver_agent(config_params, first_start_time, last_end_time):
    operation = config_params.get('operation')
    batch_mode = config_params.get('batch_mode', False)
    times_file = config_params.get('times')
    input_path = config_params.get('input_path')
    if times_file:
       with open(times_file, 'r') as file:
            times = file.readlines()
            for time_range in times:
                start_time, end_time = time_range.strip().split(',')
                if operation == "backup":
                    monstaver.main(time_range=f"{start_time},{end_time}", inputs=[input_path], delete=True,  backup_restore=None)
                elif operation == "restore":
                    monstaver.main(time_range=None, inputs=None, delete=None, backup_restore=True)          
    elif operation == "backup": 
        if batch_mode:
            monstaver.main(time_range=f"{first_start_time},{last_end_time}", inputs=[input_path], delete=True, backup_restore=None)
    elif operation == "restore":
        monstaver.main(time_range=None, inputs=None, delete=None, backup_restore=True)

def status_reporter_agent(config_params):
    result_dir = config_params.get('output_path')
    times_file = config_params.get('times')
    image_generate = config_params.get('image_generate', False)
    if times_file:
       with open(times_file, 'r') as file:
            times = file.readlines()
            for time_range in times:
                start_time, end_time = time_range.strip().split(',')
                status_reporter.main(path_dir=result_dir, time_range=f"{start_time},{end_time}", img=image_generate)

def status_analyzer_agent(config_params):
    result_dir = config_params.get('input_path')
    merge = config_params.get('merge', False)
    merge_csv = config_params.get('merge_csv')
    analyze = config_params.get('analyze', False)
    analyze_csv = config_params.get('analyze_csv')
    transform_dir = config_params.get('transform')
    if merge:
        analyzer.main_merge(input_directory=result_dir, selected_csv=merge_csv)
        time.sleep(10)
    if analyze:
        analyzer.main_analyze(csv_original=f"{result_dir}/{analyze_csv}", transformation_directory=transform_dir)

def report_recorder_agent(config_params):
    input_template = config_params.get('input_template')
    output_html = config_params.get('output_html')
    kateb_title = config_params.get('kateb_title')
    pybot = f"python3 ./../../pywikibot/report_recorder.py -it {input_template} -oh {output_html} -kt {kateb_title}"
    subprocess.call(pybot, shell=True)

def main():
    data_loaded = load_config(config_file)
    if 'scenario' in data_loaded:
        config_gen_output = None
        first_start_time = None
        last_end_time = None
        for task in data_loaded['scenario']:            
            try:
                if 'Config_gen' in task:
                    config_params = task['Config_gen']
                    config_gen_output = config_gen_agent(config_params)
                elif 'Mrbench' in task:
                    config_params = task['Mrbench']
                    first_start_time, last_end_time = mrbench_agent(config_params, config_gen_output)
                elif 'Status-Reporter' in task:
                    config_params = task['Status-Reporter']
                    status_reporter_agent(config_params)
                elif 'Monstaver' in task:
                    config_params = task['Monstaver']
                    monstaver_agent(config_params, first_start_time, last_end_time)
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='kara tools manager')
    parser.add_argument('-sn', '--scenario_name', help='input scenario path')
    args = parser.parse_args()
    config_file = args.scenario_name
    main()
