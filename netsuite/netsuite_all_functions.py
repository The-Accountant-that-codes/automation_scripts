import os
from dotenv import load_dotenv
import requests
from requests_oauthlib import OAuth1

## Get env variables
# Get the current working directory
current_directory = os.getcwd()

# Construct the path to the .env file in the parent directory
env_path = os.path.join(current_directory, '..','.env')

# Load the environment variables from the .env file
load_dotenv(dotenv_path=env_path)

# NS Credentials
NS_REALM_ID = os.getenv('NS_PROD_REALM_ID')
NS_COMPANY_ID = os.getenv('NS_PROD_COMPANY_ID')
NS_CLIENT_KEY = os.getenv('NS_PROD_CLIENT_KEY')
NS_CLIENT_SECRET = os.getenv('NS_PROD_CLIENT_SECRET')
NS_TOKEN_ID = os.getenv('NS_PROD_TOKEN_ID')
NS_TOKEN_SECRET = os.getenv('NS_PROD_TOKEN_SECRET')

# Authenticate to NetSuite
netsuite_auth = OAuth1(
    client_key=NS_CLIENT_KEY,
    client_secret=NS_CLIENT_SECRET,
    resource_owner_key=NS_TOKEN_ID,
    resource_owner_secret=NS_TOKEN_SECRET,
    signature_method='HMAC-SHA256',
    signature_type='AUTH_HEADER',
    realm=NS_REALM_ID
)

# NetSuite helper functions

def fetch_all_netsuite_records(auth, endpoint: str):
    """
    Fetch all records from a NetSuite REST API endpoint with pagination support.

    Args:
        endpoint (str): e.g. 'account', 'vendor', 'transaction'

    Returns:
        List of all record items.
    """
    base_url = f"https://{NS_COMPANY_ID}.suitetalk.api.netsuite.com/services/rest/record/v1"
    url = f"{base_url}/{endpoint}"

    all_items = []
    offset = 0

    while True:
        paged_url = f"{url}?offset={offset}"
        response = requests.get(paged_url, auth=auth)

        if response.status_code != 200:
            print(f"Request failed: {response.status_code}")
            print(response.text)
            break

        data = response.json()
        items = data.get("items", [])
        all_items.extend(items)

        if not data.get("hasMore", False):
            break

        offset += len(items)

    return all_items

def fetch_all_dataset_records(auth, dataset_id: str, limit: int = 1000):
    """
    Fetch all records from a SuiteAnalytics Dataset using NetSuite's REST API with pagination.

    Args:
        auth: OAuth1 authentication object.
        dataset_id (str): The internal ID of the dataset (e.g., 'custdataset_enterprise_revenue').
        limit (int): Number of records per page (max 1000 is typical).

    Returns:
        list: All dataset records.
    """
    base_url = f"https://{NS_COMPANY_ID}.suitetalk.api.netsuite.com"
    endpoint = f"/services/rest/query/v1/dataset/{dataset_id}/result"
    
    offset = 0
    all_items = []

    while True:
        url = f"{base_url}{endpoint}?limit={limit}&offset={offset}"
        response = requests.get(url, auth=auth)

        if response.status_code != 200:
            print(f"Failed to fetch data (offset {offset}): {response.status_code}")
            print(response.text)
            break

        data = response.json()
        items = data.get("items", [])
        all_items.extend(items)

        if not data.get("hasMore"):
            break

        offset += limit

    return all_items

def fetch_record_by_id(auth, endpoint: str, record_id: str):
    """
    Fetch a single NetSuite record by its ID.

    Args:
        endpoint (str): e.g. 'account', 'vendor', 'transaction'
        record_id (str): NetSuite internal ID of the record

    Returns:
        dict: Record data if successful, None otherwise
    """
    base_url = f"https://{NS_COMPANY_ID}.suitetalk.api.netsuite.com/services/rest/record/v1"
    url = f"{base_url}/{endpoint}/{record_id}"

    response = requests.get(url, auth=auth)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Request failed with status {response.status_code}")
        print(response.text)
        return None
    
