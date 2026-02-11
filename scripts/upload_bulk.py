import sys
import requests

def upload(csv_path, api_base='http://127.0.0.1:8000/api'):
    url = f"{api_base}/admin/users/bulk_import/"
    with open(csv_path, 'rb') as f:
        files = {'file': (csv_path, f, 'text/csv')}
        r = requests.post(url, files=files)
        print('status', r.status_code)
        try:
            print(r.json())
        except Exception:
            print(r.text)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python upload_bulk.py path/to/users.csv [api_base]')
        sys.exit(1)
    csv = sys.argv[1]
    api = sys.argv[2] if len(sys.argv) > 2 else 'http://127.0.0.1:8000/api'
    upload(csv, api)
