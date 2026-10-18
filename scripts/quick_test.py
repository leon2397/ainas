import requests
print(requests.get("http://localhost:8000/api/monitor/status").status_code)
print(requests.get("http://localhost:8000/api/plugins/").status_code)
print(requests.get("http://localhost:8000/api/enterprise/sso/status").status_code)
