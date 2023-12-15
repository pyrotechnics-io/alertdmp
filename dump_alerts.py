#!/usr/bin/env python

import csv
import os
import argparse
from pandas import json_normalize
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

query_policies = None
query_policy_conditions = None


def load_templates():
    global query_policies
    global query_policy_conditions

    with open("policies.gql", 'r') as pol:
        query_policies = gql(pol.read())
    with open("policy_conditions.gql", 'r') as cond:
        query_policy_conditions = gql(cond.read())

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

    while True:
        result = client.execute(query_policies, variable_values={"accountId": account_id, "cursor": cursor})
        policies = result['actor']['account']['alerts']['policiesSearch']['policies']
        all_policies.extend(policies)
        if result['actor']['account']['alerts']['policiesSearch']['nextCursor'] is None:
            break

    for policy in all_policies:
        policy_id = policy['id']
        policy_name = policy['name']
        cursor = None
        while True:
            conditions_result = client.execute(query_policy_conditions, variable_values={"cursor": cursor, "policyId": policy_id, "accountId": account_id})
            conditions = conditions_result['actor']['account']['alerts']['nrqlConditionsSearch']['nrqlConditions']
            # Need to add the policy name to all of them. 
            for c in conditions:
                c["policyName"] = policy_name
            csv_data.extend(conditions)
            if conditions_result['actor']['account']['alerts']['nrqlConditionsSearch']['nextCursor'] is None:
                break
    return csv_data

def get_args():
    parser = argparse.ArgumentParser(description="Alert configuration dumper")
    parser.add_argument("--account_id", required=True, help="Your New Relic account ID")
    parser.add_argument("--api_key", required=True, help="Your New Relic API key")
    parser.add_argument("--output_file", required=False, default="alert_policies.csv", help="Output file")
    parser.add_argument("--use_pandas", required=False, default=True, help="Use pandas for json normalization")
    
    args = parser.parse_args()
    return args

def main():
    args = get_args()
    account_id = int(args.account_id)
    api_key = args.api_key
    load_templates()
    if os.path.exists(args.output_file):
      os.remove(args.output_file)
    policy_data = process(account_id, api_key)

    if args.use_pandas:
        df = json_normalize(policy_data, sep='.')
        df.to_csv(args.output_file, index=False)
    else:    
        with open(args.output_file, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=policy_data[0].keys())
            writer.writeheader()
            writer.writerows(policy_data)

if __name__ == "__main__":
    main()
