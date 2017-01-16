#!/usr/bin/env python3
from shodanobject import ShodanObject
from base import dict_clean_empty
from base import ask_input_file
from base import ask_output_file
from base import ask_input_directory
from base import get_option_from_user
from base import create_output_directory
from base import ask_continue
import json
import os

print('---Shodan json converter---')
shodan = ShodanObject()
choice = get_option_from_user('File input or directory input?(f/d)', {'f', 'd'})
if choice is 'f':
    input_file = ask_input_file()
    str_path_output_file = ask_output_file('outputfiles/shodan/')
    with open(str_path_output_file, 'a') as output_file:
        for str_banner in input_file.open():
            banner = dict_clean_empty(json.loads(str_banner))
            shodan.to_es_convert(shodan, banner)
            output_file.write(json.dumps(banner) + '\n')
    print('Converted ' + str(input_file.as_posix()) + ' to ' + str_path_output_file)
elif choice is 'd':
    input_directory = ask_input_directory()
    output_directory = create_output_directory(input_directory)
    files_to_convert = []
    for file in os.listdir(input_directory):
        if file.endswith(".json"):
            files_to_convert.append(file)
    print('These files will be converted: ' + str(files_to_convert))
    print('Total number of files: ' + str(len(files_to_convert)))
    ask_continue()
    counter = 0
    for input_file in files_to_convert:
        counter += 1
        str_output_file = output_directory + '/' + input_file[:-5] + '-converted.json'
        print('\r' + 'Converting ' + input_file + '[' + str(counter) + '/' + str(len(files_to_convert)) + ']...', end='')
        with open(str_output_file, 'a') as output_file:
            for str_banner in open(input_directory + '/' + input_file, 'r'):
                banner = dict_clean_empty(json.loads(str_banner))
                shodan.to_es_convert(shodan, banner)
                output_file.write(json.dumps(banner) + '\n')
    print('\nConverted files written in ' + output_directory)
