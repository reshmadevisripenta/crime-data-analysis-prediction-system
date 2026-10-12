import urllib.request
import urllib.parse
import http.cookiejar
import re

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Fetch registration page
resp = opener.open('http://127.0.0.1:8000/accounts/register/')
html = resp.read().decode('utf-8')
csrf_token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)

# 2. Register new user
data = urllib.parse.urlencode({
    'csrfmiddlewaretoken': csrf_token,
    'first_name': 'Live',
    'last_name': 'Tester',
    'username': 'livetester_99',
    'email': 'livetester_99@police.gov',
    'role': 'analyst',
    'password1': 'LiveSecret123!',
    'password2': 'LiveSecret123!'
}).encode('utf-8')

req = urllib.request.Request(
    'http://127.0.0.1:8000/accounts/register/',
    data=data,
    headers={'Referer': 'http://127.0.0.1:8000/accounts/register/'}
)

resp2 = opener.open(req)
print('Registration response code:', resp2.status, 'Final URL:', resp2.geturl())

# 3. Test duplicate registration
# Fetch fresh CSRF
resp_fresh = opener.open('http://127.0.0.1:8000/accounts/register/')
html_fresh = resp_fresh.read().decode('utf-8')
csrf_fresh = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html_fresh).group(1)

data_dup = urllib.parse.urlencode({
    'csrfmiddlewaretoken': csrf_fresh,
    'first_name': 'Live',
    'last_name': 'Tester',
    'username': 'livetester_99',
    'email': 'livetester_99@police.gov',
    'role': 'analyst',
    'password1': 'LiveSecret123!',
    'password2': 'LiveSecret123!'
}).encode('utf-8')

req3 = urllib.request.Request(
    'http://127.0.0.1:8000/accounts/register/',
    data=data_dup,
    headers={'Referer': 'http://127.0.0.1:8000/accounts/register/'}
)
resp3 = opener.open(req3)
html3 = resp3.read().decode('utf-8')
print('Duplicate username error displayed:', 'This username is already taken.' in html3)
