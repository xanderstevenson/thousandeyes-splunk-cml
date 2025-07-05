import requests
import json
import time
import urllib3

# Suppress insecure HTTPS request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# TE API settings
TE_API_TOKEN = '<YOUR THOUSANDEYES API TOKEN>'
TE_API_URL = 'https://api.thousandeyes.com/v7/tests'
TE_API_RESULTS_BASE = 'https://api.thousandeyes.com/v7/test-results'

# Splunk HEC settings
SPLUNK_HEC_URL = '<YOUR SPLUNK URL>/services/collector/event'
SPLUNK_TOKEN = '<SPLUNK HEC TOKEN>'

splunk_headers = {
    'Authorization': f'Splunk {SPLUNK_TOKEN}',
    'Content-Type': 'application/json'
}

headers = {
    'Authorization': f'Bearer {TE_API_TOKEN}',
    'Accept': 'application/json'
}

# List of test IDs to include (only working ones)
VALID_TEST_IDS = {
    '<INSERT TEST ID FROM TE WEB UI>',  # server-1 web
    '<INSERT TEST ID FROM TE WEB UI>',  # API Test for Cisco Umbrella
    '<INSERT TEST ID FROM TE WEB UI>',  # ubuntu-te TCP Ping google.com:80
}

def fetch_te_tests():
    try:
        resp = requests.get(TE_API_URL, headers=headers, verify=False)
        resp.raise_for_status()
        tests = resp.json().get('tests', [])
        return [test for test in tests if test.get('testId') in VALID_TEST_IDS]
    except Exception as e:
        print(f"[ERROR] Failed to fetch TE tests: {e}")
        return []


def fetch_test_results(test):
    test_id = test.get('testId')
    test_type = test.get('type')
    if not test_id or not test_type:
        print(f"[WARN] Missing testId or type for test {test.get('testName')}")
        return None

    endpoint_map = {
        'agent-to-server': 'network',
        'http-server': 'http-server',
        'page-load': 'page-load',
        'api': 'api'
    }

    endpoint_suffix = endpoint_map.get(test_type)
    if not endpoint_suffix:
        print(f"[WARN] Unknown test type '{test_type}' for test {test.get('testName')}")
        return None

    url = f"{TE_API_RESULTS_BASE}/{test_id}/{endpoint_suffix}"
    try:
        resp = requests.get(url, headers=headers, verify=False)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[ERROR] Could not get result for test {test_id}: {e}")
        return None


def evaluate_pass_fail(test, results_data, health_threshold=0.95, api_txn_threshold=1000):
    test_type = test.get('type')
    test_id = test.get('testId')
    test_name = test.get('testName')

    if not results_data or 'results' not in results_data:
        print(f"[INFO] No result payload for test {test_name} (ID: {test_id})")
        return "NO_RESULTS"

    results = results_data['results']
    if not results or not isinstance(results, list):
        print(f"[INFO] No recent results for test {test_name} (ID: {test_id})")
        return "NO_RESULTS"

    result = results[0]
    print(f"[DEBUG] Raw results for {test_name} (ID: {test_id}):\n{json.dumps(result, indent=2)}")

    try:
        # Check for freshness
        if 'endTime' in result:
            now_epoch = int(time.time())
            if now_epoch - result['endTime'] > 600:
                print(f"[INFO] Result too old for test {test_name}")
                return "NO_RESULTS"

        if 'healthScore' in result:
            return "PASS" if result['healthScore'] >= health_threshold else "FAIL"

        if test_type == 'http-server':
            code = result.get('responseCode')
            error = result.get('errorType', '').lower()
            return "PASS" if code == 200 and error in ['', 'none'] else "FAIL"

        if test_type == 'api':
            txn_time = result.get('apiTransactionTime')
            return "PASS" if txn_time is not None and txn_time < api_txn_threshold else "FAIL"

        if test_type == 'agent-to-server':
            loss = result.get('loss')
            return "PASS" if loss == 0 else "FAIL"

        return "FAIL"

    except Exception as e:
        print(f"[ERROR] Failed to evaluate result for test {test_name} (ID: {test_id}): {e}")
        return "FAIL"


def send_to_splunk(event):
    payload = {
        "event": event,
        "sourcetype": "te:test",
        "host": "ubuntu-te",
        "time": time.time()
    }
    try:
        resp = requests.post(SPLUNK_HEC_URL, headers=splunk_headers, data=json.dumps(payload), verify=False)
        resp.raise_for_status()
        print(f"[SENT] {event.get('testName')} (ID: {event.get('testId')}) - Status: {event.get('status')}")
    except Exception as e:
        print(f"[ERROR] Failed to send to Splunk for test '{event.get('testName')}': {e}")


def main():
    tests = fetch_te_tests()
    if not tests:
        print("No tests found.")
        return

    print("Found Tests:")
    for test in tests:
        print(f"  - {test.get('testName')} (ID: {test.get('testId')}) Type: {test.get('type')}")

    for test in tests:
        results_data = fetch_test_results(test)
        status = evaluate_pass_fail(test, results_data)

        event = {
            'testId': test.get('testId'),
            'testName': test.get('testName'),
            'type': test.get('type'),
            'status': status,
            'results': results_data.get('results') if results_data else {}
        }

        send_to_splunk(event)


if __name__ == "__main__":
    main()
