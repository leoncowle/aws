#!/usr/local/bin/python3.9

import boto3
import argparse
import sys

parser = argparse.ArgumentParser(description='List AWS SSM parameters')
filterby = parser.add_mutually_exclusive_group(required=True)
filterby.add_argument('--beginswith', type=str, required=False, help='Show SSM parameters *beginning with* this string')
filterby.add_argument('--contains', type=str, default=False, help='Show SSM parameters *containing* this string')
parser.add_argument('--region', type=str, required=False, default="us-west-2", help="AWS region")
parser.add_argument('--showvalues', action='store_true', default=False)
args = parser.parse_args()

ssmclient = boto3.client(service_name="ssm", region_name=args.region)

if args.beginswith:
    optionStr = "BeginsWith"
    valueStr = args.beginswith
else:
    optionStr = "Contains"
    valueStr = args.contains

# Create a paginator iterator, to automatically page through all results
# No need to manual look for, keep track of, and provide "NextToken"s to each call
paginator = ssmclient.get_paginator('describe_parameters')
operation_parameters = {
    'ParameterFilters': [
        {
            'Key': 'Name',
            'Option': optionStr,
            'Values': [
                valueStr
            ]
        }
    ]
}
page_iterator = paginator.paginate(**operation_parameters)
totalParms = []
for page in page_iterator:
    totalParms += page['Parameters']

# Create a list of tuples containing param name and type
totalParmsNamesAndType = [(entry['Name'], entry['Type']) for entry in totalParms]

# Use max() to find the maximum string lenght of all the 'Name' entries
maxlen = len(max([x[0] for x in totalParmsNamesAndType], key=len))

# Print results
entriesLen = len(totalParmsNamesAndType)
if entriesLen:
    print(f'Found {entriesLen} entries matching your condition. They are:')
    for entry in totalParmsNamesAndType:
        print(f" - {entry[0]:{maxlen}}", end='')
        if args.showvalues:
            if entry[1] == "SecureString":
                # Don't look up values for encrypted parameters
                valStr = '<SecureString>'
            else:
                # Make another get_parameter call to obtain the value of the parameter
                valStr = ssmclient.get_parameter(Name=entry[0], WithDecryption=False)["Parameter"]['Value']
            print(f" (value: {valStr})", end='')
        print()
else:
    print('Did not find any entries matching your condition.')