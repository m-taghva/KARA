import re
import string
import random
import os
import argparse

# cleanup output dir for new template
def cleanup_output_config_gen(output_directory):
    for filename in os.listdir(output_directory):
        if "#" in filename:
            file_path = os.path.join(output_directory, filename)
            os.remove(file_path)

def replace_vars(input_text, conf_name, output_directory):
    currentVar = re.search("\?\d+L\d+[sd]", input_text)
    if currentVar:
        if currentVar.group()[-1] == 's':
            replace_vars(input_text.replace(currentVar.group(),str(''.join(random.choices(string.ascii_uppercase + string.digits,k=int(currentVar.group().split('L')[1].split('s')[0]))))),conf_name, output_directory)
        else:
            replace_vars(input_text.replace(currentVar.group(),str(''.join(random.choices(string.digits,k=int(currentVar.group().split('L')[1].split('d')[0]))))),conf_name, output_directory)
    else:
        with open(os.path.join(output_directory, f"{conf_name}#"), 'w') as outfile:
            outfile.write(input_text)

def replace_tags(input_text, conf_name, output_directory):
    global conf_number
    currentTag = re.search("#\d+{", input_text)
    if currentTag:
        TagRegex = currentTag.group() + "[^}]+}[^#]*#"
        for i in range(len(re.search(TagRegex, input_text).group().split('}')[0].split(','))):
            newInput = input_text
            tagName = ""
            for similarTag in re.findall(TagRegex, input_text):
                similarTagList = similarTag.split('{')[1].split('}')[0].split(',')
                newInput = re.sub(TagRegex, similarTagList[i], newInput, 1)
                tagName += ("#" + re.search("(?<=})[^#]*(?=#)", similarTag).group() + ":" + str(similarTagList[i]))
            replace_tags(newInput, conf_name + tagName, output_directory)
    else:
        conf_number += 1
        replace_vars(input_text, "{:04}".format(conf_number) + conf_name, output_directory)
                    
def main(input_file_path, output_directory, conf_number):
    conf_number = int(conf_number) if conf_number is not None else 1
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    cleanup_output_config_gen(output_directory)
    with open(input_file_path, 'r') as inputFile:
        input_text = inputFile.read()
    replace_tags(input_text, "", output_directory)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate configuration files.')
    parser.add_argument('-i', '--input', help='Input file path', required=True)
    parser.add_argument('-o', '--output', help='Output directory', required=True)
    parser.add_argument('-c', '--conf_number', help='conf_number counter')
    args = parser.parse_args()
    input_file_path= args.input
    output_directory=args.output
    conf_number = int(args.conf_number) if args.conf_number is not None else 1
    main(input_file_path, output_directory, conf_number)
