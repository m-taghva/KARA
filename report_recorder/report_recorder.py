import argparse
import re
import os
import yaml
import logging
import csv
import subprocess
import sys
import pandas as pd
from bs4 import BeautifulSoup
pywiki_path = os.path.abspath("./../report_recorder/pywikibot/")
if pywiki_path not in sys.path:
    sys.path.append(pywiki_path)
import pywikibot
classification_path = os.path.abspath("./../report_recorder/")
if classification_path not in sys.path:
    sys.path.append(classification_path)
import classification
import analyzer

config_file = "/etc/kara/report_recorder.conf"

def load_config(config_file):
    with open(config_file, "r") as stream:
        try:
            data_loaded = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"Error loading the configuration: {exc}")
            sys.exit(1)
    return data_loaded

#### make test HTML template ####
def test_page_maker(merged_file, merged_info_file, all_test_dir, cluster_name, scenario_name, data_loaded):
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
        sub_html_result = classification.create_tests_details(mergedInfo2,merged2,testGroup,array_of_groups_1,all_test_dir,data_loaded)
        htmls_dict.update({f"{cluster_name}--{scenario_name}--{format_tg}":sub_html_result+data_loaded['naming_tag'].get('tags')})
    htmls_dict.update({cluster_name+'--'+scenario_name:html_result.replace("**var**",str(number_of_groups))+data_loaded['naming_tag'].get('tags')})
    return htmls_dict

#### make HTML template ####
def dict_html_software(data):
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

def dict_html_hardware(dict):
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

def create_sw_hw_htmls(template_content, html_output, page_title, data_loaded): #HW_page_title = cluster_name #SW_page_title = cluster_name + scenario_name
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
        dict = analyzer.compare(part.strip(), spec.strip())
        hw_info_dict.update({spec.strip():dict})
        html_of_dict = dict_html_hardware(dict)
        html_data = html_data.replace(hconfig_placeholder, html_of_dict)
    for sconfig_info in re.finditer(r'{sw_config}:(.+)', template_content):
        sconfig_placeholder = sconfig_info.group(0)
        sconfigs = sconfig_info.group(1).split(',')
        if sconfigs[0] == "swift_status":
            software_html = dict_html_software(analyzer.generate_all_swift_status(sconfigs[1]))
        else:
            software_html = dict_html_software(analyzer.generate_confs(sconfigs[0],None if len(sconfigs)== 1 else sconfigs[1]))
        html_data = html_data.replace(sconfig_placeholder, software_html)
    html_data += "<p> </p>"
    html_data += data_loaded['naming_tag'].get('tags')
    htmls_dict.update({page_title:html_data})
    htmls_dict.update(sub_pages_maker(html_data,page_title,hw_info_dict,data_loaded))
    for html_key,html_value in htmls_dict.items():
        with open(os.path.join(html_output+"/"+html_key+".html"), 'w') as html_file:
            html_file.write(html_value)
            print(f"HTML template saved to: {html_output+'/'+html_key+'.html'}") 
            logging.info(f"report_recorder - HTML template saved to: {html_output+'/'+html_key+'.html'}")
    return htmls_dict

def create_test_htmls(template_content, html_output, cluster_name, scenario_name, merged_file, merged_info_file, all_test_dir, data_loaded): #page_title = cluster_name + scenario_name
    logging.info("report_recorder - Executing create_test_htmls function")
    htmls_dict = test_page_maker(merged_file, merged_info_file, all_test_dir, cluster_name, scenario_name, data_loaded)
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

def sub_pages_maker(template_content , page_title ,hw_info_dict,data_loaded):
    logging.info("report_recorder - Executing sub_pages_maker function")
    global configs_dir
    htmls_list={}
    c_dir = configs_dir
    sub_dir_path = os.path.join(c_dir,'configs/{serverName}/hardware/')
    if page_title + "--CPU" in template_content:
        htmls_list.update({page_title + "--CPU":one_sub_page_maker(sub_dir_path+'cpu/',hw_info_dict['cpu'],data_loaded)})
    if page_title + "--Memory" in template_content:
        htmls_list.update({page_title + "--Memory":one_sub_page_maker(sub_dir_path+'memory/',hw_info_dict['memory'],data_loaded)})
    if page_title + "--Network" in template_content:
        htmls_list.update({page_title + "--Network":one_sub_page_maker(sub_dir_path+'net/',hw_info_dict['net'],data_loaded)})
    if page_title + "--Disk" in template_content:
        htmls_list.update({page_title + "--Disk":one_sub_page_maker(sub_dir_path+'disk/',hw_info_dict['disk'],data_loaded)})
    if page_title + "--PCI" in template_content:
        #htmls_list.update({page_title + "--PCI":sub_page_maker(sub_dir_path+'pci/',hw_info_dict['pci'],data_loaded)})
        htmls_list.update({page_title + "--PCI":one_sub_page_maker(sub_dir_path+'pci/',hw_info_dict['cpu'],data_loaded)})
    return htmls_list

def one_sub_page_maker(path_to_files,spec_dict,data_loaded):
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
    html_content += data_loaded['naming_tag'].get('tags')
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

    data_loaded = load_config(config_file)
    if cluster_name is None:
        cluster_name = data_loaded['naming_tag'].get('cluster_name')
    if scenario_name is None:
        scenario_name = data_loaded['naming_tag'].get('scenario_name')
    if htmls_path is None:
        htmls_path = data_loaded['output_path']
    if merged_file is None:
        merged_file = data_loaded['tests_info'].get('merged')
    if merged_info_file is None:
        merged_info_file = data_loaded['tests_info'].get('merged_info')
    if all_test_dir is None:
        all_test_dir = data_loaded['tests_info'].get('tests_dir')
    if configs_directory is None:
        configs_directory = data_loaded['configs_dir']
    if create_html_operation:
        if configs_directory is not None:
            if os.path.exists(configs_directory):
                configs_dir = configs_directory
                analyzer.conf_dir(configs_dir)
                analyzer.get_list_of_servers()
            else:
                print(f"\033[91minput backup File not found\033[0m")
        if input_template:
            with open(input_template, 'r') as template_content:
                if 'hardware' in os.path.basename(input_template):
                    htmls_dict = create_sw_hw_htmls(template_content.read(), htmls_path, cluster_name+'--HW', data_loaded) 
                if 'software' in os.path.basename(input_template):
                    htmls_dict = create_sw_hw_htmls(template_content.read(), htmls_path, cluster_name+'--'+scenario_name+'--SW', data_loaded)
        if merged_file and merged_info_file and all_test_dir:
            htmls_dict.update(create_test_htmls("",htmls_path, cluster_name, scenario_name, merged_file, merged_info_file, all_test_dir, data_loaded)) 
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
    htmls_path = args.htmls_path if args.htmls_path else None
    cluster_name = args.cluster_name if args.cluster_name else None
    scenario_name = args.scenario_name if args.scenario_name else None
    merged_file = args.merged_file if args.merged_file else None
    merged_info_file = args.merged_info_file if args.merged_info_file else None
    all_test_dir = args.all_test_dir if args.all_test_dir else None
    configs_directory = args.configs_directory if args.configs_directory else None
    upload_operation = args.upload_operation
    create_html_operation = args.create_html_operation
    main(input_template, htmls_path, cluster_name, scenario_name, configs_directory, upload_operation, create_html_operation, merged_file, merged_info_file, all_test_dir)
