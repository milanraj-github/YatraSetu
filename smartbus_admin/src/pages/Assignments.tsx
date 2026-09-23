import React, { useState, useEffect } from 'react';
import { driverService, busService } from '../services/api';
import { AlertCircle, Plus, Search, X } from 'lucide-react';


interface Driver {
  id: number;
  full_name: string;
  email: string;
  status: string;
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
  driver: Driver;
  bus: Bus;
}

export default function Assignments() {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [buses, setBuses] = useState<Bus[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState('');
  
  // Assign Modal
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const [selectedDriverId, setSelectedDriverId] = useState<number | ''>('');
  const [selectedBusId, setSelectedBusId] = useState<number | ''>('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [assignRes, driversRes, busesRes] = await Promise.all([
        driverService.getAllAssignments(),
        driverService.getAll(),
        busService.getAll()
      ]);
      setAssignments(assignRes.data || []);
      setDrivers(driversRes.data || []);
      setBuses(busesRes.data || []);
      setError(null);
    } catch (err: any) {
      setError('Failed to load assignments.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDriverId || !selectedBusId) return;
    try {
      await driverService.assignBus(Number(selectedDriverId), Number(selectedBusId));
      setIsAssignModalOpen(false);
      setSelectedDriverId('');
      setSelectedBusId('');
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail?.message || 'Failed to assign bus');
    }
  };

  const handleUnassign = async (driverId: number) => {
    if (!window.confirm('Are you sure you want to unassign this driver from their current bus?')) return;
    try {
      await driverService.unassignBus(driverId);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail?.message || 'Failed to unassign bus');
    }
  };

  // Find if a driver already has an assignment
  const getDriverAssignmentStatus = (driverId: number) => {
    return assignments.find(a => a.driver_id === driverId);
  };

  // Find if a bus already has an assignment
  const getBusAssignmentStatus = (busId: number) => {
    return assignments.find(a => a.bus_id === busId);
  };

  const filteredAssignments = assignments.filter(a => 
    (a.driver?.full_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (a.bus?.bus_number || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Assignments</h1>
          <p className="text-sm text-gray-500">Manage which driver operates which bus.</p>
        </div>
        <button
          onClick={() => setIsAssignModalOpen(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition flex items-center"
        >
          <Plus className="w-5 h-5 mr-1" />
          New Assignment
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg flex items-center">
          <AlertCircle className="w-5 h-5 mr-2" />
          {error}
        </div>
      )}

      {/* Search */}
      <div className="bg-white p-4 rounded-xl border border-gray-200">
        <div className="relative">
          <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search by driver name or bus number..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          />
        </div>
      </div>

      {/* Assignments Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Loading assignments...</div>
        ) : filteredAssignments.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-500 mb-4">No active assignments found.</p>
            <button
              onClick={() => setIsAssignModalOpen(true)}
              className="text-blue-600 font-medium hover:underline"
            >
              + Create your first assignment
            </button>
          </div>
        ) : (
          <table className="w-full text-left text-sm text-gray-600">
            <thead className="bg-gray-50 border-b border-gray-200 text-gray-700">
              <tr>
                <th className="px-6 py-4 font-medium">Driver</th>
                <th className="px-6 py-4 font-medium">Bus</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium">Assigned From</th>
                <th className="px-6 py-4 font-medium">Assigned Until</th>
                <th className="px-6 py-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredAssignments.map((a) => (
                <tr key={a.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="font-medium text-gray-900">{a.driver.full_name}</div>
                    <div className="text-xs text-gray-500">{a.driver.email}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="font-medium text-gray-900">{a.bus.bus_number}</div>
                    <div className="text-xs text-gray-500">{a.bus.registration_number}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${a.status === 'ACTIVE' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                      {a.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {new Date(a.assigned_from).toLocaleString(undefined, {dateStyle: 'medium', timeStyle: 'short'})}
                  </td>
                  <td className="px-6 py-4 text-gray-500">
                    {a.assigned_until ? new Date(a.assigned_until).toLocaleString(undefined, {dateStyle: 'medium', timeStyle: 'short'}) : 'Ongoing'}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => handleUnassign(a.driver_id)}
                      className="text-red-600 hover:text-red-800 font-medium"
                    >
                      Unassign
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Assign Modal */}
      {isAssignModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="flex justify-between items-center p-6 border-b border-gray-100">
              <h2 className="text-xl font-bold text-gray-900">Assign Driver to Bus</h2>
              <button onClick={() => setIsAssignModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleAssign} className="p-6 space-y-6">
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Select Driver</label>
                <select
                  required
                  value={selectedDriverId}
                  onChange={(e) => setSelectedDriverId(e.target.value ? Number(e.target.value) : '')}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                >
                  <option value="">Select a driver...</option>
                  {drivers.filter(d => d.status === 'ACTIVE').map(driver => {
                    const currentAssignment = getDriverAssignmentStatus(driver.id);
                    return (
                      <option key={driver.id} value={driver.id}>
                        {driver.full_name} {currentAssignment ? `(Currently on ${currentAssignment.bus.bus_number})` : ''}
                      </option>
                    );
                  })}
                </select>
                {selectedDriverId && getDriverAssignmentStatus(Number(selectedDriverId)) && (
                  <p className="text-xs text-orange-600 mt-2 flex items-center">
                    <AlertCircle className="w-3 h-3 mr-1" />
                    This driver is currently assigned. Saving will end their current assignment.
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Select Bus</label>
                <select
                  required
                  value={selectedBusId}
                  onChange={(e) => setSelectedBusId(e.target.value ? Number(e.target.value) : '')}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                >
                  <option value="">Select a bus...</option>
                  {buses.filter(b => b.status !== 'INACTIVE').map(bus => {
                    const currentAssignment = getBusAssignmentStatus(bus.id);
                    return (
                      <option key={bus.id} value={bus.id}>
                        {bus.bus_number} - {bus.registration_number} {currentAssignment ? `(Currently assigned to ${currentAssignment.driver.full_name})` : ''}
                      </option>
                    );
                  })}
                </select>
                {selectedBusId && getBusAssignmentStatus(Number(selectedBusId)) && (
                  <p className="text-xs text-orange-600 mt-2 flex items-center">
                    <AlertCircle className="w-3 h-3 mr-1" />
                    This bus is currently assigned. Saving will reassign it and end the previous driver's assignment.
                  </p>
                )}
              </div>

              <div className="mt-8 flex gap-3">
                <button
                  type="button"
                  onClick={() => setIsAssignModalOpen(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700"
                >
                  Confirm Assignment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
