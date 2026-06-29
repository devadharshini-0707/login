import app
print('imported app')
client = app.app.test_client()
response = client.get('/login')
print('status', response.status_code)
print(response.get_data(as_text=True)[:1000])
