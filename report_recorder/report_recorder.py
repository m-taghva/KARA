import argparse
import re
import os
from bs4 import BeautifulSoup
import logging
import csv
from collections import Counter
import subprocess
import sys
import pandas as pd
pywiki_path = os.path.abspath("./../report_recorder/pywikibot/")
if pywiki_path not in sys.path:
    sys.path.append(pywiki_path)
import pywikibot
classification_path = os.path.abspath("./../report_recorder/")
if classification_path not in sys.path:
    sys.path.append(classification_path)
import classification

# read backup dir
configs_dir = ""
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

def dict_to_html_table(data):
    logging.info("report_recorder - Executing dict_to_html_table function")
    html = "<table border='1' class='wikitable'>\n"
    #generate first row
    html += "<tr>\n"
    html += f"<td>servers</td>\n"
    if isinstance(data["servers"] , list):
        for item in data["servers"]:
            html += f"<td>{item}</td>\n"
    else:
        str = data["servers"]
        html += f"<td>{str}</td>\n"
    html += "</tr>\n"
    for key, value in data.items():
        if key != "servers":
            html += "<tr>\n"
            html += f"<td>{key}</td>\n"
            if isinstance(value, set):
                str = "<br>".join(value)
                html += f"<td>{str}</td>\n"
            else:
                for i in range(len(value)):
                    html += f"<td>{value[i]}</td>\n"
            html += "</tr>\n"
    html += "</table>"
    return html

#### make test HTML template ####
def test_page_maker(merged_file, merged_info_file, all_test_dir, cluster_name, scenario_name):
    logging.info("report_recorder - Executing test_page_maker function")
    htmls_dict={}
    mergedInfo = pd.read_csv(merged_info_file)
    merged = pd.read_csv(merged_file)
    original_columns_merged_info = mergedInfo.columns.tolist()
    mergedInfo = mergedInfo.loc[:, mergedInfo.nunique() != 1]
    removed_columns_mergedInfo = [col for col in original_columns_merged_info if col not in mergedInfo.columns]
    merged = merged.drop(columns=removed_columns_mergedInfo, errors='ignore')
    num_lines = mergedInfo.shape[0]
    number_of_groups = 0
    sorted_unique = classification.csv_to_sorted_yaml(mergedInfo)
    array_of_groups = classification.group_generator(sorted_unique,threshold=8)
    html_result = f"<p> برای اطلاعات بیشتر مشخصات سخت افزاری به سند  <a href=https://kateb.burna.ir/wiki/{cluster_name}--HW>{cluster_name}--HW</a> مراجعه کنید.</p>"
    html_result += f"<p> برای اطلاعات بیشتر مشخصات نرم افزاری به سند <a href=https://kateb.burna.ir/wiki/{cluster_name}--{scenario_name}--SW>{cluster_name}--{scenario_name}--SW</a> مراجعه کنید.</p>"
    html_result += "<h2> نتایج تست های کارایی </h2>"
    html_result += f"<p> بر روی این کلاستر {num_lines} تعداد تست انجام شده که در **var** دسته تست طبقه بندی شده است. </p>"
    for sharedInfo in array_of_groups:
        mergedInfo2 = mergedInfo
        merged2 = merged
        testGroup = ' , '.join(f'{key} = {value}' for key, value in sharedInfo.items())
        for key, value in sharedInfo.items():
            mergedInfo2 = mergedInfo2[mergedInfo2[key] == int(value)]
            merged2 = merged2[merged2[key] == int(value)]
            mergedInfo2 = mergedInfo2.drop(key,axis=1)
            merged2 = merged2.drop(key,axis=1)
        if merged2.empty:
            continue    
        else:
            number_of_groups+=1
            html_result+= f"<h3> نتایج تست های گروه: {testGroup} </h3>"
        html_result+= "<table border='1' class='wikitable'>\n"
        for i, row in enumerate(merged2.to_csv().split("\n")):
            html_result += "<tr>\n"
            tag = "th" if i == 0 else "td"
            for j , column in enumerate(row.split(",")):
                if j:
                    html_result += f"<{tag}>{column}</{tag}>\n"
            html_result += "</tr>\n"
        html_result += "</table>"
        format_tg = testGroup.strip().replace(' ','').replace('=','-').replace(',','-')
        html_result += f"<a href=https://kateb.burna.ir/wiki/{cluster_name}--{scenario_name}--{format_tg}> نمایش جزئیات </a>"
        ###### create subgroups within each original group  ######
        sorted_unique_file_1 = classification.csv_to_sorted_yaml(mergedInfo2)
        array_of_groups_1 = classification.group_generator(sorted_unique_file_1,threshold=4)
        sub_html_result = classification.create_tests_details(mergedInfo2,merged2,testGroup,array_of_groups_1,all_test_dir)
        htmls_dict.update({f"{cluster_name}--{scenario_name}--{format_tg}":sub_html_result+"[[رده:تست]]\n[[رده:کارایی]]\n[[رده:هیولا]]"})
    htmls_dict.update({cluster_name+'--'+scenario_name:html_result.replace("**var**",str(number_of_groups))+"[[رده:تست]]\n[[رده:کارایی]]\n[[رده:هیولا]]"})
    return htmls_dict

