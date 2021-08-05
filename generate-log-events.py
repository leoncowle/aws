#!/usr/local/bin/python3.9

## Script to dump some random data (from Bacon Ipsum -- hhhmmmm baaaacccooonnnn)
## Into a specified AWS CloudWatch log group & log stream
## Requirements to run:
##   The needed python modules (you'll need to install 'requests' and 'boto3')
##   Valid AWS credentials in environment variables and/or ~/.aws/credentials
## Created by: Leon Cowle <leon@leolizma.com>
## Changelog:
##   2021-08-04: v1.0 initial script
##   2021-08-05: v1.01 better error handling

import requests
import time
import boto3
from botocore.exceptions import ClientError
import argparse
import json
import sys

parser = argparse.ArgumentParser(description="Put log events into an AWS CloudWatch log group stream")
parser.add_argument("--count", type=int, required=False, default=5, help="Number of log events to create [default: 5]")
parser.add_argument("--groupname", type=str, required=True, help="Log group name")
parser.add_argument("--streamname", type=str, required=True, help="Log stream name")
parser.add_argument("--region", type=str, required=False, default="us-west-2", help="AWS region for log group")
parser.add_argument("--nostdout", action="store_true", help="Do not dump generated data to stdout as well")
parser.add_argument("--dontcreate", action="store_true", help="Do not create log group/stream if it doesn't exist")
args = parser.parse_args()

log_group_name = args.groupname
log_stream_name = args.streamname
count = args.count

# Test my credentials
try:
    sts = boto3.client(service_name="sts", region_name=args.region)
    sts.get_caller_identity()     # API call to test my AWS creds
except Exception as e:
    print("Error: Authentication failed when connecting to AWS.")
    print("Error: Please check your credentials...")
    print(f"Error: Message returned from AWS API call: {e}")
    sys.exit(1)

# Get a 'logs' boto3 client
client = boto3.client(service_name="logs", region_name=args.region)

events = []
for i in range(count):
    # Get some random data from Bacon Ipsum!
    r = requests.get("https://baconipsum.com/api/?type=all-meat&sentences=1&start-with-lorem=1")
    events.append({"timestamp": int(time.time()*1000), "message": r.json()[0]})

# Attempt to create log_group_name and log_stream_name. Silently ignore 'already exists' errors.
if not args.dontcreate:
    try:
        client.create_log_group(logGroupName=log_group_name)
    except client.exceptions.ResourceAlreadyExistsException as e:
        pass
    try:
        client.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
    except client.exceptions.ResourceAlreadyExistsException as e:
        pass

# Get the next expected uploadSequenceToken, by making a fake call, which will fail.
# But in failing, it will tell us what the next expectedSequenceToken is.
uploadSequenceToken = ""
try:
    client.put_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        logEvents=[
            {
                "timestamp": int(time.time()*1000),
                "message": "fake data"
            }
        ],
        sequenceToken=str(int(time.time()*1000))
    )
    # Force an exception, because we want/expect the above put_log_events to fail!
    assert False, "The 'fake' put_log_events call unexpectedly succeeded!"
except ClientError as e:
    if e.response["Error"]["Code"] == "InvalidSequenceTokenException":
        if "expectedSequenceToken" in e.response:
            # This error tells us what the next expectedSequenceToken is
            uploadSequenceToken = e.response["expectedSequenceToken"]
        elif "The next expected sequenceToken is: null" in e.response["Error"]["Message"]:
            # This error tells us that it doesn't want a sequenceToken (it's a new/empty log stream)
            uploadSequenceToken = None
        else:
            # Not sure there is a use-case where this 'else' can be reached, but just in case...
            print(f'The initial/"fake" put_log_events call failed with code "{e.response["Error"]["Code"]}" '
                  f'and message "{e.response["Error"]["Message"]}"')
            print("Exiting...")
            sys.exit(1)
    else:
        # Any other ClientError error other than InvalidSequenceTokenException
        print(f'The initial/"fake" put_log_events call failed with code "{e.response["Error"]["Code"]}" '
              f'and message "{e.response["Error"]["Message"]}"')
        print("Exiting...")
        sys.exit(1)
except (AssertionError, Exception) as e:
    print("The initial/'fake' put_log_events call either succeeded unexpectedly, or didn't fail with a ClientError.")
    print("This isn't an expected outcome, hence exiting...")
    print(f"Debug: Exception: {e}")
    sys.exit(1)

# Build args to be sent to put call
putArgs = {
    'logGroupName': log_group_name,
    'logStreamName': log_stream_name,
    'logEvents': events
}
if uploadSequenceToken is not None:
    # Log streams that already have data expect a sequenceToken
    putArgs['sequenceToken'] = uploadSequenceToken

try:
    response = client.put_log_events(**putArgs)
    if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
        print(f"Put log event API call failed with {response}")
        sys.exit(1)
except ClientError as e:
    print(f'The put_log_events call failed with code "{e.response["Error"]["Code"]}" '
          f'and message "{e.response["Error"]["Message"]}"')
    sys.exit(1)

if not args.nostdout:
    print(json.dumps(events, indent=4))

sys.exit(0)
