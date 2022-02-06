#!/usr/bin/env python3

import datetime as dt
import math
import os

import boto3
from botocore.exceptions import ClientError

def start_instance(session, inst_id):
    ec2 = session.client("ec2")
    return func_the_instance(ec2.start_instances, inst_id)

def stop_instance(session, inst_id):
    ec2 = session.client("ec2")
    return func_the_instance(ec2.stop_instances, inst_id)

def func_the_instance(func, inst_id):
    try:
        func(InstanceIds=[inst_id], DryRun=True)
    except ClientError as e:
        if "DryRunOperation" not in str(e):
            raise
    
    try:
        response = func(InstanceIds=[inst_id], DryRun=False)
    except ClientError as e:
        raise e

    return response

# Input "h hours" or "d days" and output a timedelta
def build_timedelta(in_str):
    time_len_str, time_unit = in_str.split(" ")
    if time_unit.lower() not in ["hours", "days"]:
        raise RuntimeError(f"Invalid time length: {in_str}")
    td_dict = {time_unit.lower(): int(time_len_str)}
    return dt.timedelta(**td_dict)
    

# Returns "START" if the current day is a multiple of rate_days
# after the base_start_date + base_offset_days, and the time is after start_time
# but before end_time.  Otherwise returns "STOP"
#
# base_start_time : YYYY-MM-DD hh:mm+hh:mm  - Python datetime fromisoformat
# run_time : "h hours"
# rate : "d days"
def determine_stop_start(base_start_time_in, run_time_in, rate_in):
    base_start_time_unktz = dt.datetime.fromisoformat(base_start_time_in)
    base_start_time = base_start_time_unktz.astimezone(dt.timezone.utc)
    
    run_time = build_timedelta(run_time_in)
    rate = build_timedelta(rate_in)
    base_end_time = base_start_time + run_time

    now = dt.datetime.now(dt.timezone.utc)

    full_periods_past = math.floor((now - base_start_time) / rate)
    most_recent_start = (full_periods_past * rate) + base_start_time
    most_recent_end = (full_periods_past * rate) + base_end_time

    if most_recent_start <= now < most_recent_end:
        return "START"
    return "STOP"

def main(event, context):
    needed_vars = ["PROFILE", "REGION", "INSTANCE",
        "BASE_START_TIME", "RUN_TIME", "RATE"]
    in_vars = {var: os.environ.get(var) for var in needed_vars}

    sess = boto3.session.Session(region_name=in_vars["REGION"],
        profile_name=in_vars["PROFILE"])

    retval = None

    start_stop = determine_stop_start(in_vars["BASE_START_TIME"], 
        in_vars["RUN_TIME"], in_vars["RATE"])
    print(f"Preparing to: {start_stop}")

    if start_stop == "START":
        retval = start_instance(sess, in_vars["INSTANCE"])
    else:
        retval = stop_instance(sess, in_vars["INSTANCE"])

    print(f"Response: {retval}")

if __name__ == "__main__":
    main((), ())
