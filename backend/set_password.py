import firebase_admin
from firebase_admin import credentials, auth

cred = credentials.Certificate("/Users/sagars/Documents/BUS/backend/firebase-service-account.json")
firebase_admin.initialize_app(cred)

uid = "nMJMcTemKCMjtvqLjnFLvmyvm153"
auth.update_user(uid, password="password123")
print("Password updated for driver1@sode-edu.in to password123")
