import React, { useEffect, useState } from 'react';
import { driverService, busService } from '../services/api';
import { Users, Plus, Search, Filter, AlertTriangle, X, ShieldAlert, Bus as BusIcon, History } from 'lucide-react';

interface Driver {
  id: number;
  firebase_uid: string;
  email: string;
  full_name: string;
  is_email_verified: boolean;
  status: string;
  created_at: string;
}

interface Bus {
  id: number;
  bus_number: string;
  registration_number: string;
  capacity: number;
  status: string;
}

interface Assignment {
  id: number;
  driver_id: number;
  bus_id: number;
  status: string;
  assigned_from: string;
  assigned_until: string | null;
}

const Drivers: React.FC = () => {
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [buses, setBuses] = useState<Bus[]>([]);
  
  // To avoid N+1 requests in the list, we would ideally have the backend include the current assignment in the list.
  // Since the existing backend doesn't, we will fetch individual details when viewed, and for the list we just show the driver.
  // Wait, let's just fetch all drivers.
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('All');

  // Modals state
  const [isViewOpen, setIsViewOpen] = useState(false);
  const [isAssignOpen, setIsAssignOpen] = useState(false);
  
  const [currentDriver, setCurrentDriver] = useState<Driver | null>(null);
  const [currentAssignment, setCurrentAssignment] = useState<Assignment | null>(null);
  const [currentAssignedBus, setCurrentAssignedBus] = useState<Bus | null>(null);
  const [assignmentHistory, setAssignmentHistory] = useState<Assignment[]>([]);
  
  const [selectedBusId, setSelectedBusId] = useState<number | ''>('');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchDrivers = async () => {
    try {
      setLoading(true);
      const res = await driverService.getAll();
      setDrivers(res.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail?.message || 'Failed to fetch drivers. Check permissions.');
    } finally {
      setLoading(false);
    }
  };

  const fetchBuses = async () => {
    try {
      const res = await busService.getAll();
      setBuses(res.data);
    } catch (err) {
      console.error("Failed to fetch buses");
    }
  };

  useEffect(() => {
    fetchDrivers();
    fetchBuses();
  }, []);

  const handleView = async (driver: Driver) => {
    setCurrentDriver(driver);
    setCurrentAssignment(null);
    setCurrentAssignedBus(null);
    setAssignmentHistory([]);
    setIsViewOpen(true);
    setActionError(null);

    try {
      // 1. Get driver detail which includes current_assignment
      const detailRes = await driverService.getById(driver.id);
      if (detailRes.data.current_assignment) {
        setCurrentAssignment(detailRes.data.current_assignment);
        // Fetch the specific bus details for display
        const busRes = await busService.getById(detailRes.data.current_assignment.bus_id);
        if (busRes.success) {
          setCurrentAssignedBus(busRes.data);
        }
      }

      // 2. Get history
      const historyRes = await driverService.getAssignments(driver.id);
      if (historyRes.success) {
        setAssignmentHistory(historyRes.data);
      }
    } catch (e) {
      console.error("Failed to load full driver details", e);
    }
  };

  const handleOpenAssign = () => {
    setSelectedBusId(currentAssignment ? currentAssignment.bus_id : '');
    setActionError(null);
    setIsAssignOpen(true);
  };

  const handleAssignBus = async () => {
    if (!currentDriver || !selectedBusId) return;
    
    setActionLoading(true);
    setActionError(null);
    try {
      await driverService.assignBus(currentDriver.id, Number(selectedBusId));
      setIsAssignOpen(false);
      // Refresh driver details
      handleView(currentDriver);
    } catch (err: any) {
      let errorMsg = 'Failed to assign bus.';
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          errorMsg = err.response.data.detail.map((d: any) => `${d.loc.join('.')} ${d.msg}`).join(', ');
        } else {
          errorMsg = err.response.data.detail.message || err.response.data.detail;
        }
      }
      setActionError(errorMsg);
    } finally {
      setActionLoading(false);
    }
  };

  const handleUnassignBus = async () => {
    if (!currentDriver || !currentAssignment) return;
    
    if (window.confirm('Are you sure you want to remove this driver\'s bus assignment?')) {
      setActionLoading(true);
      setActionError(null);
      try {
        await driverService.unassignBus(currentDriver.id);
        // Refresh driver details
        handleView(currentDriver);
      } catch (err: any) {
        setActionError(err.response?.data?.detail?.message || 'Failed to unassign bus.');
      } finally {
        setActionLoading(false);
      }
    }
  };

  // Filtering
  const filteredDrivers = drivers.filter(d => {
    const matchesSearch = d.full_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          d.email.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filterStatus === 'All' ? true : d.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Drivers</h1>
          <p className="text-sm text-slate-500">Manage drivers and their current bus assignments.</p>
        </div>
        <button 
          onClick={() => alert("Backend requires a secure driver-creation endpoint (via Firebase Admin SDK) which is not yet implemented. Please manage Firebase users directly for now.")}
          className="bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 rounded-lg flex items-center font-medium transition-colors"
        >
          <Plus className="w-5 h-5 mr-2" />
          Add Driver
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 p-4 rounded-lg flex items-start border border-red-200">
          <AlertTriangle className="w-5 h-5 mr-3 flex-shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="w-5 h-5 absolute left-3 top-2.5 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search drivers..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 outline-none"
          />
        </div>
        <div className="relative w-full sm:w-48">
          <Filter className="w-5 h-5 absolute left-3 top-2.5 text-slate-400" />
          <select 
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 outline-none appearance-none"
          >
            <option value="All">All Statuses</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="INACTIVE">INACTIVE</option>
            <option value="SUSPENDED">SUSPENDED</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600">
            <thead className="bg-slate-50 text-slate-500 border-b border-slate-200 uppercase text-xs font-semibold">
              <tr>
                <th className="px-6 py-4">Driver</th>
                <th className="px-6 py-4">Email</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {loading ? (
                <tr><td colSpan={4} className="px-6 py-8 text-center text-slate-400">Loading drivers...</td></tr>
              ) : filteredDrivers.length === 0 ? (
                <tr><td colSpan={4} className="px-6 py-8 text-center text-slate-400">No drivers found.</td></tr>
              ) : (
                filteredDrivers.map((driver) => (
                  <tr key={driver.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div className="w-8 h-8 rounded bg-emerald-50 text-emerald-600 flex items-center justify-center mr-3 font-bold">
                          {driver.full_name.charAt(0).toUpperCase()}
                        </div>
                        <span className="font-semibold text-slate-800">{driver.full_name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">{driver.email}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                        driver.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-700' :
                        'bg-slate-100 text-slate-700'
                      }`}>
                        {driver.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button onClick={() => handleView(driver)} className="text-brand-600 font-medium hover:underline text-sm px-3 py-1 rounded hover:bg-brand-50">
                        View
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Driver Details Modal */}
      {isViewOpen && currentDriver && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl flex flex-col max-h-[90vh]">
            <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-900 text-white rounded-t-2xl">
              <h2 className="text-lg font-bold flex items-center"><Users className="w-5 h-5 mr-2 text-brand-500"/> Driver Details</h2>
              <button onClick={() => setIsViewOpen(false)} className="text-slate-400 hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto space-y-6 flex-1">
              
              {actionError && (
                <div className="bg-red-50 text-red-600 p-4 rounded-lg flex items-start border border-red-200 mb-4">
                  <ShieldAlert className="w-5 h-5 mr-3 flex-shrink-0" />
                  <p className="text-sm">{actionError}</p>
                </div>
              )}

              {/* Profile Section */}
              <div className="flex flex-col md:flex-row gap-6">
                <div className="flex-1 bg-slate-50 p-5 rounded-xl border border-slate-200">
                  <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center">
                     Profile
                  </h3>
                  <p className="text-xl font-bold text-slate-800">{currentDriver.full_name}</p>
                  <p className="text-sm text-slate-500 mb-4">{currentDriver.email}</p>
                  
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-slate-500 font-semibold uppercase">Status:</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          currentDriver.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-700'
                        }`}>
                          {currentDriver.status}
                    </span>
                  </div>
                </div>

                {/* Current Assignment Section */}
                <div className="flex-1 bg-brand-50 p-5 rounded-xl border border-brand-200">
                  <div className="flex justify-between items-start mb-4">
                    <h3 className="text-sm font-bold text-brand-600 uppercase tracking-wider flex items-center">
                      Current Assignment
                    </h3>
                    <div className="space-x-2">
                      {currentAssignment && (
                        <button 
                          onClick={handleUnassignBus} 
                          disabled={actionLoading}
                          className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded font-medium hover:bg-red-200 disabled:opacity-50"
                        >
                          Unassign
                        </button>
                      )}
                      <button 
                        onClick={handleOpenAssign}
                        className="text-xs bg-brand-600 text-white px-3 py-1 rounded font-medium hover:bg-brand-700 shadow-sm"
                      >
                        {currentAssignment ? 'Change Bus' : 'Assign Bus'}
                      </button>
                    </div>
                  </div>

                  {currentAssignment && currentAssignedBus ? (
                    <div>
                      <div className="flex items-center mb-2">
                        <BusIcon className="w-5 h-5 text-brand-600 mr-2" />
                        <span className="text-xl font-bold text-slate-800">{currentAssignedBus.bus_number}</span>
                      </div>
                      <p className="text-sm text-slate-600">Reg: {currentAssignedBus.registration_number} • Cap: {currentAssignedBus.capacity}</p>
                      
                      <div className="mt-4 pt-4 border-t border-brand-200/50 flex justify-between text-xs text-slate-500">
                        <span>Assigned: {new Date(currentAssignment.assigned_from).toLocaleDateString()}</span>
                        <span className="font-semibold text-brand-700">{currentAssignment.status}</span>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-4 text-slate-500">
                      <BusIcon className="w-10 h-10 text-slate-300 mb-2" />
                      <p className="font-medium text-slate-600">No Bus Assigned</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Assignment History */}
              <div>
                <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4 flex items-center">
                  <History className="w-4 h-4 mr-2 text-slate-500" /> Assignment History
                </h3>
                
                {assignmentHistory.length === 0 ? (
                  <p className="text-sm text-slate-500 italic bg-slate-50 p-4 rounded-lg border border-slate-200">No assignment history found for this driver.</p>
                ) : (
                  <div className="border border-slate-200 rounded-lg overflow-hidden">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
                        <tr>
                          <th className="px-4 py-3 font-medium">Bus ID</th>
                          <th className="px-4 py-3 font-medium">From</th>
                          <th className="px-4 py-3 font-medium">Until</th>
                          <th className="px-4 py-3 font-medium">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {assignmentHistory.map(hist => (
                          <tr key={hist.id}>
                            <td className="px-4 py-3 font-medium text-slate-700">Bus #{hist.bus_id}</td>
                            <td className="px-4 py-3 text-slate-500">{new Date(hist.assigned_from).toLocaleDateString()}</td>
                            <td className="px-4 py-3 text-slate-500">{hist.assigned_until ? new Date(hist.assigned_until).toLocaleDateString() : '—'}</td>
                            <td className="px-4 py-3">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                hist.status === 'ACTIVE' ? 'bg-brand-100 text-brand-700' : 'bg-slate-100 text-slate-500'
                              }`}>
                                {hist.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

            </div>
          </div>
        </div>
      )}

      {/* Assign Bus Modal */}
      {isAssignOpen && currentDriver && (
        <div className="fixed inset-0 bg-slate-900/60 flex items-center justify-center z-[60] p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center">
              <h3 className="font-bold text-slate-800">Assign Bus to {currentDriver.full_name.split(' ')[0]}</h3>
              <button onClick={() => setIsAssignOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>
            
            <div className="p-6">
              {actionError && (
                <div className="mb-4 text-xs text-red-600 bg-red-50 p-2 rounded border border-red-200">
                  {actionError}
                </div>
              )}
              
              <label className="block text-sm font-medium text-slate-700 mb-2">Select Bus from Database</label>
              <select 
                value={selectedBusId} 
                onChange={(e) => setSelectedBusId(e.target.value ? Number(e.target.value) : '')}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 outline-none"
              >
                <option value="">-- Choose a Bus --</option>
                {buses.map(b => (
                  <option key={b.id} value={b.id}>{b.bus_number} ({b.registration_number})</option>
                ))}
              </select>
              <p className="mt-2 text-xs text-slate-500">
                This will automatically close any previous active assignment for this driver and bus.
              </p>
            </div>
            
            <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end space-x-3">
              <button onClick={() => setIsAssignOpen(false)} className="px-4 py-2 text-slate-600 text-sm font-medium hover:bg-slate-200 rounded-lg transition-colors">
                Cancel
              </button>
              <button 
                onClick={handleAssignBus} 
                disabled={!selectedBusId || actionLoading}
                className="px-4 py-2 bg-brand-500 text-white text-sm font-medium hover:bg-brand-600 rounded-lg transition-colors disabled:opacity-50"
              >
                {actionLoading ? 'Saving...' : 'Confirm Assignment'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default Drivers;
