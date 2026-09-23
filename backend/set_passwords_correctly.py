import firebase_admin
from firebase_admin import credentials, auth

cred = credentials.Certificate("/Users/sagars/Documents/BUS/backend/firebase-service-account.json")
firebase_admin.initialize_app(cred)

auth.update_user("nMJMcTemKCMjtvqLjnFLvmyvm153", password="Driver1_Password123!")
auth.update_user("WfDs8WTQgLeZxcudBjR2LvUWKRW2", password="Driver2_Password123!")
auth.update_user("mQNCqZ3iIEhN36BfiEn4QTlkplB3", password="Driver3_Password123!")
print("Passwords restored to config defaults")
