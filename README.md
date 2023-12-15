# New Relic Alert Configuration Dumper

## Overview

This Python script, `Alert Configuration Dumper`, is designed to interact with the New Relic API to fetch and dump alert configurations. It retrieves alert policy data and policy conditions associated with an account on New Relic, and then outputs this data either in JSON format or as a CSV file.

## Features

- Fetch alert policy data and conditions from New Relic API.
- Output data in either JSON or CSV format.
- Option to use pandas for JSON normalization.
- Logging support for debugging and tracking the process.
- Command line arguments for flexibility and ease of use.

## Requirements

- Python 3.x
- `pandas` library (optional for JSON normalization)
- `gql` library for GraphQL support
- `requests` library for handling HTTP requests

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

- `--account_id`: Your New Relic account ID (required).
- `--api_key`: Your New Relic API key (required).
- `--output_file`: Specify the output file name (default: alert_policies.csv).
- `--json`: Output data in JSON format.
- `--use_pandas`: Use pandas for JSON normalization (default: True).
- `--debug`: Enable debug mode for additional logging (default: False).