#### make HTML template ####
def dict_to_html(dict):
    logging.info("report_recorder - Executing dict_to_html function")
    html_dict = "<table border='1' class='wikitable'>\n"
    html_dict += "<tr><th> نام سرور </th><th> مشخصات </th></tr>\n"
    for key, value in dict.items():
        if isinstance(value, list):
            value_str = '<br>'.join(value)
        else:
            value_str = str(value)
        html_dict += f"<tr><td>{value_str}</td><td>{key}</td></tr>\n"
    html_dict += "</table>"
    return html_dict

def csv_to_html(csv_file):
    logging.info("report_recorder - Executing csv_to_html function")
    html_csv = "<table border='1' class='wikitable'>\n"
    with open(csv_file, 'r') as file:
        for i, row in enumerate(csv.reader(file)):
            html_csv += "<tr>\n"
            tag = "th" if i == 0 else "td"
            for column in row:
                html_csv += f"<{tag}>{column}</{tag}>\n"
            html_csv += "</tr>\n"
    html_csv += "</table>"
    return html_csv

def create_sw_hw_htmls(template_content, html_output, page_title): #HW_page_title = cluster_name #SW_page_title = cluster_name + scenario_name
    logging.info("report_recorder - Executing create_sw_hw_htmls function")
    htmls_dict={}
    hw_info_dict = {}
    html_data = template_content.replace("{title}",f"{page_title}") # for replace placeholder with title in page url
    for match in re.finditer(r'{input_config}:(.+)', template_content):
        # Iterate over the placeholders and replace them with content
        address_placeholder = match.group(0)
        file_path = match.group(1).strip()
        if '{backup_dir}' in file_path:
            file_path = file_path.replace('{backup_dir}', configs_dir)
        if '.csv' in os.path.basename(file_path):
            html_csv = csv_to_html(file_path) 
            html_data = html_data.replace(address_placeholder, html_csv)
        else:
            with open(file_path, 'r') as file:
                content_of_file = file.readlines()
            html_content = ""
            for content_line in content_of_file:
                html_content += f"<p>{content_line.replace(' ','&nbsp;')}</p>"
            html_data = html_data.replace(address_placeholder, html_content)
    for hconfig_info in re.finditer(r'{hw_config}:(.+)', template_content):
        hconfig_placeholder = hconfig_info.group(0)
        part,spec = hconfig_info.group(1).split(',')
        dict = compare(part.strip(), spec.strip())
        hw_info_dict.update({spec.strip():dict})
        html_of_dict = dict_to_html(dict)
        html_data = html_data.replace(hconfig_placeholder, html_of_dict)
    for sconfig_info in re.finditer(r'{sw_config}:(.+)', template_content):
        sconfig_placeholder = sconfig_info.group(0)
        sconfigs = sconfig_info.group(1).split(',')
        if sconfigs[0] == "swift_status":
            software_html = dict_to_html_table(generate_all_swift_status(sconfigs[1]))
        else:
            software_html = dict_to_html_table(generate_confs(sconfigs[0],None if len(sconfigs)== 1 else sconfigs[1]))
        html_data = html_data.replace(sconfig_placeholder, software_html)
    htmls_dict.update({page_title:html_data})
    htmls_dict.update(sub_pages_maker(html_data,page_title,hw_info_dict))
    for html_key,html_value in htmls_dict.items():
        with open(os.path.join(html_output+"/"+html_key+".html"), 'w') as html_file:
            html_file.write(html_value)
            print(f"HTML template saved to: {html_output+'/'+html_key+'.html'}") 
            logging.info(f"report_recorder - HTML template saved to: {html_output+'/'+html_key+'.html'}")
    return htmls_dict

