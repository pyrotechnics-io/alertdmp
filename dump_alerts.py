#!/usr/bin/env python

import csv
import os
import time
import json
import argparse
from pandas import json_normalize
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
import logging

# GraphQL templates
query_policies = None
query_policy_conditions = None

# Http
max_retries = 10
retry_delay = 5

def setup_module_logger(name, log_level):
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


def load_templates():
    global query_policies
    global query_policy_conditions

    with open("policies.gql", 'r') as pol:
        query_policies = gql(pol.read())
    with open("policy_conditions.gql", 'r') as cond:
        query_policy_conditions = gql(cond.read())

def process(account_id, new_relic_api_key):
    global max_retries
    global retry_delay
    transport = RequestsHTTPTransport(
        url='https://api.newrelic.com/graphql',
        headers={'API-Key': new_relic_api_key},
        use_json=True,
    )
    client = Client(transport=transport, fetch_schema_from_transport=True)
    cursor = None
    all_policies = []
    csv_data = []

    logger.info("Looking for all configured policies")
    retries = max_retries
    while True:
        try:
            result = client.execute(query_policies, variable_values={"accountId": account_id, "cursor": cursor})
        except Exception as e:
            retries -= 1
            if retries == 0:
                logger.error("Maximum retries exceeded. Last error: {}", e)
                os._exit(-1)
            else:
                logger.debug("Retry {} on HTTP error: {}".format(retries, e))
            time.sleep(retry_delay)
            continue
        policies = result['actor']['account']['alerts']['policiesSearch']['policies']
        all_policies.extend(policies)
        cursor = result['actor']['account']['alerts']['policiesSearch']['nextCursor']
        if cursor is None:
            break

    for policy in all_policies:
        policy_id = policy['id']
        policy_name = policy['name']
        cursor = None
        logger.info("Looking for conditions inside policy: {}".format(policy_id))
        retries = max_retries
        while True:
            try:
                conditions_result = client.execute(query_policy_conditions, variable_values={"cursor": cursor, "policyId": policy_id, "accountId": account_id})
            except Exception as e:
                retries -= 1
                if retries == 0:
                    logger.error("Maximum retries exceeded. Last error: {}", e)
                    os._exit(-1)
                else:
                    logger.debug("Retry {} on HTTP error: {}".format(retries, e))
                time.sleep(retry_delay)
                continue
            conditions = conditions_result['actor']['account']['alerts']['nrqlConditionsSearch']['nrqlConditions']
            logger.debug(json.dumps(conditions, indent=4))
            # Need to add the policy name to all of them. 
            for c in conditions:
                c["policyName"] = policy_name
            csv_data.extend(conditions)
            cursor = conditions_result['actor']['account']['alerts']['nrqlConditionsSearch']['nextCursor']
            if cursor is None:
                break
    return csv_data

def get_args():
    parser = argparse.ArgumentParser(description="Alert configuration dumper")
    parser.add_argument("--account_id", required=True, help="Your New Relic account ID")
    parser.add_argument("--api_key", required=True, help="Your New Relic API key")
    parser.add_argument("--output_file", required=False, default="alert_policies.csv", help="Output file")
    parser.add_argument("--json", required=False, action='store_true', default=False, help="Dump json directly to file")
    parser.add_argument("--use_pandas", required=False, action='store_true', default=True, help="Use pandas for json normalization")
    parser.add_argument("--debug", required=False, action='store_true', default=False, help="Dump debug data")
    
    args = parser.parse_args()
    return args

def main():
    global logger
    args = get_args()
    if args.debug:
      logger = setup_module_logger(__name__, logging.DEBUG)
    else:
      logger = setup_module_logger(__name__, logging.INFO)
    account_id = int(args.account_id)
    api_key = args.api_key
    logger.info("Running on account {}".format(args.account_id))
    
    logger.info("Loading GraphQL templates")
    load_templates()
    if os.path.exists(args.output_file):
      logger.debug("Removing stale file")
      os.remove(args.output_file)
    logger.info("Collecting data ...")
    policy_data = process(account_id, api_key)

    if args.json:
        logger.info("Dumping to JSON")
        with open(args.output_file, 'w', newline='') as file:
            file.write(json.dumps(policy_data, indent=4))
    else:
        if args.use_pandas:
            logger.info("Dumping to CSV using pandas")
            df = json_normalize(policy_data, sep='.')
            df.to_csv(args.output_file, index=False)
        else:    
            logger.info("Dumping to CSV using csv module")
            with open(args.output_file, 'w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=policy_data[0].keys())
                writer.writeheader()
                writer.writerows(policy_data)

if __name__ == "__main__":
    main()
