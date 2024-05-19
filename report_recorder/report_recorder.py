import argparse
import re
import os
import pywikibot
from bs4 import BeautifulSoup
import logging
import csv
from collections import Counter
import subprocess

configs_dir = ""
def load(directory):
    with open(configs_dir + directory, 'r') as f:
        content = f.readlines()
    return content

#dmidecode -t 1
def generate_brand_model(serverName):
    result = load(f'/configs/{serverName}' + "/hardware/server-manufacturer/dmidecode.txt")
    manufacturer = ""
    productName = ""
    for line in result:
        if "Manufacturer" in line:
            manufacturer = line.split(":")[1].replace("\n" , "")
        if "Product Name" in line:
            productName = line.split(":")[1].replace("\n" , "")
    return manufacturer + productName

# lscpu
def generate_cpu_model(serverName):
    result= load(f'/configs/{serverName}' + "/hardware/cpu/lscpu.txt")
    coresPerSocket = ""
    socket = ""
    threads = ""
    model = ""
    for line in result:
        line = line.replace("  ", "").replace("\n","").split(":")
        if "Core(s) per socket" in line[0]:
            coresPerSocket=line[1]
            #print ("("+  coresPerSocket+ ")")
        if "Socket(s)" in line[0]:
            socket=line[1]
        if "Thread(s) per core" in line[0]:
            threads = line[1]
        if "Model name" in line[0]:
            model = line[1]
    return coresPerSocket + " cores x " + socket + " sockets x " + threads + " threads " + model

# lshw -short -C memory
def generate_ram_model(serverName):
    result = load(f'/configs/{serverName}' + "/hardware/ram/lshw-brief.txt")
    rams=[]
    for line in result:
        line = line.replace("  ", "")
        if "DIMM" in line:
            if "empty" not in line:
                model = line.split("memory ")[1]
                rams.append(model)
    counts = Counter(rams)
    ram = ""
    for item , count in counts.items():
        ram+= str(count) + " " + item
    return ram

# lshw -json -C net
def generate_net_model(serverName):
    result = load(f'/configs/{serverName}' + "/hardware/net/lshw.txt")
    #print(result)
    Flag = False
    nets=[]
    capacities = []
    for line in result:
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
        if capacities[i] is not None:
            netModel.append(capacities[i] + " " + nets[i])
        else:
            netModel.append(nets[i])
    counts = Counter(netModel)
    net = ""
    for item, count in counts.items():
        net += str(count) + " " + item + "\n"
    return net

#dmidecode -t 2
def generate_motherboard_model(serverName):
    result = load(f'/configs/{serverName}' + "/hardware/motherboard/dmidecode.txt")
    manufacturer = ""
    productName = ""
    for line in result:
        if "Manufacturer" in line:
            manufacturer = line.split(":")[1].replace("\n", "")
        if "Product Name" in line:
            productName = line.split(":")[1].replace("\n", "")
    return manufacturer + productName

# lshw -short -C disk
def generate_disk_model(serverName):
    result = load(f'/configs/{serverName}' + "/hardware/disk/lshw-brief.txt")
    disks= []
    for line in result:
        if "disk" in line:
            diskname = line.split("disk")[1].replace("  ", "").replace("\n", "")
            if diskname != " ":
                disks.append(diskname)
    counts = Counter(disks)
    disksNames =""
    for item, count in counts.items():
        disksNames += str(count) + item + "\n"
    return disksNames

def generate_model(server ,part ,spec):
    if part == "hardware":
        if spec == "cpu":
            return generate_cpu_model(server)
        elif spec == "ram":
            return generate_ram_model(server)
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

def compare(part ,spec):
    cmd = ["ls" , f'{configs_dir}/configs']
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    listOfServers = result.stdout.split("\n")
    listOfServers.pop()
    dict = {}
    for server in listOfServers:
        model= generate_model(server ,part ,spec)
        if model in dict:
            if dict[model] is None:
                dict[model] = []
        else: dict[model]= []
        dict[model].append(server)
    return dict

#### make HTML template ####
def dict_to_html(dict):
    html_dict = "<table border='1' class='wikitable'>\n"
    html_dict += "<tr><th> نام سرور </th><th> برند و مدل </th></tr>\n"
    for key, value in dict.items():
        key_str = ''.join(key)
        formatted_key = key_str.replace(' ', '_')
        if isinstance(value, list):
            value_str = ','.join(value)
        else:
            value_str = str(value)
        html_dict += f"<tr><td>{value_str}</td><td>{formatted_key}</td></tr>\n"
    html_dict += "</table>"
    return html_dict

def csv_to_html(csv_file):
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

def create_html_template(template_content, html_output):
    logging.info("Executing report_recorder create_html_template function")
    html_data = template_content # for replace placeholder with content of files
    # Find all occurrences of {input_config} placeholders in the template
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
    for config_info in re.finditer(r'{server_config}:(.+)', template_content):
        config_placeholder = config_info.group(0)
        part,spec = config_info.group(1).split(',')
        dict = compare(part.strip(), spec.strip())
        html_dict = dict_to_html(dict)
        html_data = html_data.replace(config_placeholder, html_dict)
    with open(html_output, 'w') as html_file:
        html_file.write(html_data)
        print(f"HTML template saved to: {html_output}")  
    return html_data

