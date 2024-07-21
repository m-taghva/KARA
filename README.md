‪<h2>Monster Performance Kit</h2>
<h3>open stack swift performance and monitoring tools (Kara)</h3>
<img src="kara_chart.gif" width="800" height="500"/>
    <img src="kara_tools.gif" width="800" height="500"/>

    ## Attention ! after clone repository, please remove (.placeholder) files inside ./results/ ##
    
        1 - Installing the COSBench Benchmarking Software
            In the first step, the COSBench tool needs to be installed. For installation guidance, refer to the Cloud Object Storage Benchmark page.
            After installation, go to the main directory and use the following commands to make the cli.sh script executable and create a soft link in the /usr/bin path.
            sudo chmod +x /home/user/cosbench/0.4.2.c4/cli.sh
            sudo ln -s /home/user/cosbench/0.4.2.c4/cli.sh /usr/bin/cosbench
        
        2 - Installing the KARA Toolset
            2.1 - Installing Tool Prerequisites:
                pip install pytz datetime matplotlib pandas alive_progress BeautifulSoup4
                apt install xfsprogs # install this tool in monster servers for xfs file system data collection.
                
            2.2 - Cloning the Latest Version of the Program from GitHub:
                git clone https://github.com/m-taghva/kara
                
            2.3 - Project Directory Description:
                The existing and required directories in the project: 
                monstaver: Backup and restore tool for the database
                status_reporter: Reporting tools from the database
                analyzer: Analysis and aggregation of reports taken in CSV format
                config_gen: Test execution and test configuration tools
                mrbench: Test execution tools
                report_recorder: Documentation tools for test results in the Katib system
                manager: Management tool for the set, configuration files, and tool prerequisites
                results: Location for storing test results and reports
                configure: Auxiliary tools
                
            2.4 - Operating System and SSH Settings:
                Edit the sudoers file and give permission to the user running KARA to execute sudo commands without a password:
                # visudo
                    > %sudo ALL=(ALL:ALL) ALL
                    > user ALL=(ALL) NOPASSWD: ALL
                    
                Create an SSH key for the desired user on all monster and MC servers, as well as the server running KARA, so that no password is needed for SSH login:
                # adduser
                # ssh-keygen (make sure the new key is just for the new user and his .ssh directory)
                # ssh-copy-id -p <port> user@ip
                
            2.5 - Running the configure tool:
                After installing the prerequisites and cloning the repository, the configure.sh tool in the manager directory needs to be run to execute some prerequisite processes and install KARA.
                # bash configure.sh
                
            2.6 - Tool Logs:
                The path and log file for all tools are the same and equal to var/log/kara/all.log/. In more advanced tools with a configuration file, it is possible to change the log display level between debug - info - warning - error -    critical. For simpler tools without a configuration file, the log display level is debug.

        3- Execution Description of Tools
            **Note: All tool configuration files are in the standard YAML format, allowing sections that are not needed to be commented out.
            
            3.1 - config-gen Tool:
                This tool is responsible for creating workload configurations and various tests for COSBench. The program is located in the config_gen directory, and its input is an input.txt file in that directory. Based on the content of this input file, the tool can generate multiple configuration files with different values to facilitate and speed up the process of creating different scenarios.
                
                run config_gen:
                        # python3 config-gen.py -i input.txt -o <output dir>
                
            3.2 - mrbench Tool:
                This tool is responsible for executing the test configurations created by the previous tool and sending them to COSBench. It creates a unique directory for each test based on the test's time interval within a parent directory, such as result, and stores the results and information obtained from COSBench in it. This tool also has the capability to modify Swift and Ring configuration files, and it can receive files in .gz, .builder, and .conf formats from a directory that contains all the files for this purpose. The tool has a configuration file named mrbench.conf located in the /etc/KARA/ directory, which includes the information of monster servers and containers. It uses these configurations to connect via SSH and modify Swift and Ring files, and finally, restart the monster containers. This program is located in the mrbench directory.
                config file of mrbench:

                                swift:
                                    m-r1z1s1: # container name
                                         ssh_user: root # ssh user
                                         ip_swift: 192.168.143.158 # ip server
                                         ssh_port: 22 # ssh port
                                
                                    m-r2z2s2: # container name
                                         ssh_user: root #ssh user
                                         ip_swift: 192.168.143.155 # ip server
                                         ssh_port: 22 # ssh port
                                    log:
                                       level: info  # values = debug - info - warning - error - critical

                run mrbench:
                    # python3 mrbench.py -i <path to test config file> -o <output dir> -cr <path to config_ring dir>

            3.3 - status-reporter Tool:
                This tool is responsible for sending queries to the InfluxDB database and retrieving responses based on the required measurements or metrics. It displays the results in two formats: CSV files and graphs. The tool is located in the status-reporter directory, and its configuration files are located in /etc/KARA/ in the status.conf file. The metric files are located in the metrics directory within the tool's main directory. This tool is designed to receive its required inputs in two ways: through the configuration file or by accepting arguments from the user.

                3.3.1 - Configuration File Description:
                        The configuration file consists of three main sections and a log section, each explained below:
                        - Database Information Section:
                                You can repeat this part of the configuration for other MC servers or lists of databases and related Hiola servers, allowing you to include multiple servers and databases for reporting in one configuration file.
                                
                                influxdbs:  # influxdbs section  
                                  MC:  # mc server name 
                                    ip: 192.168.1.1  # mc ip
                                    databases:  # list of databases
                                       opentsdb:  # first database name
                                           hostls:  # monster server name and alias or config name
                                             m-r1z1s1-controller: paco 
                                             m-r2z2s2-controller: proxy
                                             
                        - Metric Files Information Section:
                                The second part of the configuration is related to the measurement or metric files. In this section, the mathematical operations for each file and their paths are mentioned. These can be modified using the input switches or program arguments. Each file contains a list of metrics sent by netdata and stored in influxdb, with the ability to comment out unnecessary metrics. The naming format for metrics in the existing files should be as follows: netdata.n.n.n.
                            
                                metrics:
                                  sum:
                                    path: ./../status_reporter/metrics/sum_metric_list.txt
                                  mean:
                                    path: ./../status_reporter/metrics/mean_metric_list.txt
                                  max:
                                    path: ./../status_reporter/metrics/max_metric_list.txt
                                  min:
                                    path: ./../status_reporter/metrics/min_metric_list.txt
                                    
                        - Time Information Section:
                                In this section, you can define time margins from the beginning and end of the report interval to ensure more accurate output, measured in seconds.
                                When sending queries to generate graphs, you can also group time intervals to improve the readability and accuracy of the output graph, measured in seconds.
                                The final part includes the report time range, specifying the start and end times in Tehran timestamp format. If there is no specific time range for the report, you can set it to report from the current time to a previous interval, formatted like this: now-2h (from now to 2 hours ago). This can be modified using the program's input switches.
                                
                                time:
                                  start_time_sum: 10  # increase your report start time
                                  end_time_subtract: 10  # decrease your report end time
                                  time_group: 10  # time group for image query 
                                  time_range: 2024-04-23 10:55:00,2024-04-23 10:59:00  # or now-2h,now-1h
                                  
                        - Usage Method:
                                If you need images and graphs for each execution and report, use the --img switch at the end of the following command:
                                # python3 status_reporter.py -m <path to metric file 1>,<path to metric file 2>,<path to metric file n> -t ‘start time,end time’ -o <output dir or result dir>
                                The results will be saved in the given directory under query_result as graphs for each Hiola server and a CSV file for all of them, named after the report's time range.
                            

            3.4 - Monstaver tool:
                Description:
                Monstaver is a tool designed to perform the following tasks:
                    Database Backup:
                        Receives a user-defined time interval and creates a backup of the InfluxDB database within that interval.
                    Swift Configuration Handling:
                        Retrieves Swift configurations (including ring, object, container, and account) from monster and transfers them to the final backup directory.
                    Integration with Test Results:
                        Can include test results and reports generated by other tools alongside backups and configurations.
                    Compression and Storage:
                        Compresses these files for easier storage and movement, categorized for convenience.
                    Backup Restoration:
                        Provides functionality to restore backups taken from InfluxDB when needed.
                    Cluster Upload:
                        Uploads the final compressed backup file to the monster cluster, such as zdrive.                        
                    Configuration File:
                        The configuration file for Monstaver is located at etc/KARA/monstaver.conf.

                3.4.1 - Configuration File Description for Monstaver
                        The configuration file for Monstaver is structured into two main sections and a logging section, each serving specific purposes related to backup and restoration tasks.
                        Backup Section (default):
                            This section includes fundamental information for the backup process, categorized into three parts as explained:
                            
                            default:
                                time: 2024-06-15 11:00:00,2024-06-15 11:05:00 # time range : start,end
                                time_margin: 10,10 # time margin
                                input_paths:
                                  - /home/KARA/results  # some dir inside local server
                                backup_output: /tmp/influxdb-backup  # output of all parts in local server
                                # Monster storage info for uploading backup
                                token_url: https://api.zdrive.ir/auth/v1.0
                                public_url: https://api.zdrive.ir/v1/AUTH_user
                                username: "user:user"
                                password: **********
                                cont_name: a name
                                # Make backup from hardware/software/swift
                                hardware_backup: True
                                software_backup: True
                                swift_backup: True
                                
                        Swift Backup Section (swift):
                            This section contains details about Hiola servers and their containers, used for SSH connection and fetching Swift files, including configurations (hardware/software) and Swift-specific details.
                            
                            swift:
                                m-r1z1s1: # container name
                                  ssh_user: root # SSH user
                                  ip_swift: 192.168.143.158 # Server IP
                                  ssh_port: 22 # SSH port
                                
                                m-r2z2s2: # container name
                                  ssh_user: root # SSH user
                                  ip_swift: 192.168.143.155 # Server IP
                                  ssh_port: 22 # SSH port
                                  
                        Database Sources Section (db_sources):
                            This section includes information about MC (Monster Container) servers hosting InfluxDB, along with the mount point of the container and the list of databases available for backup.
                            
                            db_sources:
                            MC:
                              ip: 192.168.143.150 # InfluxDB server IP
                              ssh_port: 22 # SSH port
                              ssh_user: root # SSH user
                              container_name: influxdb # InfluxDB container name
                              influx_volume: /var/lib/influxdb/KARA_BACKUP # Mount point of InfluxDB container to host
                              databases:
                                - opentsdb
                                
                        Restoration Section:
                            This section defines information about servers hosting InfluxDB for restoration purposes. It specifies similar configurations to the backup section but includes details for restoring databases from backup files located in the compressed backup file.
                            
                            influxdbs_restore:
                                MyPC:
                                  ip: 192.168.143.150 # MC server IP or new server of InfluxDB
                                  ssh_port: 22 # SSH port
                                  ssh_user: root # SSH user
                                  container_name: influxdb # Container name
                                  influx_volume: /var/lib/influxdb/KARA_RESTORE # Mount point with restore directory
                                  databases:
                                    - prefix: "rst1_" # New database prefix name
                                      location: /tmp/influxdb-backup/231107T000743_231107T030012/dbs/influxdb.tar.gz # Backup file in local server
                                      
                        Program Output:
                            The program generates its output in the directory /tmp/influxdb-backup/, which contains three main directories:
                            dbs: For database backups.
                            other_info: For user-defined paths.
                            configs: For hardware, software, and Swift configurations related to each Hiola server.
                            This configuration file enables Monstaver to efficiently manage and perform backups and restorations of InfluxDB databases along with associated Swift configurations and other relevant data.

                        Usage of the tool:
                            This tool can receive its main inputs both as user arguments and through a configuration file.
                            # python3 monstaver.py -t 'start time,end time' -i /path/to/dir/ -r -hw -sw -s -ib -d
                            The argument d is for cleaning the final output directory and only preserving its compressed state. r is for restoring, s is for obtaining Swift configurations, sw and hw for hardware and software information retrieval respectively, ib for backup creation, i for user-specified directories, and t denotes the backup time interval.

            3-5- status-analyzer tool:
                This tool consists of two main processes: first, aggregating CSV files created by other tools, and then analyzing them for comparison and troubleshooting. The tool resides in the analyzer directory.
                Aggregation (merge): 
                    This tool takes as input a list of CSV files or a directory containing CSV files, aggregates them, and saves the merged result in a file named merged.csv at the specified user-provided path.
                Analysis (analyze):
                This section is responsible for parsing and analyzing CSV files. It can perform operations such as averaging and summing across selected columns and create a new CSV with new columns containing the analysis results. The workflow of the analysis section is as follows: it takes as input one CSV file and a directory containing several files. These files include selected column names, the name of the analysis result column, and the type of mathematical operation for each analysis.
                The output of this program is a new CSV file named by combining the name of the initial file and the input directory containing the transformation operations within it. This new file replaces the selected columns with the previous CSV columns and the newly analyzed columns. It is saved alongside the original and selected files. Depending on the desired column types within the subset files in the transformation directory, you may change the name of this directory to *-transformation.

                usage:
                    # python3 status-analyzer.py -M -o<output> -sc <csv1,csv2,csvn> -A -c <csv for analyze> -t <transformation dir>
                    # python3 status-analyzer.py -M -o<output> -sc <csv_dir/*> -A -c <csv for analyze> -t <transformation dir>

            3-6- report_recorder tool:
                This tool is responsible for generating documentation from received reports for Hyola tests and saving them in HTML format. Subsequently, it uploads them to the Kateb system. The workflow of this tool is as follows: it takes as input an HTML template for the hardware specifications of Hyola servers and another template for the software specifications of monster. Within these templates, it places server information in specified locations using predefined placeholders. It generates multiple types of templates as output.
                For test information, it also receives a merged CSV file and an output directory of tests. It creates HTML documents for the specifications and configurations of the tests, along with graphs for each test. Subsequently, it uploads them.
                The initial and main templates for hardware and software are located in the all-htmls-dir directory.
                Usage of the Tool:
                    Before running the software, you need to enter your Katib user information in the user-config.py file located in the report-recorder or manager directory. After opening this file, enter your username under the user name section. During the first upload to Kateb, you will also need to enter your password.
                    config file of this tool:
                    
                        naming_tag:
                            cluster_name: kara
                            scenario_name: pre_test
                            # tags of mediawiki 
                            tags: "[[رده:تست]]\n[[رده:کارایی]]\n[[رده:هیولا]]"
                        
                        tests_info:
                            merged: /home/kara/results/analyzed/merged.csv 
                            merged_info: /home/kara/results/analyzed/merged_info.csv
                            tests_dir: /home/kara/results/ # dir of all tests result
                            metrics: # metrics name for making report withe their images
                                - netdata-disk-sdb-writes-mean
                                - netdata-statsd-timer-swift-object-server-put-timing-events-mean
                        
                        output_path: /home/kara/report_recorder/all-htmls-dir/
                        configs_dir: /tmp/influxdb-backup/240624T092914_240624T093015/ # backup dir path
                                            
                    This software operates in three different modes, described below:
                        For Software and Hardware Sections:
                            To specify the uncompressed backup directory from which information will be extracted and placed into templates.                            
                        For the Testing Section:
                            Specify the paths to the consolidated CSV files (m, -mi) from which test information will be extracted. Provide the parent directory of all test results (-td) for uploading test graphs.                        
                        Creating and Uploading Software Information:
                        # python3 report_recorder.py -H -SW -i <path to/software.html> -o <output path> -cn <cluster name> -sn <scenario name> -cd <path to/monstaver backup dir> -U
                        
                        Creating and Uploading Hardware Information:
                        # python3 report_recorder.py -H -HW -i <path to/hardware.html> -o <output path> -cn <cluster name> -cd <path to/monstaver backup dir> -U
                        
                        Creating and Uploading Test Information:
                        # python3 report_recorder.py -H -MT -o <output path> -cn <cluster name> -sn <scenario name> -m <path to/merged.csv> -mi <path to/merged_info.csv> -td <path to/all test result dir> -U
                        
                        These commands will generate HTML documents and upload them to the Katib system, incorporating the specified software, hardware, or test information as needed.
                    
            3-7- Manager Tool:            
                This tool operates as a central control hub for system monitoring, executing all created tools in pipeline fashion and various scenarios, providing them with necessary inputs. For smoother and faster user experience, it is advisable to use this tool to automatically execute other tools and software, thereby reducing the likelihood of human error.
                To use this tool, simply provide it with a scenario file customized according to the user's needs.
                A detailed explanation of this file follows:
                    The default scenario file is located in /manager/scenario_dir/ directory, which can be edited and customized to create several different types as needed.
                    This tool operates as a central control hub for system monitoring, executing all created tools in a specified pipeline and various scenarios, providing them with necessary inputs. For a smoother and faster user experience, it is recommended to use this tool to automatically execute other tools and software, thereby reducing the likelihood of human error.
                    The scenario file determines the execution order of tools and is customizable. Each tool section defines its required inputs and outputs, as detailed below:
                        config_gen:
                          # This section receives a list of input templates. It can include multiple workload test templates with specific numbering, or config files like swift configs. Output type for the program is also specified in the next section.
                          
                        Mrbench:
                          # This section defines the output directory path and the execution mode of status-reporter and monstaver concurrently with each test run. Output type options are specified as csv output, images, database backups, or just hardware and software information in backups. Swift and ring config directories are specified.
                        
                         # # # Note: If config-gen has been executed before this tool and has swift configs, there's no need to use the conf_dir section, but ring files must be listed.
    
                        status_reporter:
                          # If this tool needs to work independently, use its specific section. Here, inputs can include a file containing a list of required test intervals, and specify whether graph images are needed, along with the final output path.
                        monstaver:
                          # If this tool needs to work independently, use its specific section. Here, you can specify a file containing a list of required time intervals for backup, and the desired directory alongside backups. Additionally, batch_mode can be enabled to perform backup operations for a batch of tests after all tests have been executed. Next section can also specify the type of operation, whether it's backup with restore.
                          
                        status_analyzer:
                          # In this tool's section, aggregation and analysis operations can be specified, along with required inputs for each section.
                          
                        report_recorder:
                          # In this tool's section, specify the html templates to be created and uploaded to Katib, along with the parent directory path of input templates and the storage path for output templates, and the page names in Katib are specified.
                        This scenario file is in YAML format and can be commented out as needed.