def create_test_htmls(template_content, html_output, cluster_name, scenario_name, merged_file, merged_info_file, all_test_dir): #page_title = cluster_name + scenario_name
    logging.info("report_recorder - Executing create_test_htmls function")
    htmls_dict = test_page_maker(merged_file, merged_info_file, all_test_dir, cluster_name, scenario_name)
    for html_key,html_value in htmls_dict.items():
        with open(os.path.join(html_output+"/"+html_key+".html"), 'w') as html_file:
            html_file.write(html_value)
            print(f"HTML template saved to: {html_output+'/'+html_key+'.html'}") 
            logging.info(f"report_recorder - HTML template saved to: {html_output+'/'+html_key+'.html'}") 
    return htmls_dict

#### upload data and make wiki page ####
def convert_html_to_wiki(html_content):
    logging.info("report_recorder - Executing convert_html_to_wiki function")
    soup = BeautifulSoup(html_content, 'html.parser')
    # Convert <a> tags to wiki links
    for a_tag in soup.find_all('a'):
        a_tag.replace_with(f"[{a_tag['href']} |{a_tag.text}]")
    # Convert <img> tags to wiki images
    for img_tag in soup.find_all('img'):
        if 'src' in img_tag.attrs:
            img_tag.replace_with(f"[[File:{os.path.basename(img_tag['src'])}|border|center|800px|{os.path.basename(img_tag['src']).split('_')[0]}]]")
    return str(soup)

def sub_pages_maker(template_content , page_title ,hw_info_dict):
    logging.info("report_recorder - Executing sub_pages_maker function")
    global configs_dir
    htmls_list={}
    s1 = configs_dir
    sub_dir_path = os.path.join(s1,'configs/{serverName}/hardware/')
    if page_title + "--CPU" in template_content:
        htmls_list.update({page_title + "--CPU":one_sub_page_maker(sub_dir_path+'cpu/',hw_info_dict['cpu'])})
    if page_title + "--Memory" in template_content:
        htmls_list.update({page_title + "--Memory":one_sub_page_maker(sub_dir_path+'memory/',hw_info_dict['memory'])})
    if page_title + "--Network" in template_content:
        htmls_list.update({page_title + "--Network":one_sub_page_maker(sub_dir_path+'net/',hw_info_dict['net'])})
    if page_title + "--Disk" in template_content:
        htmls_list.update({page_title + "--Disk":one_sub_page_maker(sub_dir_path+'disk/',hw_info_dict['disk'])})
    if page_title + "--PCI" in template_content:
        #htmls_list.update({page_title + "--PCI":sub_page_maker(sub_dir_path+'pci/',hw_info_dict['pci'])})
        htmls_list.update({page_title + "--PCI":one_sub_page_maker(sub_dir_path+'pci/',hw_info_dict['cpu'])})
    return htmls_list

def one_sub_page_maker(path_to_files,spec_dict):
    logging.info("report_recorder - Executing one_sub_page_maker function")
    html_content = ""
    for i in os.listdir(path_to_files.replace("{serverName}",next(iter(spec_dict.values()))[0])):
        html_content += f"<h2> {str(i).replace('.txt','')} </h2>"
        for key,value in spec_dict.items():
            html_content += f"<h3> {value} </h3>"
            p = path_to_files.replace("{serverName}",value[0])+i
            if os.path.exists(p):
                with open(p, 'r') as file:
                    file_contents = file.readlines()
                for file_content in file_contents:
                    html_content += f"<p>{file_content.replace(' ','&nbsp;')}</p>"
            else:
                html_content += "<p> فایل مربوطه یافت نشد </p>"
    html_content += "<p> </p>"
    html_content += "[[رده:تست]]\n[[رده:کارایی]]\n[[رده:هیولا]]"
    return html_content

def upload_data(site, page_title, wiki_content):
    logging.info("report_recorder - Executing upload_data function")
    try:
        page = pywikibot.Page(site, page_title)
        if not page.exists():
            page.text = wiki_content + '\n powered by KARA'
            page.save(summary="Uploaded by KARA", force=True, quiet=False, botflag=False)
            #page.save(" برچسب: [[مدیاویکی:Visualeditor-descriptionpagelink|ویرایش‌گر دیداری]]")
            logging.info(f"Page '{page_title}' uploaded successfully.")
        else:
            print(f"Page '\033[91m{page_title}\033[0m' already exists on the wiki.")
            logging.warning(f"report_recorder - Page '{page_title}' already exists on the wiki.")
    except pywikibot.exceptions.Error as e:
        logging.error(f"report_recorder - Error uploading page '{page_title}': {e}")

