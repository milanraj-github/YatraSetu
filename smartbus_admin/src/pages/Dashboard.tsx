import React, { useEffect, useState } from 'react';
import { Bus, Users, Activity } from 'lucide-react';
import { dashboardService } from '../services/api';

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState({ buses: 0, drivers: 0, trips: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await dashboardService.getStats();
        setStats(data);
      } catch (error) {
        console.error("Error loading stats", error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchStats();
  }, []);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-slate-800">Dashboard Overview</h1>
        <div className="text-sm text-slate-500">Live system status</div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard 
          title="Total Buses" 
          value={loading ? "..." : stats.buses.toString()} 
          icon={Bus} 
          color="bg-blue-500" 
        />
        <StatCard 
          title="Active Drivers" 
          value={loading ? "..." : stats.drivers.toString()} 
          icon={Users} 
          color="bg-emerald-500" 
        />
        <StatCard 
          title="Today's Trips" 
          value={loading ? "..." : stats.trips.toString()} 
          icon={Activity} 
          color="bg-indigo-500" 
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Buses Card */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
            <h2 className="text-lg font-semibold text-slate-800">Active Buses</h2>
          </div>
          <div className="p-6">
            <div className="flex flex-col items-center justify-center h-48 text-slate-400">
              <Bus className="w-12 h-12 mb-3 text-slate-300" />
              <p>Map loading functionality pending...</p>
            </div>
          </div>
        </div>

        {/* Recent Activity Card */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
            <h2 className="text-lg font-semibold text-slate-800">Recent Activity</h2>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              <div className="flex items-start">
                <div className="w-2 h-2 mt-2 rounded-full bg-emerald-500 mr-4"></div>
                <div>
                  <p className="text-sm font-medium text-slate-800">System initialized</p>
                  <p className="text-xs text-slate-500">Admin logged in to control panel</p>
                </div>
              </div>
              <div className="flex items-start">
                <div className="w-2 h-2 mt-2 rounded-full bg-blue-500 mr-4"></div>
                <div>
                  <p className="text-sm font-medium text-slate-800">Phase 2 API Connected</p>
                  <p className="text-xs text-slate-500">Successfully fetched stats from backend</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const StatCard = ({ title, value, icon: Icon, color }: { title: string, value: string, icon: any, color: string }) => {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex items-center">
      <div className={`${color} w-14 h-14 rounded-lg flex items-center justify-center text-white mr-4 shadow-md`}>
        <Icon className="w-7 h-7" />
      </div>
      <div>
        <p className="text-sm font-medium text-slate-500">{title}</p>
        <h3 className="text-3xl font-bold text-slate-800 mt-1">{value}</h3>
      </div>
    </div>
  );
};

export default Dashboard;
