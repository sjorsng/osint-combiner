from elasticsearch import Elasticsearch
from elasticsearch import exceptions
import configparser
from netaddr import IPNetwork
import re
import string
import sys
from pathlib import Path
import json

config = configparser.ConfigParser()
config.read("config.ini")
CENSYS_API_ID = (config['SectionOne']['CENSYS_API_ID'])
CENSYS_API_KEY = (config['SectionOne']['CENSYS_API_KEY'])
SHODAN_API_KEY = (config['SectionOne']['SHODAN_API_KEY'])
ES_IP = (config['SectionOne']['ELASTICSEARCH_IP'])
nrOfResults = 0


def es_get_all_ips(str_existing_index):
    """Returns list of list_of_ips stored in given Elasticsearch index"""
    list_ips = []
    es = Elasticsearch(([{'host': ES_IP}]))
    count = es.count(index=str_existing_index)['count']
    res = es.search(index=str_existing_index,
                    body={"size": 0, "aggs": {"all_ip": {"terms": {"field": "ip", "size": count}}}})
    for key in res['aggregations']['all_ip']['buckets']:
        list_ips.append(key['key'])
    return list_ips


def exists_es_index(str_valid_index):
    """Return if given index string exists in ElasticSearch cluster"""
    connection_attempts = 0
    while connection_attempts < 3:
        try:
            es = Elasticsearch(([{'host': ES_IP}]))
            es_indices = es.indices
            return es_indices.exists(index=str_valid_index)
        except exceptions.ConnectionTimeout:
            connection_attempts += 1
    print('Elasticsearch connection timeout, exiting now...')
    sys.exit(1)


def get_cidr_from_user_input():
    """Parses one CIDR from user input and returns IPNetwork"""
    ip_or_cidr = '0'
    while not isinstance(ip_or_cidr, IPNetwork):
        try:
            ip_or_cidr = IPNetwork(input('IP/CIDR: '))
        except:
            print('Not a valid IP/CIDR.')
    return ip_or_cidr


def parse_all_cidrs_from_file(file_path):
    """Returns set of CIDR strings from given file"""
    output = set()
    while not output:
        with open(file_path) as f:
            output = re.findall('(?:\d{1,3}\.){3}\d{1,3}(?:/\d\d?)?', f.read())
            print('CIDRs in file: ' + str(len(output)))
    return output


def is_valid_file_name(str_input):
    """Returns if str is valid file name. May only contain: ascii_lowercase, digits, dot, dash, underscore"""
    allowed = set(string.ascii_lowercase + string.digits + '.-_')
    if str_input is not '':
        return set(str_input) <= allowed
    return False


def is_valid_es_index_name(str_input):
    """Returns if str is valid Elasticsearch index name. May only contain: ascii_lowercase, digits, dash, underscore"""
    allowed = set(string.ascii_lowercase + string.digits + '-_')
    if str_input is not '':
        return set(str_input) <= allowed
    return False


def dict_add_source_prefix(obj, source_str, shodan_protocol_str=''):
    """Return dict where any non-nested element (except 'ip and ip_int') is prefixed by the OSINT source name"""
    keys_not_source_prefixed = ['ip', 'asn', 'ip_int']
    # These will still have the source prefixed
    shodan_keys_not_port_prefixed = ['asn', 'data', 'ip', 'ipv6 port', 'hostnames', 'domains', 'location',
                                'location.area_code', 'location.city', 'location.country_code', 'location.country_code3',
                              'location.country_name', 'location.dma_code', 'location.latitude', 'location.longitude',
                              'location.postal_code', 'location.region_code', 'opts', 'org', 'isp', 'os', 'transport',
                              'protocols']
    for key in obj:
        # prefix all non-nested elements except ip and ip_int
        if '.' not in key and key not in keys_not_source_prefixed:
            # if other OSINT than Shodan, just prefix source
            if shodan_protocol_str is '':
                new_key = key.replace(key, (source_str + "." + key))
            # if shodan
            else:
                # just prefix source if general shodan key
                if key in shodan_keys_not_port_prefixed:
                    new_key = key.replace(key, (source_str + "." + key))
                # prefix source AND shodan.module (protocol) if protocol-specific key
                else:
                    new_key = key.replace(key, (source_str + "." + shodan_protocol_str + '.' + key))
            if new_key != key:
                obj[new_key] = obj[key]
                del obj[key]
    return obj


def print_json_tree(df, indent='  '):
    """Prints tree structure of given dict for test/debug purposes"""
    for key in df.keys():
        print(indent+str(key))
        if isinstance(df[key], dict):
            print_json_tree(df[key], indent + '   ')


def dict_clean_empty(d):
    """Returns dict with all empty elements removed, value 0 retained"""
    if not isinstance(d, (dict, list)):
        return d
    if isinstance(d, list):
        return [v for v in (dict_clean_empty(v) for v in d) if v]
    return {k: v for k, v in ((k, dict_clean_empty(v)) for k, v in d.items()) if v or v == 0}


def ask_input_file():
    """Return existing file from user input"""
    input_file = Path('')
    input_file_path = ''
    while not input_file.is_file():
        input_file_path = input('Input file (with path from project root):')
        input_file = Path(input_file_path)
    return input_file


def ask_output_file(str_prefix_output_file):
    """Return valid file path string from user input """
    str_name_output_file = ''
    while not is_valid_file_name(str_name_output_file):
        str_name_output_file = input('Output file:' + str_prefix_output_file)
    return str_prefix_output_file + str_name_output_file


class ConcatJSONDecoder(json.JSONDecoder):
    """Returns list of dicts from given string containing multiple root JSON objects"""
    # shameless copy paste from element/decoder.py
    FLAGS = re.VERBOSE | re.MULTILINE | re.DOTALL
    WHITESPACE = re.compile(r'[ \t\n\r]*', FLAGS)

    def decode(self, s, _w=WHITESPACE.match):
        s_len = len(s)
        objs = []
        end = 0
        while end != s_len:
            obj, end = self.raw_decode(s, idx=_w(s, end).end())
            end = _w(s, end).end()
            objs.append(obj)
        return objs



