import os
import json
import subprocess
import sys
from datetime import datetime , timedelta
import argparse
import yaml
import logging
import pytz
# For font style
BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[1;33m"

config_file = "/etc/KARA/status.conf"

def load_config(config_file):
    with open(config_file, "r") as stream:
        try:
            data_loaded = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"Error loading the configuration: {exc}")
            sys.exit(1)
    return data_loaded

# Function to convert "now-nh" format to timestamp
def parse_time(tehran_timestamp):
    if tehran_timestamp.startswith("now-") and tehran_timestamp.endswith("h"):
        try:
            hours = int(tehran_timestamp.split("-")[1][:-1])
            now_time_subtract = datetime.now() - timedelta(hours=hours) 
            now_time_timestamp = int(now_time_subtract.timestamp())
            return now_time_timestamp
        except ValueError:
            print("\033[91mInvalid time range format. Expected format: 'now-nh' where n is a number\033[0m") 
            exit()          
    else:
        print("\033[91mInvalid time range format. Expected format: 'now-nh' where n is a number\033[0m")
        exit()

# Function to convert Tehran timestamp to UTC
def convert_tehran_to_utc(tehran_timestamp, add_seconds):
    if tehran_timestamp.startswith("now-") and tehran_timestamp.endswith("h"):
        now_time_result = parse_time(tehran_timestamp)
        timesamp_time_add = now_time_result + add_seconds
        utc_now_time_result = datetime.utcfromtimestamp(timesamp_time_add).strftime("%Y-%m-%dT%H:%M:%SZ")
        return utc_now_time_result
    elif not tehran_timestamp.startswith("now-") and not tehran_timestamp.endswith("h"):
        tehran_timestamp_convert = int(datetime.strptime(tehran_timestamp, "%Y-%m-%d %H:%M:%S").timestamp())
        timestamp_add = tehran_timestamp_convert + add_seconds
        utc_timestamp_result = datetime.utcfromtimestamp(timestamp_add).strftime("%Y-%m-%dT%H:%M:%SZ")
        return utc_timestamp_result
    else:
        print("\033[91mInvalid time range format. Expected format: 'now-nh' where n is a number or time stamp format (Y-M-D H:M:S) for start and end time !\033[0m")
        exit()

# Function to extract metrics from files
def get_metrics_from_file(metric_file_path):
    logging.info("Executing status reporter get_metrics_from_file function")
    metrics = []
    with open(metric_file_path, 'r') as f:
        metrics = [metric.strip() for metric in f if metric.strip() and not metric.strip().startswith('#')]
    return metrics
                            
