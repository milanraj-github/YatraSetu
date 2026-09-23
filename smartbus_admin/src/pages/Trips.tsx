import { useState, useEffect } from 'react';
import { tripService, busService, driverService, routeService, scheduleService } from '../services/api';
import { AlertCircle, Calendar, Clock, Map, Search, Truck, User, X, RefreshCw } from 'lucide-react';

interface Trip {
  id: number;
  bus_id: number;
  route_id: number;
  schedule_id: number;
  driver_id: number;
  session_date: string;
  direction: string;
  status: string;
  started_at: string | null;
  ended_at: string | null;
  bus?: Bus;
  driver?: Driver;
  route?: Route;
  schedule?: Schedule;
}

// Minimal interfaces for joined data
interface Bus { id: number; bus_number: string; registration_number: string; }
interface Driver { id: number; full_name: string; email: string; }
interface RouteStop { boarding_point_id: number; sequence_order: number; direction: string; boarding_point: { name: string; }; }
interface Route { id: number; name: string; stops: RouteStop[]; }
interface Schedule { id: number; start_time: string; }

export default function Trips() {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [buses, setBuses] = useState<Bus[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [routes, setRoutes] = useState<Route[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Date Filter - default to today in YYYY-MM-DD for Asia/Kolkata
  const todayStr = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
  const [filterDate, setFilterDate] = useState<string>(todayStr);

  // Search & Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [filterBus, setFilterBus] = useState<string>('ALL');
  const [filterDriver, setFilterDriver] = useState<string>('ALL');
  const [filterRoute] = useState<string>('ALL');
  const [filterDirection, setFilterDirection] = useState('ALL');

  // Modals
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [selectedTrip, setSelectedTrip] = useState<Trip | null>(null);

  useEffect(() => {
    fetchData();
  }, [filterDate]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = filterDate ? { session_date: filterDate } : undefined;
      const [tripRes, busRes, driverRes, routeRes, schedRes] = await Promise.all([
        tripService.getAll(params),
        busService.getAll(),
        driverService.getAll(),
        routeService.getAll(),
        scheduleService.getAll()
      ]);
      setTrips(tripRes.data || []);
      setBuses(busRes.data || []);
      setDrivers(driverRes.data || []);
      setRoutes(routeRes.data || []);
      setSchedules(schedRes.data || []);
      setError(null);
    } catch (err: any) {
      setError('Unable to load trips. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Join data
  const augmentedTrips = trips.map(t => ({
    ...t,
    bus: buses.find(b => b.id === t.bus_id),
    driver: drivers.find(d => d.id === t.driver_id),
    route: routes.find(r => r.id === t.route_id),
    schedule: schedules.find(s => s.id === t.schedule_id)
  }));

  // Filtering
  const filteredTrips = augmentedTrips.filter(t => {
    // Search
    const searchLower = searchTerm.toLowerCase();
    const matchesSearch = 
      `TRIP-${t.id}`.toLowerCase().includes(searchLower) ||
      t.bus?.bus_number.toLowerCase().includes(searchLower) ||
      t.driver?.full_name.toLowerCase().includes(searchLower) ||
      t.route?.name.toLowerCase().includes(searchLower);

    const matchesStatus = filterStatus === 'ALL' || t.status === filterStatus;
    const matchesBus = filterBus === 'ALL' || t.bus_id.toString() === filterBus;
    const matchesDriver = filterDriver === 'ALL' || t.driver_id.toString() === filterDriver;
    const matchesRoute = filterRoute === 'ALL' || t.route_id.toString() === filterRoute;
    const matchesDirection = filterDirection === 'ALL' || t.direction === filterDirection;

    return matchesSearch && matchesStatus && matchesBus && matchesDriver && matchesRoute && matchesDirection;
  });

  // Formatting Time
  const formatTimeOnly = (isoString: string | null) => {
    if (!isoString) return '—';
    return new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata',
      hour: '2-digit', minute: '2-digit', hour12: false
    }).format(new Date(isoString));
  };

  // Status Badge Color Map
  const statusColors: Record<string, string> = {
    SCHEDULED: 'bg-blue-100 text-blue-800',
    ACTIVE: 'bg-green-100 text-green-800 border border-green-300',
    COMPLETED: 'bg-gray-200 text-gray-800',
    CANCELLED: 'bg-red-100 text-red-800',
  };

  // Statistics
  const stats = {
    total: filteredTrips.length,
    active: filteredTrips.filter(t => t.status === 'ACTIVE').length,
    scheduled: filteredTrips.filter(t => t.status === 'SCHEDULED').length,
    completed: filteredTrips.filter(t => t.status === 'COMPLETED').length,
    cancelled: filteredTrips.filter(t => t.status === 'CANCELLED').length,
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Trips</h1>
          <p className="text-sm text-gray-500">Monitor and manage actual bus journeys.</p>
        </div>
        <div className="flex items-center gap-3">
          <input 
            type="date" 
            value={filterDate}
            onChange={(e) => setFilterDate(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 outline-none"
            title="Date filter is applied automatically"
          />
          <button
            onClick={fetchData}
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg font-medium hover:bg-gray-50 transition flex items-center shadow-sm"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin text-blue-500' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg flex items-center shadow-sm border border-red-100">
          <AlertCircle className="w-5 h-5 mr-2" />
          {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white p-4 md:p-6 rounded-xl border border-gray-200 shadow-sm text-center md:text-left">
          <div className="text-sm text-gray-500 font-medium mb-1">Total Trips</div>
          <div className="text-2xl font-bold text-gray-900">{stats.total}</div>
        </div>
        <div className="bg-white p-4 md:p-6 rounded-xl border border-green-200 bg-green-50/30 shadow-sm text-center md:text-left">
          <div className="text-sm text-green-700 font-medium mb-1 flex items-center justify-center md:justify-start">
            <span className="w-2 h-2 rounded-full bg-green-500 mr-2 animate-pulse"></span>
            Active Now
          </div>
          <div className="text-2xl font-bold text-green-700">{stats.active}</div>
        </div>
        <div className="bg-white p-4 md:p-6 rounded-xl border border-gray-200 shadow-sm text-center md:text-left">
          <div className="text-sm text-blue-600 font-medium mb-1">Scheduled</div>
          <div className="text-2xl font-bold text-gray-900">{stats.scheduled}</div>
        </div>
        <div className="bg-white p-4 md:p-6 rounded-xl border border-gray-200 shadow-sm text-center md:text-left">
          <div className="text-sm text-gray-500 font-medium mb-1">Completed</div>
          <div className="text-2xl font-bold text-gray-900">{stats.completed}</div>
        </div>
        <div className="bg-white p-4 md:p-6 rounded-xl border border-gray-200 shadow-sm text-center md:text-left">
          <div className="text-sm text-red-500 font-medium mb-1">Cancelled</div>
          <div className="text-2xl font-bold text-gray-900">{stats.cancelled}</div>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-wrap gap-4">
        <div className="flex-1 min-w-[200px] relative">
          <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search trips..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          />
        </div>
        <div className="w-full md:w-36">
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm text-gray-700">
            <option value="ALL">All Status</option>
            <option value="SCHEDULED">Scheduled</option>
            <option value="ACTIVE">Active</option>
            <option value="COMPLETED">Completed</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </div>
        <div className="w-full md:w-36">
          <select value={filterBus} onChange={(e) => setFilterBus(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm text-gray-700">
            <option value="ALL">All Buses</option>
            {buses.map(b => <option key={b.id} value={b.id}>{b.bus_number}</option>)}
          </select>
        </div>
        <div className="w-full md:w-40">
          <select value={filterDriver} onChange={(e) => setFilterDriver(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm text-gray-700">
            <option value="ALL">All Drivers</option>
            {drivers.map(d => <option key={d.id} value={d.id}>{d.full_name}</option>)}
          </select>
        </div>
        <div className="w-full md:w-36">
          <select value={filterDirection} onChange={(e) => setFilterDirection(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm text-gray-700">
            <option value="ALL">All Directions</option>
            <option value="MORNING">Morning</option>
            <option value="EVENING">Evening</option>
          </select>
        </div>
      </div>

      {/* Trips Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm overflow-x-auto">
        {loading ? (
          <div className="p-12 text-center text-gray-500 flex flex-col items-center">
            <RefreshCw className="w-8 h-8 animate-spin text-blue-500 mb-4" />
            Loading trips...
          </div>
        ) : filteredTrips.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-gray-500 text-lg">No trips found for this date.</p>
            <p className="text-sm text-gray-400 mt-2">Adjust your filters or select a different date.</p>
          </div>
        ) : (
          <table className="w-full text-left text-sm text-gray-600 whitespace-nowrap min-w-[900px]">
            <thead className="bg-gray-50 border-b border-gray-200 text-gray-700">
              <tr>
                <th className="px-6 py-4 font-medium">Trip ID</th>
                <th className="px-6 py-4 font-medium">Bus</th>
                <th className="px-6 py-4 font-medium">Driver</th>
                <th className="px-6 py-4 font-medium">Route</th>
                <th className="px-6 py-4 font-medium">Sched / Actual</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredTrips.map((trip: any) => (
                <tr key={trip.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 font-medium text-gray-900">
                    TRIP-{trip.id.toString().padStart(3, '0')}
                  </td>
                  <td className="px-6 py-4 font-medium text-gray-900">
                    {trip.bus?.bus_number || 'Unknown'}
                  </td>
                  <td className="px-6 py-4">
                    <div className="truncate max-w-[150px] font-medium text-gray-900" title={trip.driver?.full_name}>
                      {trip.driver?.full_name || 'Unknown'}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="truncate max-w-[200px] font-medium text-gray-900" title={trip.route?.name}>
                      {trip.route?.name || 'Unknown'}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">{trip.direction}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center text-gray-900 mb-1" title="Scheduled Departure">
                      <Calendar className="w-3.5 h-3.5 mr-1.5 text-gray-400" />
                      {trip.schedule?.start_time?.substring(0, 5) || '—'}
                    </div>
                    <div className="flex items-center text-blue-700 font-medium" title="Actual Start Time">
                      <Clock className="w-3.5 h-3.5 mr-1.5 text-blue-400" />
                      {formatTimeOnly(trip.started_at)}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${statusColors[trip.status] || 'bg-gray-100 text-gray-800'}`}>
                      {trip.status === 'ACTIVE' && <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block mr-1.5 animate-pulse"></span>}
                      {trip.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button onClick={() => { setSelectedTrip(trip); setIsViewModalOpen(true); }} className="text-blue-600 hover:text-blue-800 font-medium bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded transition-colors">
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* View Details Modal */}
      {isViewModalOpen && selectedTrip && (() => {
        const routeStops = selectedTrip.route?.stops?.filter((s: RouteStop) => s.direction === selectedTrip.direction).sort((a: RouteStop, b: RouteStop) => a.sequence_order - b.sequence_order) || [];
        
        return (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 overflow-y-auto">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl my-8 overflow-hidden flex flex-col md:flex-row min-h-[60vh]">
              {/* Left Panel: Information */}
              <div className="w-full md:w-1/2 p-6 md:p-8 bg-white border-r border-gray-100 flex flex-col">
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900 mb-1">TRIP-{selectedTrip.id.toString().padStart(3, '0')}</h2>
                    <span className={`px-2.5 py-1 rounded text-xs font-bold inline-flex items-center ${statusColors[selectedTrip.status] || 'bg-gray-100 text-gray-800'}`}>
                      {selectedTrip.status === 'ACTIVE' && <span className="w-1.5 h-1.5 rounded-full bg-green-500 mr-1.5 animate-pulse"></span>}
                      {selectedTrip.status}
                    </span>
                  </div>
                  <button onClick={() => setIsViewModalOpen(false)} className="text-gray-400 hover:text-gray-600 md:hidden">
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div className="space-y-6 flex-1">
                  <div>
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Bus Details</h3>
                    <div className="flex items-center p-3 border border-gray-100 rounded-lg bg-gray-50">
                      <div className="w-10 h-10 bg-white shadow-sm rounded flex items-center justify-center mr-3 text-gray-600"><Truck className="w-5 h-5" /></div>
                      <div>
                        <div className="font-bold text-gray-900">{selectedTrip.bus?.bus_number || 'Unknown Bus'}</div>
                        <div className="text-xs text-gray-500">{selectedTrip.bus?.registration_number || 'No Reg'}</div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Driver Details</h3>
                    <div className="flex items-center p-3 border border-gray-100 rounded-lg bg-gray-50">
                      <div className="w-10 h-10 bg-white shadow-sm rounded-full flex items-center justify-center mr-3 text-blue-600 font-bold">
                        {selectedTrip.driver?.full_name?.charAt(0) || <User className="w-5 h-5" />}
                      </div>
                      <div>
                        <div className="font-bold text-gray-900">{selectedTrip.driver?.full_name || 'Unknown Driver'}</div>
                        <div className="text-xs text-gray-500">{selectedTrip.driver?.email || 'No Email'}</div>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Schedule Source</h3>
                      <div className="font-medium text-gray-900">SCH-{selectedTrip.schedule_id.toString().padStart(3, '0')}</div>
                    </div>
                    <div>
                      <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Session Date</h3>
                      <div className="font-medium text-gray-900">{new Date(selectedTrip.session_date).toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', dateStyle: 'medium'})}</div>
                    </div>
                  </div>

                  <div className="border-t border-gray-100 pt-6">
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4">Journey Times</h3>
                    <div className="grid grid-cols-3 gap-2">
                      <div className="text-center p-3 rounded-lg border border-gray-100">
                        <div className="text-xs text-gray-500 mb-1">Scheduled</div>
                        <div className="font-bold text-gray-900">{selectedTrip.schedule?.start_time?.substring(0, 5) || '—'}</div>
                      </div>
                      <div className="text-center p-3 rounded-lg border border-blue-100 bg-blue-50">
                        <div className="text-xs text-blue-600 mb-1">Started At</div>
                        <div className="font-bold text-blue-900">{formatTimeOnly(selectedTrip.started_at)}</div>
                      </div>
                      <div className="text-center p-3 rounded-lg border border-gray-100">
                        <div className="text-xs text-gray-500 mb-1">Ended At</div>
                        <div className="font-bold text-gray-900">{formatTimeOnly(selectedTrip.ended_at)}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Panel: Route Map */}
              <div className="w-full md:w-1/2 bg-gray-50 relative flex flex-col max-h-[60vh] md:max-h-none">
                <div className="absolute top-4 right-4 z-10 hidden md:block">
                  <button onClick={() => setIsViewModalOpen(false)} className="bg-white p-2 rounded-full shadow-sm border border-gray-200 text-gray-500 hover:text-gray-800 transition-colors">
                    <X className="w-5 h-5" />
                  </button>
                </div>
                
                <div className="p-6 md:p-8 flex-1 overflow-y-auto">
                  <h3 className="text-lg font-bold text-gray-900 mb-1">{selectedTrip.route?.name || 'Unknown Route'}</h3>
                  <div className={`text-xs font-bold uppercase tracking-wider mb-6 inline-block px-2 py-1 rounded ${selectedTrip.direction === 'MORNING' ? 'bg-orange-100 text-orange-800' : 'bg-purple-100 text-purple-800'}`}>
                    {selectedTrip.direction} DIRECTION
                  </div>

                  {routeStops.length === 0 ? (
                    <div className="text-center py-8 px-4 border-2 border-dashed border-gray-200 rounded-lg">
                      <Map className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                      <p className="text-sm text-gray-500">No stops configured for this direction.</p>
                    </div>
                  ) : (
                    <div className="relative border-l-2 border-blue-200 ml-4 space-y-6 pb-4 mt-2">
                      {routeStops.map((stop: RouteStop, idx: number) => {
                        const isFirst = idx === 0;
                        const isLast = idx === routeStops.length - 1;
                        return (
                          <div key={stop.boarding_point_id} className="relative pl-6">
                            <div className={`absolute -left-[9px] top-0.5 w-4 h-4 rounded-full border-2 border-white shadow-sm flex items-center justify-center ${isFirst ? 'bg-green-500' : isLast ? 'bg-red-500' : 'bg-gray-300'}`} />
                            <div className="font-medium text-gray-900 leading-none pt-0.5 mb-1">
                              {stop.boarding_point?.name || 'Unknown Stop'}
                            </div>
                            <div className="text-xs text-gray-500">Stop {idx + 1}</div>
                          </div>
                        );
                      })}
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