#### upload data and make wiki page ####
def upload_data(site, page_title, wiki_content):
    logging.info("Executing report_recorder upload_data function")
    try:
        page = pywikibot.Page(site, page_title)
        if not page.exists():
            page.text = wiki_content + "\n powered by KARA"
            page.save(summary="Uploaded by KARA", force=True, quiet=False, botflag=False)
            #page.save(" برچسب: [[مدیاویکی:Visualeditor-descriptionpagelink|ویرایش‌گر دیداری]]")
            logging.info(f"Page '{page_title}' uploaded successfully.")
        else:
            print(f"Page '\033[91m{page_title}\033[0m' already exists on the wiki.")
            logging.warning(f"Page '{page_title}' already exists on the wiki.")
    except pywikibot.exceptions.Error as e:
        logging.error(f"Error uploading page '{page_title}': {e}")

def convert_html_to_wiki(html_content):
    logging.info("Executing report_recorder convert_html_to_wiki function")
    soup = BeautifulSoup(html_content, 'html.parser')
    # Convert <a> tags to wiki links
    for a_tag in soup.find_all('a'):
        if 'href' in a_tag.attrs:
            a_tag.replace_with(f"[{a_tag['href']}|{a_tag.text}]")
    # Convert <img> tags to wiki images
    for img_tag in soup.find_all('img'):
        if 'src' in img_tag.attrs:
            img_tag.replace_with(f"[[File:{img_tag['src']}]]")
    return str(soup)

def upload_images(site, html_file_path):
    logging.info("Executing report_recorder upload_images function")
    with open(html_file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')
    # Find image filenames in <img> tags
    image_filenames = [img['src'] for img in soup.find_all('img') if 'src' in img.attrs]
    # Upload each image to the wiki
    for image_filename in image_filenames:
        image_path = os.path.join(os.path.dirname(html_file_path), image_filename)
        page = pywikibot.FilePage(site, f'File:{image_filename}')
        if not page.exists():
            # Create a FilePage object
            file_page = pywikibot.FilePage(site, page.title())
            # Check if the file already exists
            if file_page.exists():
                raise ValueError("File already exists!")
            # Upload the file
            success = file_page.upload(image_path, comment=f"Uploaded image '{image_filename}' using KARA")
            if success:
                print(f"File uploaded successfully! File page: {file_page.full_url()}")
            else:
                print("Upload failed.")
            logging.info(f"Image '{image_filename}' uploaded successfully.")
        else:
            logging.warning(f"Image '{image_filename}' already exists on the wiki.")

def main(input_template, html_output, page_title, html_page, directoryOfConfigs, upload_operation, create_html):
    global configs_dir
    log_dir = f"sudo mkdir /var/log/kara/ > /dev/null 2>&1 && sudo chmod -R 777 /var/log/kara/"
    log_dir_run = subprocess.run(log_dir, shell=True)
    logging.basicConfig(filename= '/var/log/kara/all.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("\033[92m****** report_recorder main function start ******\033[0m")
    if create_html:
        if os.path.exists(directoryOfConfigs):
            configs_dir = directoryOfConfigs
        else:
            print(f"\033[91minput backup File not found\033[0m")
        with open(input_template, 'r') as template_content:
            # Create HTML template
            create_html_template(template_content.read(), html_output)
    if upload_operation:
        # Set up the wiki site
        site = pywikibot.Site()
        site.login()
        with open(html_page, 'r', encoding='utf-8') as file:
            html_content = file.read()
        wiki_content = convert_html_to_wiki(html_content)
        # Upload converted data to the wiki
        upload_data(site, page_title, wiki_content)
        # Upload images to the wiki
        upload_images(site, html_page)
    logging.info("\033[92m****** report_recorder main function end ******\033[0m")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate report for kateb")
    parser.add_argument("-i", "--input_template", help="Template HTML file path")
    parser.add_argument("-o", "--html_output", help="Output HTML file name")
    parser.add_argument("-p", "--html_page", help="HTML template for upload")
    parser.add_argument("-t", "--page_title", help="Kateb page title.")
    parser.add_argument("-U", "--upload_operation", action='store_true', help="upload page to kateb")
    parser.add_argument("-H", "--create_html", action='store_true', help="create HTML page template")
    parser.add_argument("-tc", "--directoryOfConfigs", help="directory of test configs")
    args = parser.parse_args()
    if args.upload_operation and (args.html_page is None or args.page_title is None):
        print(f"\033[91mError: Both -p (--html_page) and -t (--page_title) switches are required for upload operation -U\033[0m")
        exit(1)
    if args.create_html and (args.input_template is None or args.html_output is None or args.directoryOfConfigs is None):
        print(f"\033[91mError: these switch -i (--input_template) and -o (--html_output) and -tc (--directoryOfConfigs) are required for generate HTML operation -H\033[0m")
        exit(1)
    input_template = args.input_template 
    html_output = args.html_output
    page_title = args.page_title 
    html_page = args.html_page
    directoryOfConfigs = args.directoryOfConfigs       
    upload_operation = args.upload_operation
    create_html = args.create_html
    main(input_template, html_output, page_title, html_page, directoryOfConfigs, upload_operation, create_html)
