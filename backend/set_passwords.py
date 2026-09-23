import firebase_admin
from firebase_admin import credentials, auth

cred = credentials.Certificate("/Users/sagars/Documents/BUS/backend/firebase-service-account.json")
firebase_admin.initialize_app(cred)

auth.update_user("WfDs8WTQgLeZxcudBjR2LvUWKRW2", password="password123")
auth.update_user("mQNCqZ3iIEhN36BfiEn4QTlkplB3", password="password123")
print("driver2 and driver3 passwords reset to password123")
