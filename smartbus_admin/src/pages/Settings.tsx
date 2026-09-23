import { useState, useEffect } from 'react';
import { authService } from '../services/api';
import { Settings as SettingsIcon, User, Shield, Moon, LogOut, CheckCircle, AlertTriangle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Settings() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('profile');

  // Form State
  const [userProfile, setUserProfile] = useState<any>(null);
  const [fullName, setFullName] = useState('');

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const res = await authService.getMe();
      const user = res.data?.user;
      setUserProfile(user);
      setFullName(user?.full_name || 'Admin User');
    } catch (err: any) {
      console.error(err);
      if (err.response?.status === 401) {
        authService.logout();
        navigate('/login');
      } else {
        setError('Unable to load profile information.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await authService.syncUser({ full_name: fullName });
      setSuccessMsg('Settings updated successfully.');
      setTimeout(() => setSuccessMsg(null), 3000);
      await fetchProfile();
    } catch (err) {
      console.error(err);
      setError('Unable to update settings.');
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  if (loading && !userProfile) {
    return (
      <div className="py-20 text-center text-gray-500">
        Loading settings...
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center">
          <SettingsIcon className="w-6 h-6 mr-2 text-blue-600" />
          Settings
        </h1>
        <p className="text-sm text-gray-500 mt-1">Manage your administrative profile and preferences.</p>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg flex items-center shadow-sm border border-red-100">
          <AlertTriangle className="w-5 h-5 mr-2" />
          {error}
        </div>
      )}

      {successMsg && (
        <div className="bg-green-50 text-green-700 p-4 rounded-lg flex items-center shadow-sm border border-green-100">
          <CheckCircle className="w-5 h-5 mr-2" />
          {successMsg}
        </div>
      )}

      <div className="flex flex-col md:flex-row gap-6">
        {/* Navigation Sidebar */}
        <div className="w-full md:w-64 space-y-1">
          <button 
            onClick={() => setActiveTab('profile')} 
            className={`w-full flex items-center px-4 py-3 text-sm font-bold rounded-lg transition-colors ${activeTab === 'profile' ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-600' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 border-l-4 border-transparent'}`}
          >
            <User className="w-5 h-5 mr-3" /> Profile & Account
          </button>
          <button 
            onClick={() => setActiveTab('preferences')} 
            className={`w-full flex items-center px-4 py-3 text-sm font-bold rounded-lg transition-colors ${activeTab === 'preferences' ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-600' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 border-l-4 border-transparent'}`}
          >
            <Moon className="w-5 h-5 mr-3" /> Preferences
          </button>
          <button 
            onClick={() => setActiveTab('security')} 
            className={`w-full flex items-center px-4 py-3 text-sm font-bold rounded-lg transition-colors ${activeTab === 'security' ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-600' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 border-l-4 border-transparent'}`}
          >
            <Shield className="w-5 h-5 mr-3" /> Security
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 space-y-6">
          
          {activeTab === 'profile' && (
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
                <h2 className="font-bold text-gray-900">Admin Profile</h2>
                <span className="px-2.5 py-1 bg-green-100 text-green-800 text-xs font-bold rounded-full border border-green-200">
                  {userProfile?.status || 'ACTIVE'}
                </span>
              </div>
              <div className="p-6">
                <form onSubmit={handleSave} className="space-y-5">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div>
                      <label className="block text-sm font-bold text-gray-700 mb-1">Full Name</label>
                      <input
                        type="text"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        required
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition-colors"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-bold text-gray-700 mb-1">Email Address</label>
                      <input
                        type="email"
                        value={userProfile?.email || ''}
                        disabled
                        className="w-full px-4 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-500 cursor-not-allowed"
                      />
                      <p className="text-xs text-gray-400 mt-1">Email cannot be changed directly.</p>
                    </div>
                    <div>
                      <label className="block text-sm font-bold text-gray-700 mb-1">Role</label>
                      <input
                        type="text"
                        value={userProfile?.role || 'ADMIN'}
                        disabled
                        className="w-full px-4 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-500 font-bold cursor-not-allowed"
                      />
                    </div>
                  </div>
                  
                  <div className="pt-4 border-t border-gray-100 flex justify-end">
                    <button
                      type="submit"
                      disabled={saving || !fullName.trim()}
                      className="px-6 py-2 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center"
                    >
                      {saving ? 'Saving...' : 'Save Changes'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {activeTab === 'preferences' && (
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                <h2 className="font-bold text-gray-900">Application Preferences</h2>
              </div>
              <div className="p-6 space-y-6">
                
                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                  <div>
                    <h3 className="font-bold text-gray-900">Theme</h3>
                    <p className="text-sm text-gray-500">Currently fixed to Light Mode.</p>
                  </div>
                  <span className="text-sm text-gray-400 bg-gray-100 px-3 py-1 rounded border border-gray-200 font-bold">Light</span>
                </div>

                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                  <div>
                    <h3 className="font-bold text-gray-900">System Timezone</h3>
                    <p className="text-sm text-gray-500">Global SMARTBUS operations timezone.</p>
                  </div>
                  <span className="text-sm text-gray-700 font-mono font-bold bg-gray-100 px-3 py-1 rounded border border-gray-200">Asia/Kolkata</span>
                </div>

                <div className="flex items-center justify-between py-2">
                  <div>
                    <h3 className="font-bold text-gray-900">Notifications</h3>
                    <p className="text-sm text-gray-500">Push notifications and alerts.</p>
                  </div>
                  <span className="text-sm text-gray-400 bg-gray-100 px-3 py-1 rounded border border-gray-200 font-bold">System Default</span>
                </div>

              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                  <h2 className="font-bold text-gray-900">Security Information</h2>
                </div>
                <div className="p-6 space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
                      <div className="text-xs font-bold text-gray-500 mb-1">AUTHENTICATION</div>
                      <div className="font-bold text-gray-900">Firebase Authentication</div>
                    </div>
                    <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
                      <div className="text-xs font-bold text-gray-500 mb-1">AUTHORIZATION</div>
                      <div className="font-bold text-gray-900">Backend RBAC (Role-Based Access)</div>
                    </div>
                  </div>
                  
                  <div className="p-4 bg-blue-50/50 border border-blue-100 rounded-lg mt-4">
                    <div className="text-xs font-bold text-blue-600 mb-1">ACTIVE SESSION</div>
                    <div className="font-bold text-gray-900">Signed in as: {userProfile?.email}</div>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-red-200 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-red-100 bg-red-50">
                  <h2 className="font-bold text-red-800">Session Management</h2>
                </div>
                <div className="p-6 flex items-center justify-between">
                  <div>
                    <h3 className="font-bold text-gray-900">End Session</h3>
                    <p className="text-sm text-gray-500">Log out of your administrative account securely.</p>
                  </div>
                  <button 
                    onClick={handleLogout}
                    className="flex items-center px-4 py-2 bg-white border border-red-300 text-red-600 hover:bg-red-50 font-bold rounded-lg transition-colors"
                  >
                    <LogOut className="w-4 h-4 mr-2" /> Logout
                  </button>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
