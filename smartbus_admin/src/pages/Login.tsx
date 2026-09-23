import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/api';
import { Bus, ShieldAlert } from 'lucide-react';

const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      const result = await authService.login(email, password);
      if (result.success && result.data?.user?.role === 'ADMIN') {
        navigate('/');
      } else {
        setError('Unauthorized: You must be an ADMIN to access this portal.');
        authService.logout(); // clear token if it was invalid role
      }
    } catch (err: any) {
      console.error("Login Error:", err);
      if (err?.code === 'auth/invalid-credential' || err?.code === 'auth/user-not-found' || err?.code === 'auth/wrong-password') {
         setError("Invalid email or password.");
      } else if (err?.response?.status === 401 || err?.response?.status === 403) {
         setError("Unauthorized: Invalid permissions.");
      } else {
         setError('Authentication service is unavailable. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-slate-800 rounded-2xl shadow-xl overflow-hidden">
        <div className="p-8 text-center border-b border-slate-700">
          <div className="w-16 h-16 bg-brand-500 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-brand-500/30">
            <Bus className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">SMARTBUS</h1>
          <p className="text-slate-400 mt-2 text-sm uppercase tracking-widest font-semibold">Admin Control Panel</p>
        </div>
        
        <div className="p-8">
          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/50 rounded-lg flex items-start text-red-400">
              <ShieldAlert className="w-5 h-5 mr-3 flex-shrink-0 mt-0.5" />
              <p className="text-sm">{error}</p>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Admin Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-shadow"
                placeholder="admin@sode-edu.in"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-shadow"
                placeholder="Enter password"
              />
            </div>
            
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 bg-brand-500 hover:bg-brand-600 text-white font-semibold rounded-xl shadow-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center"
            >
              {loading ? (
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : 'Access Admin Panel'}
            </button>
          </form>
          
          <div className="mt-8 text-center">
            <p className="text-xs text-slate-500">
              Secured by SMARTBUS Identity
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