def upload_images(site, html_content):
    logging.info("report_recorder - Executing upload_images function")
    soup = BeautifulSoup(html_content, 'html.parser')
    image_paths = [img['src'] for img in soup.find_all('img') if 'src' in img.attrs]
    # Upload each image to the wiki
    for image_path in image_paths:
        image_filename = os.path.basename(image_path)
        page = pywikibot.FilePage(site, f'File:{image_filename}')
        if not page.exists():
            file_page = pywikibot.FilePage(site, page.title())
            if file_page.exists():
                raise ValueError("File already exists!")
            success = file_page.upload(image_path, comment=f"Uploaded image '{image_filename}' using KARA")
            if success:
                print(f"File uploaded successfully! File page: {file_page.full_url()}")
                logging.info(f"report_recorder - Image '{image_filename}' uploaded successfully.")
            else:
                print(f"Upload this image '{image_filename}' failed.")
                logging.warning(f"report_recorder - Upload this image '{image_filename}' failed.")
        else:
            print(f"Image'\033[91m{image_filename}\033[0m'already exists on the wiki.")
            logging.warning(f"report_recorder - Image '{image_filename}' already exists on the wiki.")

def main(input_template, htmls_path, cluster_name, scenario_name, configs_directory, upload_operation, create_html_operation, merged_file, merged_info_file, all_test_dir):
    global configs_dir
    htmls_dict = {}
    log_maker = subprocess.run(f"sudo mkdir /var/log/kara/ > /dev/null 2>&1 && sudo chmod -R 777 /var/log/kara/", shell=True)
    logging.basicConfig(filename= '/var/log/kara/all.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    logging.info("\033[92m****** report_recorder main function start ******\033[0m")
    if create_html_operation:
        if configs_directory is not None:
            if os.path.exists(configs_directory):
                configs_dir = configs_directory
                get_list_of_servers()
            else:
                print(f"\033[91minput backup File not found\033[0m")
        if input_template:
            with open(input_template, 'r') as template_content:
                if 'hardware' in os.path.basename(input_template):
                    htmls_dict = create_sw_hw_htmls(template_content.read(), htmls_path, cluster_name+'--HW') 
                if 'software' in os.path.basename(input_template):
                    htmls_dict = create_sw_hw_htmls(template_content.read(), htmls_path, cluster_name+'--'+scenario_name+'--SW')
        if merged_file and merged_info_file and  all_test_dir:
            htmls_dict.update(create_test_htmls("",htmls_path, cluster_name, scenario_name, merged_file, merged_info_file, all_test_dir)) 
    elif upload_operation:
        for html_file in os.listdir(htmls_path):
            with open(os.path.join(htmls_path,html_file), 'r', encoding='utf-8') as file:
                htmls_dict = [{cluster_name+html_file:file.read()}]
    if upload_operation:
        # Set up the wiki site
        site = pywikibot.Site()
        site.login()
        for title,content in htmls_dict.items():
            wiki_content = convert_html_to_wiki(content)
            # Upload converted data to the wiki
            upload_data(site, title, wiki_content)
            # Upload images to the wiki
            upload_images(site, content)
    logging.info("\033[92m****** report_recorder main function end ******\033[0m")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate report for kateb")
    parser.add_argument("-i", "--input_template", help="Template HTML file path")
    parser.add_argument("-o", "--htmls_path", help="Output HTML file name")
    parser.add_argument("-cn", "--cluster_name", help="cluster_name set for title of Kateb HW page.")
    parser.add_argument("-sn", "--scenario_name", help="set for title of Kateb test page.")
    parser.add_argument("-U", "--upload_operation", action='store_true', help="upload page to kateb")
    parser.add_argument("-H", "--create_html_operation", action='store_true', help="create HTML page template")
    parser.add_argument("-cd", "--configs_directory", help="directory of backup include test configs")
    parser.add_argument("-m", "--merged_file", help="path to merged.csv file")
    parser.add_argument("-mi", "--merged_info_file", help="path to merged_info.csv file")
    parser.add_argument("-td", "--all_test_dir", help="directory of all tests")
    args = parser.parse_args()
    input_template = args.input_template 
    htmls_path = args.htmls_path
    cluster_name = args.cluster_name
    scenario_name = args.scenario_name 
    merged_file = args.merged_file
    merged_info_file = args.merged_info_file
    all_test_dir = args.all_test_dir
    if args.configs_directory:
       configs_directory = args.configs_directory 
    else:
        configs_directory = None
    upload_operation = args.upload_operation
    create_html_operation = args.create_html_operation
    main(input_template, htmls_path, cluster_name, scenario_name, configs_directory, upload_operation, create_html_operation, merged_file, merged_info_file, all_test_dir)
