import itertools
import pandas as pd
import os

################# CSV to sorted yaml descending-based ##############################################################
def create_tests_details(mergedTestsInfo,mergedTests,test_group,array_of_parameters,tests_dir,data_loaded):
    img_metrics = []
    for img_metric in data_loaded['tests_info'].get('metrics', []):
        img_metrics.append(img_metric)
    html_result =  f"<p> در این سند جزئیات مربوط به تست های گروه {test_group} آمده است</p>"
    serverList = unique_values = mergedTests['Host_alias'].unique().tolist()
    for testInfo in array_of_parameters:
        testGroup = ' , '.join(f'{key} = {value}' for key, value in testInfo.items())
        h2checker = 1
        for serverName in serverList:
            mergedTestsInfo2 = mergedTestsInfo
            mergedTests2 = mergedTests 
            mergedTests2 = mergedTests2[mergedTests2['Host_alias'] == serverName ]
            for key, value in testInfo.items():
                mergedTestsInfo2 = mergedTestsInfo2[mergedTestsInfo2[key] == int(value) ]
                mergedTestsInfo2 = mergedTestsInfo2.drop(columns=key)
                mergedTests2 = mergedTests2[mergedTests2[key] == int(value) ]
                mergedTests2 = mergedTests2.drop(columns=key)
            if mergedTestsInfo2.empty:
                break
            if h2checker:
                html_result+= f"<h2> نتایج تست های گروه: {testGroup} </h2>"
                h2checker = 0
            mergedTestsInfo2.reset_index()
            test_rows = [pd.DataFrame([row], columns=mergedTestsInfo2.columns) for _, row in mergedTestsInfo2.iterrows()]
            num_of_tests_within_groups = len(test_rows)
            html_result+=f"<p> در این گروه {num_of_tests_within_groups} تست انجام شده است که نتایج آن در ادامه قرار داده شده است.  </p>"
            html_result+= f"<h3> نتایج سرور: {serverName} </h3>"
            for test in test_rows:
                trow = test.iloc[0]
                row_dict = trow.to_dict()
                selected_merged = mergedTests2.loc[mergedTests2['Time'] == row_dict['Time']]
                html_result+= f"<h4> نتایج تست : {row_dict} </h4>"
                html_result+= "<table border='1' class='wikitable'>\n"
                for i, row in enumerate(selected_merged.to_csv().split("\n")):
                    html_result += "<tr>\n"
                    tag = "th" if i == 0 else "td"
                    for j , column in enumerate(row.split(",")):
                        if j:
                            html_result += f"<{tag}>{column}</{tag}>\n"
                    html_result += "</tr>\n"
                html_result += "</table>"
                html_result += "<h4>تصاویر \n</h4> <p> </p>"
                directory_path = os.path.join(tests_dir,f"{row_dict['Time']}/query_results/{serverName}-images")
                for img in img_metrics:
                    if os.path.exists(directory_path):
                        for filename in os.listdir(directory_path):
                            if img in filename:
                                img_addr = os.path.join(directory_path,filename)
                                html_result += f"<img src={img_addr}>"   
                    else:
                        print(f"Directory {directory_path} does not exist for inserting images into kateb.")
            html_result +=  f"<h3> خلاصه و جمع بندی</h3>" 
            html_result+= "<table border='1' class='wikitable'>\n"
            for i, row in enumerate(mergedTests2.to_csv().split("\n")):
                html_result += "<tr>\n"
                tag = "th" if i == 0 else "td"
                for j , column in enumerate(row.split(",")):
                    if j:
                        html_result += f"<{tag}>{column}</{tag}>\n"
                html_result += "</tr>\n"
            html_result += "</table>"    
    html_result+= "<h2> جمع بندی نتایج</h2>"
    html_result+= f"<p> در این سند نتایج مربوط به {len(mergedTestsInfo)} تست گزارش شده است. همه تست ها دارای مقدار {test_group} هستند که برای {', '.join(array_of_parameters[0].keys())} های مختلف مورد بررسی قرار گرفتند. جدول زیر خلاصه ای از نتایج این تستها را نشان می دهد. </p>"  
    html_result+= "<table border='1' class='wikitable'>\n"
    for i, row in enumerate(mergedTests.to_csv().split("\n")):
        html_result += "<tr>\n"
        tag = "th" if i == 0 else "td"
        for j , column in enumerate(row.split(",")):
            if j:
                html_result += f"<{tag}>{column}</{tag}>\n"
        html_result += "</tr>\n"
    html_result += "</table>"  
    return html_result

##########################################################################################################
def csv_to_sorted_yaml(mergedInfo):
    unique_values = {}
    headers = mergedInfo.columns.tolist()  # Skip the header row
    for header in headers[1:]:
        unique_values.update({header:mergedInfo[header].unique()})
    sorted_dict = dict(sorted(unique_values.items(), key=lambda x: len(x[1]),reverse=True))    
    return sorted_dict

#######################################################################################################
def generate_combinations(yaml_data):
    values_lists = list(yaml_data.values())
    combinations = list(itertools.product(*values_lists))
    return combinations

########################################################################################################
def group_generator (yaml_data,threshold):
    keys_list = list(yaml_data.keys())
    result=1
    j=1
    if (len(keys_list)==1):
        j=0
    else:
        for i in range(len(keys_list)):
            key = keys_list[i]
            result*=len(yaml_data[key])
            j = i
            if result > threshold and result < 2*threshold:
                continue
            if result > 2*threshold:
                break
    keys_list1 = list(yaml_data.keys())
    start_index = j 
    end_index = len(yaml_data.keys())
    sublist = keys_list1[start_index:end_index]
    new_yaml_data = {key: yaml_data[key] for key in sublist}
    # Generate combinations
    combinations1_number_of_group = generate_combinations(new_yaml_data)
    array_of_groups=[]
    for combination1 in combinations1_number_of_group:
        result_dict1=dict(zip(new_yaml_data.keys(), combination1))
        array_of_groups.append(result_dict1)
    return array_of_groups
