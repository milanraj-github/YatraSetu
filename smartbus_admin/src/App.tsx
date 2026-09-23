import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes as RoutesRouter, Route, Navigate } from 'react-router-dom';
import AdminLayout from './layouts/AdminLayout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Buses from './pages/Buses';
import Drivers from './pages/Drivers';
import Assignments from './pages/Assignments';
import Students from './pages/Students';
import Parents from './pages/Parents';
import ParentDetails from './pages/ParentDetails';
import Routes from './pages/Routes';
import Stops from './pages/Stops';
import Schedules from './pages/Schedules';
import Trips from './pages/Trips';
import LiveMap from './pages/LiveMap';
import Alerts from './pages/Alerts';
import Emergency from './pages/Emergency';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';
import { auth } from './services/firebase';
import { authService } from './services/api';
import { onAuthStateChanged } from 'firebase/auth';

// Protected Route Wrapper
const ProtectedRoute = ({ children, isAuth, userRole }: { children: React.ReactNode, isAuth: boolean, userRole: string | null }) => {
  if (!isAuth) {
    return <Navigate to="/login" replace />;
  }
  if (userRole !== 'ADMIN') {
    return <Navigate to="/login" replace />; // or an unauthorized page
  }
  return <>{children}</>;
};

function App() {
  const [isAuth, setIsAuth] = useState<boolean | null>(null);
  const [userRole, setUserRole] = useState<string | null>(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        try {
          // Verify role with backend
          const res = await authService.getMe();
          if (res.success && res.data?.user?.role === 'ADMIN') {
            setUserRole('ADMIN');
            setIsAuth(true);
          } else {
            // Not an admin
            await authService.logout();
            setIsAuth(false);
            setUserRole(null);
          }
        } catch (e) {
          console.error("Auth verification failed:", e);
          setIsAuth(false);
          setUserRole(null);
        }
      } else {
        setIsAuth(false);
        setUserRole(null);
      }
    });
    return () => unsubscribe();
  }, []);

  if (isAuth === null) {
    return <div className="min-h-screen bg-slate-900 flex items-center justify-center text-white">Loading SMARTBUS Identity...</div>;
  }

  return (
    <Router>
      <RoutesRouter>
        <Route path="/login" element={isAuth && userRole === 'ADMIN' ? <Navigate to="/" replace /> : <Login />} />
        
        <Route path="/" element={
          <ProtectedRoute isAuth={isAuth} userRole={userRole}>
            <AdminLayout />
          </ProtectedRoute>
        }>
          <Route index element={<Dashboard />} />
          <Route path="buses" element={<Buses />} />
          <Route path="drivers" element={<Drivers />} />
          <Route path="assignments" element={<Assignments />} />
          <Route path="students" element={<Students />} />
          <Route path="parents" element={<Parents />} />
          <Route path="parents/:id" element={<ParentDetails />} />
          <Route path="routes" element={<Routes />} />
          <Route path="stops" element={<Stops />} />
          <Route path="schedules" element={<Schedules />} />
          <Route path="trips" element={<Trips />} />
          <Route path="live" element={<LiveMap />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="emergency" element={<Emergency />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </RoutesRouter>
    </Router>
  );
}

export default App;
