import urllib.request
import urllib.parse
import http.cookiejar
import re

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. GET login page and extract CSRF token
resp = opener.open('http://127.0.0.1:8000/accounts/login/')
html = resp.read().decode('utf-8')
m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
if not m:
    print('Failed to find CSRF token')
    exit(1)
csrf_token = m.group(1)

# 2. POST login credentials for admin
login_data = urllib.parse.urlencode({
    'username': 'admin',
    'password': 'admin123',
    'csrfmiddlewaretoken': csrf_token
}).encode('utf-8')

req = urllib.request.Request(
    'http://127.0.0.1:8000/accounts/login/',
    data=login_data,
    headers={'Referer': 'http://127.0.0.1:8000/accounts/login/'}
)
resp = opener.open(req)
print(f"Login result: {resp.status} (Final URL: {resp.geturl()})")

# 3. Test key authenticated and public routes
routes = [
    '/',
    '/about/',
    '/contact/',
    '/api-docs/',
    '/audit-log/',
    '/dashboard/',
    '/crime-data/',
    '/crime-data/records/',
    '/crime-data/upload/',
    '/analysis/',
    '/location/',
    '/location/api/markers/',
    '/patterns/',
    '/ontology/',
    '/ontology/api/graph-data/',
    '/model-training/',
    '/prediction/',
    '/prediction/arima/',
    '/visualization/',
    '/reports/',
    '/notifications/',
    '/accounts/profile/',
    '/accounts/settings/'
]

all_pass = True
print("-" * 50)
for r in routes:
    try:
        res = opener.open(f'http://127.0.0.1:8000{r}', timeout=5)
        print(f"{r:<28} -> {res.status} OK")
    except Exception as e:
        print(f"{r:<28} -> FAILED: {e}")
        all_pass = False

print("-" * 50)
print(f"ALL TESTED ENDPOINTS PASSED: {all_pass}")