def run_suiteql_query(auth, query_string: str):
    """
    Run a paginated SuiteQL query using NetSuite's REST API.

    Args:
        auth: OAuth1 auth object
        query_string (str): A valid SuiteQL query string (without LIMIT/OFFSET)

    Returns:
        list: All matching records
    """

    base_url = f"https://{NS_COMPANY_ID}.suitetalk.api.netsuite.com/services/rest/query/v1/suiteql"
    headers = {
        "Content-Type": "application/json",
        "Prefer": "transient"
    }

    all_items = []
    offset = 0
    limit = 1000

    while True:
        # Use query parameters, not SQL syntax
        url = f"{base_url}?limit={limit}&offset={offset}"
        payload = { "q": query_string }

        response = requests.post(url, json=payload, auth=auth, headers=headers)

        if response.status_code == 200:
            items = response.json().get("items", [])
            all_items.extend(items)

            if len(items) < limit:
                break  # No more records to fetch

            offset += limit
        else:
            print(f"SuiteQL query failed at offset {offset}: {response.status_code}")
            print(response.text)
            break

    return all_items

def create_netsuite_record(auth, endpoint: str, payload: dict):
    """
    Create a new record in NetSuite via REST API.

    Args:
        endpoint (str): e.g. 'account', 'vendor', 'customRecord1'
        payload (dict): The JSON data to create the record

    Returns:
        dict: The created record data if successful, None otherwise
    """
    base_url = f"https://{NS_COMPANY_ID}.suitetalk.api.netsuite.com/services/rest/record/v1"
    url = f"{base_url}/{endpoint}"

    response = requests.post(url, json=payload, auth=auth)

    if response.status_code in (200, 201):
        result = response.json()
        record_id = result.get("id")
        print(f"Record created: {endpoint}/{record_id}")
        return result

    elif response.status_code == 204:
        location = response.headers.get("Location")
        if location:
            record_id = location.rstrip("/").split("/")[-1]
            print(f"Record created (204): {endpoint}/{record_id}")
            return {"id": record_id}
        else:
            print("Record created (204), but no Location header provided.")
            return {}

    else:
        print(f"Record creation failed: {response.status_code}")
        print(response.text)
        return None
    

def update_netsuite_record(auth, endpoint: str, record_id: str, payload: dict):
    """
    Update an existing NetSuite record using REST API (PATCH).

    Args:
        auth: OAuth1 auth object
        endpoint (str): e.g. 'customer', 'vendor', 'account'
        record_id (str): Internal ID of the record to update
        payload (dict): Fields and values to update

    Returns:
        dict or None: Updated record data if available, or None
    """
    base_url = f"https://{NS_COMPANY_ID}.suitetalk.api.netsuite.com/services/rest/record/v1"
    url = f"{base_url}/{endpoint}/{record_id}"

    response = requests.patch(url, json=payload, auth=auth)

    if response.status_code in (200, 201):
        return response.json()
    elif response.status_code == 204:
        print(f"Record {record_id} updated (204 No Content), but NetSuite returned no response body.")
        return {}
    else:
        print(f"Update failed: {response.status_code}")
        print(response.text)
        return None

def delete_netsuite_record(auth, endpoint: str, record_id: str):    
    """
    Delete a NetSuite record using REST API.

    Args:
        auth: OAuth1 auth object
        endpoint (str): e.g. 'customer', 'vendor', 'account'
        record_id (str): Internal ID of the record to delete

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    base_url = f"https://{NS_COMPANY_ID}.suitetalk.api.netsuite.com/services/rest/record/v1"
    url = f"{base_url}/{endpoint}/{record_id}"

    response = requests.delete(url, auth=auth)

    if response.status_code == 204:
        print(f"Record {record_id} deleted successfully.")
        return True
    else:
        print(f"Deletion failed: {response.status_code}")
        print(response.text)
        return False

