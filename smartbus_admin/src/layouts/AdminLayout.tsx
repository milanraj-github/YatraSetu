import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Bus, 
  Users, 
  Map, 
  MapPin, 
  Calendar, 
  Route, 
  Activity, 
  AlertTriangle, 
  Settings,
  LogOut,
  Radio
} from 'lucide-react';
import { authService } from '../services/api';

const AdminLayout: React.FC = () => {
  const navigate = useNavigate();

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Buses', path: '/buses', icon: Bus },
    { name: 'Drivers', path: '/drivers', icon: Users },
    { name: 'Students', path: '/students', icon: Users },
    { name: 'Parents', path: '/parents', icon: Users },
    { name: 'Assignments', path: '/assignments', icon: Route },
    { name: 'Routes', path: '/routes', icon: Map },
    { name: 'Stops', path: '/stops', icon: MapPin },
    { name: 'Schedules', path: '/schedules', icon: Calendar },
    { name: 'Trips', path: '/trips', icon: Activity },
    { name: 'Live Map', path: '/live', icon: Radio },
    { name: 'Alerts', path: '/alerts', icon: AlertTriangle },
    { name: 'Emergency', path: '/emergency', icon: AlertTriangle, danger: true },
    { name: 'Analytics', path: '/analytics', icon: Activity },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];

  return (
    <div className="flex h-screen bg-slate-100 font-sans text-slate-800">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col">
        <div className="p-6 border-b border-slate-800">
          <h1 className="text-2xl font-bold tracking-tight text-brand-500">
            SMART<span className="text-white">BUS</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1 uppercase tracking-wider">Admin Control Panel</p>
        </div>
        
        <nav className="flex-1 overflow-y-auto py-4">
          <ul className="space-y-1 px-3">
            {navItems.map((item) => (
              <li key={item.name}>
                <NavLink
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                      isActive 
                        ? 'bg-brand-500/10 text-brand-500' 
                        : item.danger 
                          ? 'text-red-400 hover:bg-slate-800 hover:text-red-300' 
                          : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                    }`
                  }
                >
                  <item.icon className="w-5 h-5 mr-3 flex-shrink-0" />
                  {item.name}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <header className="bg-white border-b border-slate-200 h-16 flex items-center justify-between px-6 flex-shrink-0">
          <div className="flex items-center text-slate-500">
            {/* Breadcrumb placeholder or global search could go here */}
            <span className="font-medium">System Overview</span>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center text-brand-600 font-bold">
                A
              </div>
              <span className="text-sm font-medium text-slate-700">Admin</span>
            </div>
            <button 
              onClick={handleLogout}
              className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition-colors"
              title="Logout"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-auto bg-slate-50 p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default AdminLayout;
