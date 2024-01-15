#!/usr/bin/env python

import csv
import os
import time
import json
import argparse
from pathlib import Path
from pandas import json_normalize
from thefuzz import fuzz
import itertools
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from gql.transport.exceptions import TransportQueryError

import logging

# GraphQL templates
query_accounts = None
query_policies = None
query_policy_conditions = None

# Http
max_retries = 3
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
    global query_accountS
    global query_policies
    global query_policy_conditions

    with open("accounts.gql", 'r') as acc:
        query_accounts = gql(acc.read())
    with open("policies.gql", 'r') as pol:
        query_policies = gql(pol.read())
    with open("policy_conditions.gql", 'r') as cond:
        query_policy_conditions = gql(cond.read())

def query(client, query, parameters):
    global max_retries
    global retry_delay
    result = None
    retries = max_retries
    while True:
        try:
            result = client.execute(query, variable_values=parameters)
            return result
        except Exception as e:
            if retries == 0:
                logger.error("Maximum retries exceeded. Last error: {}", e)
                return None
            else:
                retries -= 1
                logger.debug("Retry {} on error: {}".format(retries, e))
            time.sleep(retry_delay)
            continue

def process(account_id, new_relic_api_key):
    transport = RequestsHTTPTransport(
        url='https://api.newrelic.com/graphql',
        headers={'API-Key': new_relic_api_key},
        use_json=True,
    )
    client = Client(transport=transport, fetch_schema_from_transport=True)
    cursor = None
    all_policies = []
    csv_data = []
    all_accounts = []

    if account_id:
        all_accounts.append(account_id)
    else:
        # Look for all accounts accessible by this key
        result = query(client, query_accounts, None)
        for acc in result['actor']['accounts']:
            all_accounts.append(acc['id'])

    logger.info(f"Looking into {len(all_accounts)} accounts ...")
    for account_id in all_accounts:
        logger.debug(f"Looking for configured policies on account {account_id}")
        retries = max_retries
        while True:
            result = query(client, query_policies, {"accountId": account_id, "cursor": cursor})
            policies = result['actor']['account']['alerts']['policiesSearch']['policies']
            all_policies.extend(policies)
            cursor = result['actor']['account']['alerts']['policiesSearch']['nextCursor']
            if cursor is None:
                break

        logger.debug("Looking for policies inside account: {}".format(account_id))
        for policy in all_policies:
            policy_id = policy['id']
            policy_name = policy['name']
            cursor = None
            logger.debug("Looking for conditions inside policy: {}".format(policy_id))
            while True:
                logger.debug("Querying account: {} policy: {}|{}".format(account_id, policy_id, policy_name))
                conditions_result = query(client, query_policy_conditions, {"cursor": cursor, "policyId": policy_id, "accountId": account_id})
                if conditions_result is None:
                    break # It was an un-recoverable error. Just move to the next policy
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

def post_process(policy_data):
    # Alert thresholds are a json list of values. These need to be expanded into columns instead
    for row in policy_data:
        thresholds = row["terms"]
        for index, term in enumerate(thresholds):
            for key, value in term.items():
                name = f"threshold.{index}.{key}"
                row[name] = value
    return policy_data

def get_args():
    parser = argparse.ArgumentParser(description="Alert configuration dumper")
    parser.add_argument("--account_id", required=False, help="Your New Relic Account ID (leave blank for all accounts)")
    parser.add_argument("--api_key", required=True, help="Your New Relic API key")
    parser.add_argument("--similarity", required=False, default=0, help="A percentage similarity threshold to filter against")
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
    
    account_id = None
    if args.account_id:
        account_id = int(args.account_id)

    api_key = args.api_key
    logger.info("Running on account {}".format(args.account_id))
    
    logger.info("Loading GraphQL templates")
    load_templates()
    logger.info("Collecting data ...")
    json_data = process(account_id, api_key)
    policy_data = post_process(json_data)

    if args.json:
        logger.info("Dumping to JSON")
        with open(Path(args.output_file).stem + '.json', 'w', newline='') as file:
            file.write(json.dumps(policy_data, indent=4))
    else:
        if args.use_pandas:
            logger.info("Dumping to CSV (pandas)")
            df = json_normalize(policy_data, sep='.')
            df.to_csv(args.output_file, index=False)
        else:    
            logger.info("Dumping to CSV")
            with open(args.output_file, 'w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=policy_data[0].keys())
                writer.writeheader()
                writer.writerows(policy_data)
                
    if int(args.similarity) > 0:
        logger.info(f"Discovering similar pairs")
        similar_pairs = []
        for row1, row2 in itertools.combinations(policy_data, 2):
            value1 = row1["nrql"]["query"]
            key1 = f"{row1['id']}:{row1['name']}"
            value2 = row2["nrql"]["query"]
            key2 = f"{row2['id']}:{row2['name']}"
            similarity_score = fuzz.ratio(value1, value2)
            if similarity_score >= int(args.similarity):
                similar_pairs.append({"first": key1, "second": key2, "score": similarity_score})
        logger.info(f"Sorting ...")
        sorted_data = sorted(similar_pairs, key=lambda x: x['score'], reverse=True)
        with open('similar.csv', 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=sorted_data[0].keys())
            writer.writeheader()
            writer.writerows(sorted_data)

if __name__ == "__main__":
    main()
