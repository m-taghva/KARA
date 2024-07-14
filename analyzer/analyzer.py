import os
import subprocess
import logging
import argparse
from glob import glob
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter

BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[1;33m"

def conf_dir(config_dir):
    global configs_dir
    configs_dir = config_dir
    return configs_dir

# read backup dir
listOfServers = []
def load(directory):
    with open(configs_dir + directory, 'r') as f:
        content = f.readlines()
    return content

#### HARDWARE info ####
# dmidecode -t 1
def generate_brand_model(serverName):
    manufacturer = ""
    productName = ""
    for line in load(f'/configs/{serverName}'+"/hardware/server-manufacturer/dmidecode.txt"):
        if "Manufacturer" in line:
            manufacturer = line.split(":")[1].replace("\n" , "")
        if "Product Name" in line:
            productName = line.split(":")[1].replace("\n" , "")
    return manufacturer + productName

# lscpu
def generate_cpu_model(serverName):
    coresPerSocket = ""
    socket = ""
    threads = ""
    model = ""
    for line in load(f'/configs/{serverName}' + "/hardware/cpu/lscpu.txt"):
        line = line.replace("\n","").split(":")
        if "Core(s) per socket" in line[0]:
            coresPerSocket=line[1].strip()
            #print ("("+  coresPerSocket+ ")")
        if "Socket(s)" in line[0]:
            socket=line[1].strip()
        if "Thread(s) per core" in line[0]:
            threads = line[1].strip()
        if "Model name" in line[0]:
            model = line[1].strip()
    return coresPerSocket + "xcores x " + socket + "xsockets x " + threads + "xthreads " + model

# lshw -short -C memory
def generate_memory_model(serverName):
    rams=[]
    for line in load(f'/configs/{serverName}'+"/hardware/memory/lshw-brief.txt"):
        line = line.replace("  ", "")
        if "DIMM" in line:
            if "empty" not in line:
                model = line.split("memory ")[1]
                rams.append(model)
    counts = Counter(rams)
    ram = ""
    for item , count in counts.items():
        ram+= str(count) + "x" + item
    return ram

# lshw -json -C net
def generate_net_model(serverName):
    Flag = False
    nets=[]
    capacities = []
    for line in load(f'/configs/{serverName}'+"/hardware/net/lshw-json.txt"):
        line = line.replace(",\n" , "")
        if "id" in line:
            Flag = True
        if Flag is True:
            if "product" in line:
                nets.append( line.split(":")[1].replace("" , ""))
            if "capacity" in line:
                capacities.append(line.split(":")[1].replace("000000000" , "")+"Gbit/s")
                Flag = False
    netModel=[]
    for i in range(len(nets)):
        if i < len(capacities):
            netModel.append(capacities[i] + " " + nets[i])
        else:
            netModel.append(nets[i])
    counts = Counter(netModel)
    net = ""
    for item, count in counts.items():
        net += str(count) + "x" + item + "\n"
    return net

# dmidecode -t 2
def generate_motherboard_model(serverName):
    manufacturer = ""
    productName = ""
    for line in load(f'/configs/{serverName}'+"/hardware/motherboard/dmidecode.txt"):
        if "Manufacturer" in line:
            manufacturer = line.split(":")[1].replace("\n", "")
        if "Product Name" in line:
            productName = line.split(":")[1].replace("\n", "")
    return manufacturer + productName

# lshw -C disk
def generate_disk_model(serverName):
    disks= []
    with open(f'{configs_dir}/configs/{serverName}'+"/hardware/disk/lshw.txt",'r') as f:
        diskList = f.read().split("*-")
    for i in range (1,len(diskList)):
        if not("size:" in diskList[i]):
            continue 
        diskname=""
        for x in diskList[i].splitlines():
            if "description:" in x or "product:" in x:
                diskname+=x.split(":")[1].strip() + " "
            elif "size:" in x:
                diskname+=x.split("(")[1].split(")")[0] + " "
        disks.append(diskname)
    counts = Counter(disks)
    disksNames =""
    for item, count in counts.items():
        disksNames += str(count) + "x" + item + "\n"
    return disksNames

def generate_model(server, part, spec):
    if part == "hardware":
        if spec == "cpu":
            return generate_cpu_model(server)
        elif spec == "memory":
            return generate_memory_model(server)
        elif spec == "net":
            return generate_net_model(server)
        elif spec == "motherboard":
            return generate_motherboard_model(server)
        elif spec == "brand":
            return generate_brand_model(server)
        elif spec == "disk":
            return generate_disk_model(server)
    elif part == "software":
        return "software not configed"
    
def compare(part, spec):
    listOfServers = get_list_of_servers()
    dict = {}
    for server in listOfServers:
        model= generate_model(server ,part ,spec)
        if model in dict:
            if dict[model] is None:
                dict[model] = []
        else: dict[model]= []
        dict[model].append(server)
    return dict

#### SOFTWARE info ####
def get_list_of_servers():
    cmd = ["ls", f'{configs_dir}/configs/']
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    global listOfServers
    listOfServers = result.stdout.split("\n")
    listOfServers.pop()
    return listOfServers

def compare_confs(confsOfServers):
    commonConf = confsOfServers[listOfServers[0]]
    allConfs = {}
    for server in listOfServers:
        commonConf = set(commonConf) & set(confsOfServers[server])
    for server in listOfServers:
        uncommonconfs = set(confsOfServers[server]) - commonConf
        if len(uncommonconfs) != 0:
            allConfs[server] = uncommonconfs
    if len(commonConf) != 0:
        allConfs["All(common confs)"] = commonConf
    return allConfs  #### dict of list of strings

def generate_swift_status(servername):
    listOfDowns = []
    for line in load(f"/configs/{servername}/software/swift/services/{servername}-swift-status.txt"):
        if "No" in line:
            listOfDowns.append(line.split("No ")[1].replace("\n" , "").split(" running")[0])
    return listOfDowns

def generate_all_swift_status(services):
    listOfServices = []
    if services == "main":
        listOfServices= ["proxy-server" , "object-server" , "account-server" , "container-server"]
    if services == "object":
        listOfServices = ["object-auditor" , "object-reconstructor" , "object-replicator" , "object-updater" , "object-expirer"]
    if services == "account":
        listOfServices = ["account-replicator" , "account-auditor"  , "account-reaper"]
    if services == "container":
        listOfServices = ["container-updater" , "container-auditor" , "container-replicator" , "container-sharder" , "container-sync"]
    returndict={}
    returndict ["servers"] = listOfServices
    for server in listOfServers:
        returndict[server] = []
        listOfDownServices = generate_swift_status(server)
        for service in listOfServices:
            if service in listOfDownServices:
                returndict[server].append( "Down" ) ##### returndict[server].append([service , "Down"])
            else:
                returndict[server].append( "UP" ) #### returndict[server].append([service , "UP"])
    return returndict  #### dict of list of stirng

def generate_ring(servername):
    x = {}
    for i in ["object", "account", "container"]:
        with open(configs_dir+"/configs/"+servername+"/software/swift/rings/"+servername+"-" +i+"-ring.txt", "r") as file:
            x[i] = file.read()
    ring_item_dic = {}
    ring_item = []
    for key, value in x.items():
        ring_item_dic["Ring." + key + ".nodes"] = len(set([v.split()[3] for v in value.splitlines()[6:]]))
        ring_item_dic.update({"Ring." + key + "." + item.split(" ")[1]:int(float(item.split(" ")[0])) for item in value.splitlines()[1].split(", ")[:5]})
    for rkey , rvalue in ring_item_dic.items():
        ring_item.append(rkey + " = " + str(rvalue))
    return ring_item

def get_conf(server, confType, serverType = None):
    conf = []
    if confType == "server_confs":
        conf = [i for i in load("/configs/"+ server + "/software/swift/server-confs/" + server + "-" + serverType + "-server.conf" ) if "#" not in i]
    if confType == "software_version":
        conf= [i.replace("\n", "") for i in load("/configs/"+ server + "/software/system/images-version.txt")]
    if confType == "sysctl":
        conf = [i.replace("\n" , "") for i in load ("/configs/"+ server + "/software/system/sysctl.txt")]
    if confType == "systemctl":
        conf = [" ".join(i.replace("  " , "").split(" ")[:3]) for i in load ("configs/"+ server + "/software/system/systemctl.txt")]
    if confType == "lsof":
        conf = [i.replace("\n" , "") for i in load ("/configs/"+ server + "/software/system/lsof.txt")]
    if confType == "lsmod":
        conf = [i.replace("  ", " ").replace("\n", "") for i in load("/configs/"+ server + "/software/system/lsmod.txt")]
    if confType == "rings":
        conf = generate_ring(server)
    return conf

def generate_confs(confType, serverType = None):
    confOfServers = {}
    for server in listOfServers:
        confOfServers[server] = get_conf(server, confType , serverType)
    compared_dict = compare_confs(confOfServers)
    compared_dict ["servers"] = confType
    return compared_dict

####### MERGER #######
def merge_csv(csv_file, output_directory, pairs_dict):
    logging.info("status_analyzer - Executing merge_csv function")
    try:
        csv_data = pd.read_csv(csv_file)
        if pairs_dict:  
            if os.path.exists(f'{output_directory}/merged_info.csv'):
                merged_info = pd.concat([pd.read_csv(f'{output_directory}/merged_info.csv'), pd.DataFrame(pairs_dict, index=[0])], ignore_index=True)
            else:
                merged_info = pd.DataFrame(pairs_dict, index=[0])
            merged_info.to_csv(f'{output_directory}/merged_info.csv', index=False, mode='w')
            for key, value in pairs_dict.items():
                csv_data.insert(0, key, value) 
        if os.path.exists(f'{output_directory}/merged.csv'):
            merged = pd.concat([pd.read_csv(f'{output_directory}/merged.csv'), csv_data], ignore_index=True)
        else:
            merged = csv_data
        merged.to_csv(f'{output_directory}/merged.csv', index=False, mode='w')
        print(f"Data from '{csv_file}' appended successfully to {YELLOW}'{output_directory}/merged.csv'{RESET}") 
        logging.info(f"status_analyzer - Data from '{csv_file}' appended successfully to '{output_directory}/merged.csv'") 
    except FileNotFoundError:
        logging.info(f"status_analyzer - File '{csv_file}' not found. Skipping")
        print(f"File '{csv_file}' not found. Skipping...")

def merge_process(output_directory, selected_csv):
    logging.info("status_analyzer - Executing merge_process function")
    if '*' in selected_csv:    
        selected_csv = glob(selected_csv)
        for file in selected_csv:
            merge_csv(file, output_directory, pairs_dict=None)
    else:
        for file in selected_csv:
            if os.path.exists(file):
                merge_csv(file, output_directory, pairs_dict=None)
            else:
                print(f"\033[91mThis CSV file doesn't exist:\033[0m{file}")
                logging.info(f"status_analyzer - This CSV file doesn't exist:{file}")
                exit(1)
                
####### ANALYZER #######
def read_txt_file(file_path):
    logging.info("status_analyzer - Executing read_txt_file function")
    with open(file_path, 'r') as txt_file:
        operation, new_column_name = txt_file.readline().strip().split(':')
        selected_columns = [line.strip() for line in txt_file.readlines()]
    return operation, new_column_name, selected_columns

def process_csv_file(csv_data, operation, new_column_name, selected_columns):
    logging.info("Executing status_analyzer process_csv_file function")
    if operation == 'sum':
        new_column_name = f"sum.{new_column_name}"
        csv_data[new_column_name] = csv_data[selected_columns].sum(axis=1)
    elif operation == 'avg':
        new_column_name = f"avg.{new_column_name}"
        csv_data[new_column_name] = csv_data[selected_columns].mean(axis=1)
    return csv_data

def analyze_and_save_csv(csv_original, transformation_directory):
    logging.info("status_analyzer - Executing analyze_and_save_csv function")
    csv_intermediate = pd.read_csv(csv_original)
    selected_column_names = set()
    for txt_file in os.listdir(transformation_directory):
        if txt_file.startswith('t') and txt_file.endswith('.txt'):
            txt_file_path = os.path.join(transformation_directory, txt_file)
            operation, new_column_name, selected_columns = read_txt_file(txt_file_path)
            csv_intermediate = process_csv_file(csv_intermediate, operation, new_column_name, selected_columns)
            selected_column_names.update(selected_columns)
    keep_columns = [col for col in csv_intermediate.columns if col not in selected_column_names]
    csv_final = csv_intermediate[keep_columns]
    final_output_csv_name = f"{os.path.splitext(os.path.basename(csv_original))[0]}-{os.path.basename(transformation_directory)}.csv"
    final_output_csv_path = os.path.join(os.path.dirname(csv_original), final_output_csv_name)
    csv_final.to_csv(final_output_csv_path, index=False)
    print(f"\n{BOLD}Analyzed CSV file:{RESET}{YELLOW} '{final_output_csv_path}' {RESET}{BOLD}has been created with the extracted values.{RESET}\n")
    intermediate_csv_path = os.path.join(os.path.dirname(csv_original), "intermediate.csv")
    if os.path.exists(intermediate_csv_path):
        os.remove(intermediate_csv_path)

###### Make graph and image ######
def plot_and_save_graph(selected_csv, x_column, y_column):
    logging.info("status_analyzer - Executing plot_and_save_graph function")
    # Read CSV file into a DataFrame
    data = pd.read_csv(selected_csv)
    # Extract x and y values from DataFrame
    x_values = data[x_column]
    y_values = data[y_column]
    # Plot the data
    plt.plot(x_values, y_values, marker='o')
    # Set plot labels and title
    plt.xlabel(x_column)
    plt.ylabel(y_column)
    file_name = os.path.basename(selected_csv)
    time_of_graph = file_name.replace('.csv','')
    title = f'Time of Report: {time_of_graph}'
    plt.title(title)
    # Save the plot as an image in the same directory as the CSV file
    image_file_path = selected_csv.replace('.csv', '_graph.png')
    plt.savefig(image_file_path)

def main(merge, analyze, graph, csv_original, transformation_directory, output_directory, selected_csv, x_column, y_column):
    log_dir = f"sudo mkdir /var/log/kara/ > /dev/null 2>&1 && sudo chmod -R 777 /var/log/kara/"
    log_dir_run = subprocess.run(log_dir, shell=True)
    logging.basicConfig(filename= '/var/log/kara/all.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("\033[92m****** status_analyzer main function start ******\033[0m")
    if analyze:
        analyze_and_save_csv(csv_original, transformation_directory)
    if merge:
        if not os.path.exists(output_directory):
            os.makedirs(output_directory) 
        merge_process(output_directory, selected_csv)
    if graph:
        plot_and_save_graph(selected_csv, x_column, y_column)
    logging.info("\033[92m****** status_analyzer main function end ******\033[0m")
           
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Perform CSV operations and merge files.')
    parser.add_argument('-M', '--merge', action='store_true', help='Merge CSV files')
    parser.add_argument('-o', '--output_directory', help='Path to the directory containing CSV files or output for merged csv file (required for -M)')
    parser.add_argument('-sc', '--selected_csv', help='Name of the selected CSV files or "*.csv" (required for -M)')
    parser.add_argument('-A', '--analyze', action='store_true', help='Analyze CSV files')
    parser.add_argument('-c', '--csv_org', help='Custom CSV file for analysis (required for -A)')
    parser.add_argument('-t', '--transformation_directory', help='Path to transformation directory (required for -A)')
    parser.add_argument('-G', '--graph', action='store_true', help='make graph of CSV file')
    parser.add_argument('-x', '--x_column', type=str, help='Name of the X column (required for -G)')
    parser.add_argument('-y', '--y_column', type=str, help='Name of the Y column (required for -G)')
    args = parser.parse_args()
    
    # Check required arguments based on operation
    if args.merge and (args.output_directory is None or args.selected_csv is None):
        print("Error: Both -o (--input_directory) and -sc (--selected_csv) switches are required for merge operation -M")
        exit(1)
    if args.analyze and (args.csv_org is None or args.transformation_directory is None):
        print("Error: Both -c (--csv_org) and -t (--transformation_directory) switches are required for analyze operation -A")
        exit(1)
    if args.graph and (args.x_column is None or args.y_column is None or args.selected_csv is None):
        print("Error: these switch -x (--x_column) and -y (--y_column) and sc (--selected_csv) are required for make graph operation -G")
        exit(1)

    # Set values to None if not provided
    merge = args.merge ; analyze = args.analyze ; graph = args.graph
    x_column = args.x_column ; y_column = args.y_column
    transformation_directory = args.transformation_directory.strip() if args.transformation_directory else None
    csv_original = args.csv_org.strip() if args.csv_org else None
    output_directory = args.output_directory.strip() if args.output_directory else None
    selected_csv = args.selected_csv if args.selected_csv else None
    if merge:
        if selected_csv:
            if '*' in selected_csv:
                selected_csv = args.selected_csv.strip()
            else:
                selected_csv = args.selected_csv.split(',')         
        else:
            selected_csv = None
            print(f'\033[91mplease select correct csv file your file is wrong: {args.selected_csv}\033[0m')
            exit(1)
            
    main(merge, analyze, graph, csv_original, transformation_directory, output_directory, selected_csv, x_column, y_column)