def main(metric_file, path_dir, time_range, img=False):
    log_level = load_config(config_file)['log'].get('level')
    if log_level is not None:
        log_level_upper = log_level.upper()
        if log_level_upper == "DEBUG" or "INFO" or "WARNING" or "ERROR" or "CRITICAL":
            os.makedirs('/var/log/kara/', exist_ok=True)
            logging.basicConfig(filename= '/var/log/kara/all.log', level=log_level_upper, format='%(asctime)s - %(levelname)s - %(message)s')
        else:
            print(f"\033[91mInvalid log level:{log_level}\033[0m")  
    else:
        print(f"\033[91mPlease enter log_level in the configuration file.\033[0m")

    logging.info("\033[92m****** status reporter main function start ******\033[0m")   
    metric_file= metric_file.split(',') if metric_file else []
    path_dir= path_dir if path_dir else "." 
    time_range = time_range if time_range else load_config(config_file).get('time', [])['time_range']
    # Load configuration from config file
    data_loaded = load_config(config_file)
    time_section = data_loaded.get('time', {})
    START_TIME_SUM = time_section.get('start_time_sum')
    END_TIME_SUBTRACT = time_section.get('end_time_subtract')
    TIME_GROUP = time_section.get('time_group')

    print("")
    print(f"{YELLOW}========================================{RESET}")
    print("") 
    
    # Create the output parent directory
    output_parent_dir= os.path.join(path_dir, "query_results")
    os.makedirs(output_parent_dir, exist_ok=True)
    # Split time_range and generate output_csv
    time_range_parts = time_range.split(',')
    start_time, end_time = time_range_parts[0], time_range_parts[1]
    if start_time.startswith("now-"):
        tehran_tz = pytz.timezone('Asia/Tehran')
        start_time_utc_csv = convert_tehran_to_utc(start_time, START_TIME_SUM) ; end_time_utc_csv = convert_tehran_to_utc(end_time, -END_TIME_SUBTRACT)
        utc_datetime_start = datetime.strptime(start_time_utc_csv, "%Y-%m-%dT%H:%M:%SZ") ; utc_datetime_end = datetime.strptime(end_time_utc_csv, "%Y-%m-%dT%H:%M:%SZ")
        start_timestamp = utc_datetime_start.replace(tzinfo=pytz.utc).astimezone(tehran_tz)
        end_timestamp = utc_datetime_end.replace(tzinfo=pytz.utc).astimezone(tehran_tz)
        start_timestamp_csv = start_timestamp.strftime("%Y-%m-%d %H:%M:%S") ; end_timestamp_csv = end_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        start_time_name = start_timestamp_csv.replace(" ", "-") ; end_time_name = end_timestamp_csv.replace(" ", "-")
        output_csv = os.path.join(output_parent_dir, f"{start_time_name}_{end_time_name}.csv")
    else:
        start_time_csv = start_time.replace(" ", "-")
        end_time_csv = end_time.replace(" ", "-")
        output_csv = os.path.join(output_parent_dir, f"{start_time_csv}_{end_time_csv}.csv")
    if os.path.exists(output_csv):
        os.remove(output_csv)
    # Generate metric_operation_mapping
    metric_operation_mapping = {}
    metric_operations = []
    if metric_file:
        # Extract metric operations from file names in the command-line argument
        metric_operations = [os.path.basename(metric_file).split('_')[0] for metric_file in metric_file]
        metric_operation_mapping = dict(zip(metric_file, metric_operations))
    else:
        # Read metric file paths and operations from the configuration file
        for metric_operation, metric_file in data_loaded.get('metrics', {}).items():
            metric_operations.append(metric_operation)
            metric_files_config = [metric_file.get('path', '')]
            metric_operation_mapping[metric_file.get('path', '')] = metric_operation

    output_csv_str = ["Host_alias"]  # name of the first column in csv
    csvi = 0
    # Loop through each combination of time range, host, IP, PORT, and execute the curl command
    for mc_server, config in data_loaded.get('influxdbs', {}).items():
        ip = config.get('ip')
        influx_port = config.get('influx_port')
        for db_name, db_data in config.get('databases', {}).items():
            hostls = db_data.get('hostls', {})
            for host_name, alias in hostls.items():
                alias = alias if alias and len(alias) > 1 else host_name
                start_time_utc = convert_tehran_to_utc(start_time, START_TIME_SUM)
                end_time_utc = convert_tehran_to_utc(end_time, -END_TIME_SUBTRACT)
                logging.info(f"status_reporter - start time of query in utc format: {start_time_utc}") ; logging.info(f"status_reporter - end time of query in utc format: {end_time_utc}")
                output_csv_str.append(alias)  # value inside the first column of csv
                csvi += 1
                for metric_file, metric_operation in metric_operation_mapping.items():
                    if os.path.isfile(metric_file):
                        metrics = get_metrics_from_file(metric_file)
                        for metric_name in metrics:
                            metric_name = metric_name.strip()
                            if csvi == 1:
                                metric_name = metric_name.replace(" ", "")
                                output_csv_str[0] += f",{metric_operation}_{metric_name.replace('netdata.', '')}"
                            # Construct the curl command for query 1
                            query1_curl_command = f'curl -sG "http://{ip}:{influx_port}/query" --data-urlencode "db={db_name}" --data-urlencode "q=SELECT {metric_operation}(\\"value\\") FROM \\"{metric_name}\\" WHERE (\\"host\\" =~ /^{host_name}$/) AND time >= \'{start_time_utc}\' AND time <= \'{end_time_utc}\' fill(none)"'
                            query_result = subprocess.getoutput(query1_curl_command)
                            if query_result:
                                values = json.loads(query_result).get('results', [{}])[0].get('series', [{}])[0].get('values', [])
                                values = [str(v[1]) for v in values]
                                output_csv_str[csvi] += "," + ",".join(values)
                                if values:
                                    print(f"{BOLD}Add this metric to CSV: {metric_name}{RESET}")
                                    # Construct the curl command for query 2
                                    if img:
                                        logging.info(f"status_reporter - user need image and graph")
                                        query2_curl_command = f'curl -sG "http://{ip}:{influx_port}/query" --data-urlencode "db={db_name}" --data-urlencode "q=SELECT {metric_operation}(\\"value\\") FROM /{metric_name}/ WHERE (\\"host\\" =~ /^{host_name}$/) AND time >= \'{start_time_utc}\' AND time <= \'{end_time_utc}\' GROUP BY time({TIME_GROUP}s) fill(none)"'
                                        query2_output = subprocess.getoutput(query2_curl_command)
                                        os.system(f"python3 ./../status_reporter/image_renderer.py '{query2_output}' '{host_name}' '{path_dir}'")
                                else:
                                    # check database name
                                    check_database_name = f'curl -sG "http://{ip}:{influx_port}/query" --data-urlencode "q=SHOW DATABASES"'
                                    check_database_name_result = subprocess.getoutput(check_database_name)
                                    db_json_data = json.loads(check_database_name_result)
                                    databases = [db[0] for db in db_json_data["results"][0]["series"][0]["values"]]
                                    if db_name in databases:
                                        logging.info(f"status_reporter - The database {db_name} is exist in {ip}")
                                        print(f"The database {db_name} is exist in {ip}")
                                        # check metric name
                                        check_metric_name = f'curl -sG "http://{ip}:{influx_port}/query" --data-urlencode "q=SHOW MEASUREMENTS ON {db_name} WITH MEASUREMENT =~ /{metric_name}/"'
                                        check_metric_name_result = subprocess.getoutput(check_metric_name)
                                        metric_json_data = json.loads(check_metric_name_result)
                                        if "series" in metric_json_data["results"][0]:
                                            logging.info(f"status_reporter - metric {metric_name} is exist in {db_name}")
                                            print(f"metric {metric_name} is exist in {db_name}")
                                            # check host name
                                            check_host_name = f'curl -sG "http://{ip}:{influx_port}/query" --data-urlencode "q=SHOW TAG VALUES ON {db_name} FROM \\"{metric_name}\\" WITH KEY = \\"host\\""'
                                            check_host_name_result = subprocess.getoutput(check_host_name)
                                            host_json_data = json.loads(check_host_name_result)
                                            if "series" in host_json_data["results"][0]:
                                                host_names = [item[1] for item in host_json_data["results"][0]["series"][0]["values"]]
                                                if host_name in host_names:
                                                     # check time range
                                                    logging.error(f"status_reporter - database name: {db_name}, metric name: {metric_name}, host name: {host_name} are correct but your TIME RANGE doesn't have any value")
                                                    print(f"database name: {db_name}, metric name: {metric_name}, host name: {host_name} are correct but \033[91myour TIME RANGE doesn't have any value !\033[0m")
                                                else:
                                                    logging.error(f"status_reporter - The host {host_name} name is wrong")
                                                    print(f"\033[91mThe host {host_name} name is wrong\033[0m")
                                            else:
                                                    logging.error(f"status_reporter - metric: {metric_name} doesn't have host: {host_name} so value is null !")
                                                    print(f"\033[91mmetric: {metric_name} doesn't have host: {host_name} so value is null !\033[0m")
                                        else:
                                            logging.error(f"status_reporter - metric {metric_name} doesn't exist in {db_name}")
                                            print(f"\033[91mmetric {metric_name} doesn't exist in {db_name}\033[0m")
                                    else:
                                        logging.error(f"status_reporter - The database {db_name} doesn't exist in {ip}")
                                        print(f"\033[91mThe database {db_name} doesn't exist in {ip}\033[0m")
                                        exit()
                            else:
                                ping_process = subprocess.Popen(["ping", "-c", "1", ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                                ping_output, ping_error = ping_process.communicate()
                                if ping_process.returncode == 0:
                                    logging.info(f"status_reporter - Server {ip} port {influx_port} is wrong")
                                    print(f"\033[91mServer {ip} is reachable but port {influx_port} is wrong\033[0m")
                                elif ping_process.returncode == 1:
                                    logging.critical(f"status_reporter - Server {ip} is unreachable")
                                    print(f"\033[91mServer {ip} is unreachable so your IP is wrong\033[0m")
                                exit()
    # Write the CSV file for each time range
    with open(output_csv, 'a') as csv_file:
        for line in output_csv_str:
            csv_file.write(line + "\n")
    print("")
    if img:
        print(f"{BOLD}Done! Csv and Images are save in the {RESET}{YELLOW}'{output_parent_dir}'{RESET}{BOLD} directory{RESET}")
    else:
        print(f"{BOLD}Done! Csv is save in the {RESET}{YELLOW}'{output_parent_dir}'{RESET}{BOLD} directory{RESET}")
    print("")
    print(f"{YELLOW}========================================{RESET}")
    print("")
    logging.info("\033[92m****** status reporter main function end ******\033[0m")   

if __name__ == "__main__":
    # Parse command-line arguments for your new script
    parser = argparse.ArgumentParser(description="Your Script Description")
    parser.add_argument("-m", "--metric_file", help="Enter your metric files comma-separated list of metric file paths or read them from config file.")
    parser.add_argument("-o", "--path_dir", help="Enter path to the parent directory or it use current dir as default")
    parser.add_argument("-t", "--time_range", help="Enter time range in the format 'start_time,end_time' or read time range from config file")
    parser.add_argument("--img", action="store_true", help="Create images and graphs")
    args = parser.parse_args()
    # Call your main function with the provided arguments
    main(metric_file=args.metric_file, path_dir=args.path_dir, time_range=args.time_range, img=args.img)   
