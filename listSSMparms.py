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

# Make an initial call, which will either
# return all the results we need,
# or some of the results and a NextToken (to get more results),
# or zero results and a NextToken (to start getting results)
try:
    parms = ssmclient.describe_parameters(
        ParameterFilters=[
            {
                'Key': 'Name',
                'Option': optionStr,
                'Values': [
                    valueStr
                ]
            },
        ],
        MaxResults=50
    )
except Exception as e:
    print(f'AWS call failed with: {e}')
    sys.exit(0)

totalParms = parms['Parameters']
NextToken = parms.get('NextToken', None)
while NextToken:
    # AWS is telling us there are more results to be retrieved
    parms = ssmclient.describe_parameters(
        ParameterFilters=[
            {
                'Key': 'Name',
                'Option': optionStr,
                'Values': [
                    valueStr
                ]
            },
        ],
        MaxResults=50,
        NextToken=NextToken
    )
    NextToken = parms.get('NextToken', None)
    totalParms += parms['Parameters']

totalParmsNamesAndType = [(entry['Name'], entry['Type']) for entry in totalParms]
maxlen = len(max([x[0] for x in totalParmsNamesAndType], key=len))
entriesLen = len(totalParmsNamesAndType)
if entriesLen:
    print(f'Found {entriesLen} entries matching your condition. They are:')
    for entry in totalParmsNamesAndType:
        print(f" - {entry[0]:{maxlen}}", end='')
        if args.showvalues:
            if entry[1] == "SecureString":
                valStr = '<SecureString>'
            else:
                valStr = ssmclient.get_parameter(Name=entry[0], WithDecryption=False)["Parameter"]['Value']
            print(f" (value: {valStr})", end='')
        print()
else:
    print('Did not find any entries matching your condition.')