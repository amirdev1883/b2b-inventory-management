import os
from urllib.request import Request, urlopen

host = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost").split(",")[0]
request = Request("http://127.0.0.1:8000/ready/", headers={"Host": host})
with urlopen(request, timeout=4) as response:
    if response.status != 200:
        raise SystemExit(1)
