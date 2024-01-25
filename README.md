# New Relic Alert Analyser

## Overview

The script is crafted to interface with the New Relic API, enabling it to gather and export alert configuration details. It accomplishes this by pulling data related to alert policies and their conditions from a specified New Relic account. Once retrieved, the script can output this information in either JSON or CSV format. Its primary function is to analyze these files to identify and flag any redundancy or duplicates among the alert conditions for additional scrutiny.

## Features

- Fetch alert policy data and conditions from New Relic API.
- Output data in either JSON or CSV format.
- Option to use pandas for JSON normalization.
- Logging support for debugging and tracking the process.
- Command line arguments for flexibility and ease of use.

## Requirements

### Python 3.x
- `pandas` library: Used for JSON normalization. 
- `gql` library: Provides GraphQL support.
- `requests` library: Handles HTTP requests.
- `scikit-learn` library: Used for performing clustering.
- `backoff` library: Implements backoff algorithms.
- `numpy`: Essential for numerical computations.
- `thefuzz`: Another library for fuzzy string matching.


## Installation

Before running the script, ensure you have Python installed. Then, install the required dependencies:

```bash
pip install pandas gql requests
```

## Usage

The script is executed from the command line with several options:

```bash
./dump_alerts.py --account_id YOUR_ACCOUNT_ID --api_key YOUR_API_KEY [OPTIONS]
```

### Options

- `--account_id`: Your New Relic Account ID (leave blank for all accounts). Optional.
- `--api_key`: Your New Relic API key. Required.
- `--similarity`: A percentage similarity threshold to filter against (default: 0). Optional.
- `--output_file`: Specify the output file name (default: alert_policies.csv). Optional.
- `--json`: Dump JSON directly to file. If enabled, outputs data in JSON format (default: False). Optional.
- `--purge_cache`: Purge local cache of data and requery via API (default: False). Optional.
- `--use_pandas`: Use pandas for JSON normalization (default: True). Optional.
- `--debug`: Enable debug mode for additional logging (default: False). Optional.
