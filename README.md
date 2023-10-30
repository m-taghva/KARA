# MBMT
‪<h2>Monster‬‬ ‫‪Bench-marking‬‬ ‫‪and‬‬ ‫‪Monitoring‬‬ ‫‪Tools‬‬ !</h2>

this project is related to https://github.com/alireza-hdri/ClusterBench and https://github.com/m-taghva/status-reporter.git

<img src="MBMT.png" width="1450" height="709"/>


    
    # Attention ! after clone repository, please remove (.placeholder) files inside ./result/ and Testlist_Work/workloads/ 
    
    - Install dependencies:
        # pip install pytz datetime matplotlib pandas tqdm  alive_progress
       =====================Status-Reporter==================
       - put your time range inside (time_rangs_taimestamp.txt) like this format: 2023-07-31 09:30:00,2023-07-31 10:30:00
       - write ip and port of influxdb and you data base name and target servers inside (status.conf) like this format: IP:port,DB name,host name:alias (can include # for comment)
       - aliases are used in csv file column
       - write selected metric name inside (*_metric_list.txt)
       - write your metric file like this: netdata.system.cpu.system (measurment line by line - you can use regex by \\w* in names) (can include # for comment)
       - your metric file prefix can use as expressions
       - you need to give time and metric files and customize path to query_result for saving outputs.
       - after complete all files start app with this command:
           (optional) # python3 status-reporter.py metric_list.txt,time.txt,path to query_result
           # python3 regex.py mean_metric_list,sum_metric_list, ... ,time_ranges_utc.txt,path to query_result
       ======================Analyzer========================
       - analyzer can work separately and manually :
           # python3 analyzer.py /csv-path  transformation-directory
       - in analyzer you can do sum or avg on csv columns and make new csv with transformation.
       - make t*.txt file for selecting columns and transform operation. 
       - first line of these files is operastin-new column name like : sum-my.cpu
       - other lines are selected columns.
       - new file is made in input csv directory and name is orginal csv name-transformation directory.csv
       =====================Csv-Merger========================
       - csv-merger.py is a experimental script and just use in some situations.
       - usage:
           # python3 csv-merger.py <path to parent of all query_results>
       - it can include directory name in to the merged of all csv.
       =======================Backup==========================
       - how to use backup script:
       - add new same users in influx host and your server : # adduser
       - edit sudoers file in both servers and add new user to it after %sudo group :  user1   ALL=(ALL) NOPASSWD: ALL
       - switch to new user for influx host server and create ssh key: ssh-keygen (make sure new key just for new user and his .ssh directory)
       - copy public key to your server: ssh-copy-id -p <port> user@ip
       - now change setting inside BackupConfig.json
       - run backup like this: # ptython3 backup_script.py -t 'start time(y-m-d h-m-s),end time(y-m-d h-m-s)' 
