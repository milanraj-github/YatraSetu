import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

const firebaseConfig = {
  apiKey: 'AIzaSyD_908d1t4wTuyLm15tL2rTigoy3rqLBcc',
  appId: '1:348875670834:android:3f5c707e32cbcf0dba432b',
  messagingSenderId: '348875670834',
  projectId: 'smart-bus-b4c7f',
  storageBucket: 'smart-bus-b4c7f.firebasestorage.app',
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
