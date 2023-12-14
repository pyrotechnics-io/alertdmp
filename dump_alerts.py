#!/usr/bin/env python

import csv
from pandas import json_normalize
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

# TODO: Change this!
account_id = 3493139
new_relic_api_key = 'NRAK-FJ4LZGDR25FECFSB5UBN6H2LXCN'

query_policies = gql("""
query getPolicyConditions($accountId: Int!) {
  actor {
    account(id: $accountId) {
      alerts {
        policiesSearch {
          policies {
            id
            name
            incidentPreference
          }
        }
      }
    }
  }
}
""")

query_policy_conditions = gql("""
query getPolicyConditions($accountId: Int!, $policyId: ID!) {
  actor {
    account(id: $accountId) {
      alerts {
        policy(id: $policyId) {
          id
          incidentPreference
          name
          accountId
        }
        nrqlConditionsSearch {
          nrqlConditions {
            id
            name
            nrql {
              evaluationOffset
            }
            runbookUrl
            signal {
              aggregationDelay
              aggregationMethod
              aggregationTimer
              aggregationWindow
              evaluationDelay
              evaluationOffset
              fillOption
              fillValue
              slideBy
            }
            type
            description
            enabled
            entity {
              alertSeverity
            }
            expiration {
              closeViolationsOnExpiration
              expirationDuration
              openViolationOnExpiration
            }
          }
        }
      }
    }
  }
}
""")


transport = RequestsHTTPTransport(
    url='https://api.newrelic.com/graphql',
    headers={'API-Key': new_relic_api_key},
    use_json=True,
)
client = Client(transport=transport, fetch_schema_from_transport=True)

result = client.execute(query_policies, variable_values={"accountId": account_id})
policies = result['actor']['account']['alerts']['policiesSearch']['policies']
csv_data = []

for policy in policies:
    policy_id = policy['id']
    conditions_result = client.execute(query_policy_conditions, variable_values={"policyId": policy_id, "accountId": account_id})
    conditions = conditions_result['actor']['account']['alerts']['nrqlConditionsSearch']['nrqlConditions']

    for condition in conditions:
        flattened_data = json_normalize(condition, sep='.')
        csv_data.append(flattened_data)

with open('alert_policies.csv', 'w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=csv_data[0].keys())
    writer.writeheader()
    writer.writerows(csv_data)

