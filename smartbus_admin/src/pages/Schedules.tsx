import React, { useState, useEffect } from 'react';
import { scheduleService, busService, routeService, driverService } from '../services/api';
import { AlertCircle, Calendar, Clock, Map, Navigation, Plus, Search, Truck, X } from 'lucide-react';

// Type definitions based on what we've seen
interface Schedule {
  id: number;
  bus_id: number;
  route_id: number;
  start_time: string;
  end_time: string;
  direction: string;
  days_of_week: string;
  active: boolean;
}

interface Bus {
  id: number;
  bus_number: string;
  registration_number: string;
  status: string;
}

interface RouteStop {
  id: number;
  boarding_point_id: number;
  sequence_order: number;
  direction: string;
  boarding_point: { name: string };
}

interface Route {
  id: number;
  name: string;
  code: string;
  stops: RouteStop[];
}

interface Assignment {
  id: number;
  bus_id: number;
  driver_id: number;
  driver: { full_name: string; email: string };
}

export default function Schedules() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [buses, setBuses] = useState<Bus[]>([]);
  const [routes, setRoutes] = useState<Route[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search & Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [filterDirection, setFilterDirection] = useState('ALL');
  const [filterStatus, setFilterStatus] = useState('ALL');

  // Modals
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<Schedule | null>(null);

  // Form State
  const [busId, setBusId] = useState<number | ''>('');
  const [routeId, setRouteId] = useState<number | ''>('');
  const [direction, setDirection] = useState('MORNING');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [days, setDays] = useState<string[]>([]);
  const [isActive, setIsActive] = useState(true);

  const ALL_DAYS = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY'];

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [schedRes, busRes, routeRes, assignRes] = await Promise.all([
        scheduleService.getAll(),
        busService.getAll(),
        routeService.getAll(),
        driverService.getAllAssignments()
      ]);
      setSchedules(schedRes.data || []);
      setBuses(busRes.data || []);
      setRoutes(routeRes.data || []);
      setAssignments(assignRes.data || []);
      setError(null);
    } catch (err: any) {
      setError('Unable to load schedules.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const openAddModal = () => {
    setEditingSchedule(null);
    setBusId('');
    setRouteId('');
    setDirection('MORNING');
    setStartTime('');
    setEndTime('');
    setDays(['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY']);
    setIsActive(true);
    setIsModalOpen(true);
  };

  const openEditModal = (sched: Schedule) => {
    setEditingSchedule(sched);
    setBusId(sched.bus_id);
    setRouteId(sched.route_id);
    setDirection(sched.direction);
    setStartTime(sched.start_time.substring(0, 5)); // e.g. "07:35:00" -> "07:35"
    setEndTime(sched.end_time.substring(0, 5));
    setDays(sched.days_of_week.split(',').map(d => d.trim()).filter(Boolean));
    setIsActive(sched.active);
    setIsModalOpen(true);
  };

  const openViewModal = (sched: Schedule) => {
    setEditingSchedule(sched);
    setIsViewModalOpen(true);
  };

  const toggleDay = (day: string) => {
    setDays(prev => 
      prev.includes(day) ? prev.filter(d => d !== day) : [...prev, day]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!busId || !routeId || !startTime || !endTime) return;
    if (days.length === 0) {
      alert("At least one operating day is required.");
      return;
    }

    const payload = {
      bus_id: Number(busId),
      route_id: Number(routeId),
      direction,
      start_time: startTime.length === 5 ? `${startTime}:00` : startTime,
      end_time: endTime.length === 5 ? `${endTime}:00` : endTime,
      days_of_week: days.join(','),
      active: isActive
    };

    try {
      if (editingSchedule) {
        await scheduleService.update(editingSchedule.id, payload);
      } else {
        await scheduleService.create(payload);
      }
      setIsModalOpen(false);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail?.message || 'Failed to save schedule');
    }
  };

  const handleDeactivate = async (id: number) => {
    if (!window.confirm('Are you sure you want to deactivate this schedule? It will not be permanently deleted, preserving trip history.')) return;
    try {
      await scheduleService.update(id, { active: false });
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail?.message || 'Failed to deactivate schedule');
    }
  };

  // Helper mappings
  const augmentedSchedules = schedules.map(s => {
    const bus = buses.find(b => b.id === s.bus_id);
    const route = routes.find(r => r.id === s.route_id);
    const assignment = assignments.find(a => a.bus_id === s.bus_id);
    return { ...s, bus, route, assignment };
  });

  const filteredSchedules = augmentedSchedules.filter(s => {
    // Search match
    const searchLower = searchTerm.toLowerCase();
    const matchesSearch = 
      `SCH-${s.id}`.toLowerCase().includes(searchLower) ||
      (s.bus?.bus_number || '').toLowerCase().includes(searchLower) ||
      (s.route?.name || '').toLowerCase().includes(searchLower) ||
      (s.assignment?.driver?.full_name || '').toLowerCase().includes(searchLower) ||
      (s.assignment?.driver?.email || '').toLowerCase().includes(searchLower);

    // Filter match
    const matchesDirection = filterDirection === 'ALL' || s.direction === filterDirection;
    const matchesStatus = filterStatus === 'ALL' || (filterStatus === 'ACTIVE' ? s.active : !s.active);

    return matchesSearch && matchesDirection && matchesStatus;
  });

  // Calculate Today's Schedules for the UI
  // Note: For simplicity in timezone mapping (Asia/Kolkata), we'll assume the browser
  // date maps closely enough for a high-level UI summary snippet, picking "today's name"
  const todayName = new Date().toLocaleDateString('en-US', { weekday: 'long', timeZone: 'Asia/Kolkata' }).toUpperCase();
  const todaysSchedules = augmentedSchedules
    .filter(s => s.active && s.days_of_week.includes(todayName))
    .sort((a, b) => a.start_time.localeCompare(b.start_time));

  // Summary Stats
  const totalCount = schedules.length;
  const activeCount = schedules.filter(s => s.active).length;
  const morningCount = schedules.filter(s => s.direction === 'MORNING').length;
  const eveningCount = schedules.filter(s => s.direction === 'EVENING').length;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Schedules</h1>
          <p className="text-sm text-gray-500">Manage bus operating schedules and daily services.</p>
        </div>
        <button
          onClick={openAddModal}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition flex items-center"
        >
          <Plus className="w-5 h-5 mr-1" />
          Add Schedule
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg flex items-center">
          <AlertCircle className="w-5 h-5 mr-2" />
          {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center">
          <div className="bg-blue-100 p-3 rounded-lg mr-4 text-blue-600">
            <Calendar className="w-6 h-6" />
          </div>
          <div>
            <div className="text-sm text-gray-500 font-medium">Total Schedules</div>
            <div className="text-2xl font-bold text-gray-900">{totalCount}</div>
          </div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center">
          <div className="bg-green-100 p-3 rounded-lg mr-4 text-green-600">
            <AlertCircle className="w-6 h-6" />
          </div>
          <div>
            <div className="text-sm text-gray-500 font-medium">Active Services</div>
            <div className="text-2xl font-bold text-gray-900">{activeCount}</div>
          </div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center">
          <div className="bg-orange-100 p-3 rounded-lg mr-4 text-orange-600">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <div className="text-sm text-gray-500 font-medium">Morning</div>
            <div className="text-2xl font-bold text-gray-900">{morningCount}</div>
          </div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center">
          <div className="bg-purple-100 p-3 rounded-lg mr-4 text-purple-600">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <div className="text-sm text-gray-500 font-medium">Evening</div>
            <div className="text-2xl font-bold text-gray-900">{eveningCount}</div>
          </div>
        </div>
      </div>

      <div className="flex flex-col xl:flex-row gap-6">
        <div className="xl:w-3/4 space-y-6">
          {/* Search & Filters */}
          <div className="bg-white p-4 rounded-xl border border-gray-200 flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search schedules, buses, routes, drivers..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>
            <div className="w-full md:w-40">
              <select
                value={filterDirection}
                onChange={(e) => setFilterDirection(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              >
                <option value="ALL">All Directions</option>
                <option value="MORNING">Morning</option>
                <option value="EVENING">Evening</option>
              </select>
            </div>
            <div className="w-full md:w-36">
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              >
                <option value="ALL">All Status</option>
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Inactive</option>
              </select>
            </div>
          </div>

          {/* Schedules Table */}
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
            {loading ? (
              <div className="p-8 text-center text-gray-500">Loading schedules...</div>
            ) : filteredSchedules.length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-gray-500 mb-4">No schedules found.</p>
                <button onClick={openAddModal} className="text-blue-600 font-medium hover:underline">
                  + Create your first schedule to start planning bus services.
                </button>
              </div>
            ) : (
              <table className="w-full text-left text-sm text-gray-600">
                <thead className="bg-gray-50 border-b border-gray-200 text-gray-700">
                  <tr>
                    <th className="px-6 py-4 font-medium">Schedule</th>
                    <th className="px-6 py-4 font-medium">Bus</th>
                    <th className="px-6 py-4 font-medium">Route</th>
                    <th className="px-6 py-4 font-medium">Departure</th>
                    <th className="px-6 py-4 font-medium">Driver</th>
                    <th className="px-6 py-4 font-medium">Status</th>
                    <th className="px-6 py-4 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredSchedules.map((sched) => (
                    <tr key={sched.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 font-medium text-gray-900">
                        SCH-{sched.id.toString().padStart(3, '0')}
                      </td>
                      <td className="px-6 py-4">
                        <div className="font-medium text-gray-900">{sched.bus?.bus_number || 'Unknown'}</div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="font-medium text-gray-900 truncate max-w-[150px]" title={sched.route?.name}>
                          {sched.route?.name || 'Unknown'}
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5">{sched.direction}</div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center">
                          <Clock className="w-3.5 h-3.5 mr-1 text-gray-400" />
                          <span className="font-medium text-gray-900">{sched.start_time.substring(0, 5)}</span>
                        </div>
                        <div className="text-[10px] text-gray-500 uppercase tracking-wider mt-1" title={sched.days_of_week}>
                          {sched.days_of_week.split(',').map(d => d.substring(0, 3)).join(', ')}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        {sched.assignment ? (
                          <div>
                            <div className="font-medium text-gray-900 truncate max-w-[120px]" title={sched.assignment.driver.full_name}>
                              {sched.assignment.driver.full_name}
                            </div>
                            <div className="text-xs text-gray-500 truncate max-w-[120px]" title={sched.assignment.driver.email}>
                              {sched.assignment.driver.email}
                            </div>
                          </div>
                        ) : (
                          <span className="text-orange-500 text-xs bg-orange-50 px-2 py-1 rounded">Unassigned</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${sched.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                          {sched.active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right whitespace-nowrap">
                        <button onClick={() => openViewModal(sched)} className="text-gray-500 hover:text-blue-600 font-medium mr-4">View</button>
                        <button onClick={() => openEditModal(sched)} className="text-gray-500 hover:text-blue-600 font-medium mr-4">Edit</button>
                        {sched.active && (
                          <button onClick={() => handleDeactivate(sched.id)} className="text-red-500 hover:text-red-700 font-medium">
                            Deactivate
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="xl:w-1/4">
          {/* Today's Schedules Widget */}
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm sticky top-6">
            <div className="bg-blue-600 p-4 text-white">
              <h3 className="font-bold flex items-center">
                <Calendar className="w-5 h-5 mr-2 opacity-80" />
                TODAY'S SCHEDULES
              </h3>
              <p className="text-blue-100 text-xs mt-1">Asia/Kolkata timezone</p>
            </div>
            <div className="p-4 flex flex-col gap-3">
              {todaysSchedules.length === 0 ? (
                <div className="text-sm text-gray-500 text-center py-4">No active schedules running today.</div>
              ) : (
                todaysSchedules.map(sched => (
                  <div key={sched.id} className="border border-gray-100 rounded-lg p-3 hover:border-blue-200 transition-colors">
                    <div className="flex justify-between items-start mb-2">
                      <div className="font-bold text-gray-900 flex items-center">
                        <Clock className="w-4 h-4 mr-1 text-blue-600" />
                        {sched.start_time.substring(0, 5)}
                      </div>
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${sched.direction === 'MORNING' ? 'bg-orange-100 text-orange-700' : 'bg-purple-100 text-purple-700'}`}>
                        {sched.direction}
                      </span>
                    </div>
                    <div className="text-sm font-medium text-gray-800 mb-1">{sched.bus?.bus_number || 'Unknown Bus'}</div>
                    <div className="text-xs text-gray-500 truncate" title={sched.route?.name}>{sched.route?.name || 'Unknown Route'}</div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Add / Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl overflow-hidden my-8">
            <div className="flex justify-between items-center p-6 border-b border-gray-100">
              <h2 className="text-xl font-bold text-gray-900">{editingSchedule ? 'Edit Schedule' : 'Add Schedule'}</h2>
              <button onClick={() => setIsModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Bus</label>
                  <select
                    required
                    value={busId}
                    onChange={(e) => setBusId(Number(e.target.value))}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    <option value="">Select Bus...</option>
                    {buses.map(b => (
                      <option key={b.id} value={b.id}>{b.bus_number} - {b.registration_number}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Route</label>
                  <select
                    required
                    value={routeId}
                    onChange={(e) => setRouteId(Number(e.target.value))}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    <option value="">Select Route...</option>
                    {routes.map(r => (
                      <option key={r.id} value={r.id}>{r.name} ({r.code})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Direction</label>
                  <select
                    required
                    value={direction}
                    onChange={(e) => setDirection(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    <option value="MORNING">Morning</option>
                    <option value="EVENING">Evening</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                  <select
                    required
                    value={isActive ? 'ACTIVE' : 'INACTIVE'}
                    onChange={(e) => setIsActive(e.target.value === 'ACTIVE')}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    <option value="ACTIVE">Active</option>
                    <option value="INACTIVE">Inactive</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Departure Time (HH:MM)</label>
                  <input
                    type="time"
                    required
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Estimated Arrival (HH:MM)</label>
                  <input
                    type="time"
                    required
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Operating Days</label>
                  <div className="flex flex-wrap gap-2">
                    {ALL_DAYS.map(day => (
                      <label key={day} className={`px-3 py-2 border rounded-lg cursor-pointer text-sm font-medium select-none transition-colors ${days.includes(day) ? 'bg-blue-50 border-blue-500 text-blue-700' : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'}`}>
                        <input
                          type="checkbox"
                          className="hidden"
                          checked={days.includes(day)}
                          onChange={() => toggleDay(day)}
                        />
                        {day.substring(0, 3)}
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-8 pt-6 border-t border-gray-100 bg-gray-50 -mx-6 -mb-6 px-6 py-4 rounded-b-xl flex gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 bg-white text-gray-700 rounded-lg font-medium hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 shadow-sm"
                >
                  {editingSchedule ? 'Save Changes' : 'Create Schedule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View Modal */}
      {isViewModalOpen && editingSchedule && (() => {
        const sched = augmentedSchedules.find(s => s.id === editingSchedule.id) || editingSchedule as any;
        const routeStops = sched.route?.stops?.filter((s: RouteStop) => s.direction === sched.direction).sort((a: RouteStop, b: RouteStop) => a.sequence_order - b.sequence_order) || [];

        return (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 overflow-y-auto">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl overflow-hidden my-8">
              <div className="flex justify-between items-center p-6 border-b border-gray-100">
                <h2 className="text-xl font-bold text-gray-900">Schedule Details (SCH-{sched.id.toString().padStart(3, '0')})</h2>
                <button onClick={() => setIsViewModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-6">
                  <div>
                    <div className="text-xs text-gray-500 font-bold uppercase tracking-wider mb-1">Assigned Driver</div>
                    <div className="flex items-center">
                      <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center mr-3 font-bold text-lg">
                        {sched.assignment?.driver?.full_name?.charAt(0) || '?'}
                      </div>
                      <div>
                        <div className="font-bold text-gray-900">{sched.assignment?.driver?.full_name || 'No Active Assignment'}</div>
                        {sched.assignment && <div className="text-sm text-gray-500">{sched.assignment.driver.email}</div>}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
                      <div className="text-xs text-gray-500 mb-1 flex items-center"><Truck className="w-3 h-3 mr-1"/> Bus</div>
                      <div className="font-bold text-gray-900">{sched.bus?.bus_number || 'Unknown'}</div>
                    </div>
                    <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
                      <div className="text-xs text-gray-500 mb-1 flex items-center"><Navigation className="w-3 h-3 mr-1"/> Direction</div>
                      <div className="font-bold text-gray-900">{sched.direction}</div>
                    </div>
                    <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
                      <div className="text-xs text-gray-500 mb-1 flex items-center"><Clock className="w-3 h-3 mr-1"/> Departure</div>
                      <div className="font-bold text-gray-900">{sched.start_time.substring(0, 5)}</div>
                    </div>
                    <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
                      <div className="text-xs text-gray-500 mb-1 flex items-center"><AlertCircle className="w-3 h-3 mr-1"/> Status</div>
                      <div className="font-bold text-gray-900">
                        <span className={`px-2 py-0.5 rounded text-xs ${sched.active ? 'bg-green-100 text-green-800' : 'bg-gray-200 text-gray-800'}`}>
                          {sched.active ? 'ACTIVE' : 'INACTIVE'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <div className="text-xs text-gray-500 font-bold uppercase tracking-wider mb-2">Operating Days</div>
                    <div className="flex flex-wrap gap-1">
                      {sched.days_of_week.split(',').map((d: string) => (
                        <span key={d} className="px-2 py-1 bg-blue-50 text-blue-700 text-xs font-medium rounded border border-blue-100">
                          {d.trim()}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="border-l border-gray-100 pl-8">
                  <div className="text-xs text-gray-500 font-bold uppercase tracking-wider mb-4 flex items-center">
                    <Map className="w-4 h-4 mr-2" />
                    Route Path: {sched.route?.name || 'Unknown'}
                  </div>
                  
                  {routeStops.length === 0 ? (
                    <div className="text-sm text-gray-500 italic bg-gray-50 p-4 rounded text-center">No stops found for this direction.</div>
                  ) : (
                    <div className="relative border-l-2 border-blue-200 ml-3 space-y-4 pb-4">
                      {routeStops.map((stop: RouteStop, idx: number) => (
                        <div key={stop.id} className="relative pl-6">
                          <div className={`absolute -left-[9px] top-1 w-4 h-4 rounded-full border-2 border-white shadow-sm ${idx === 0 || idx === routeStops.length - 1 ? 'bg-blue-600' : 'bg-gray-300'}`} />
                          <div className="font-medium text-sm text-gray-900 leading-none pt-1">
                            {idx + 1}. {stop.boarding_point.name}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        );
      })()}

    </div>
  );
}
