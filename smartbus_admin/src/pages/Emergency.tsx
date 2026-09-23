import { useState, useEffect } from 'react';
import { emergencyService, busService, driverService, routeService } from '../services/api';
import { Siren, ShieldAlert, CheckCircle, Search, Truck, User, Map as MapIcon, Calendar, X, AlertOctagon, AlertTriangle } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Emergency {
  id: number;
  type: string;
  severity: string;
  status: string;
  bus_id: number | null;
  driver_id: number | null;
  route_id: number | null;
  trip_id: number | null;
  latitude: number | null;
  longitude: number | null;
  accuracy: number | null;
  description: string | null;
  created_at: string;
  updated_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
}

// Minimal joins
interface Bus { id: number; bus_number: string; registration_number: string; }
interface Driver { id: number; full_name: string; email: string; }
interface Route { id: number; name: string; }

export default function EmergencyCenter() {
  const [emergencies, setEmergencies] = useState<Emergency[]>([]);
  const [buses, setBuses] = useState<Bus[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [routes, setRoutes] = useState<Route[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [filterType, setFilterType] = useState('ALL');

  // Modals
  const [selectedEvent, setSelectedEvent] = useState<Emergency | null>(null);
  
  // Action Modals
  const [actionEventId, setActionEventId] = useState<number | null>(null);
  const [actionType, setActionType] = useState<'ACKNOWLEDGE' | 'RESOLVE' | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => {
      fetchData(false);
    }, 10000); // 10s poll
    return () => clearInterval(interval);
  }, []);

  const fetchData = async (showLoad = true) => {
    if (showLoad) setLoading(true);
    try {
      const [emRes, busRes, driverRes, routeRes] = await Promise.all([
        emergencyService.getAll(),
        busService.getAll(),
        driverService.getAll(),
        routeService.getAll()
      ]);
      setEmergencies(emRes.data || []);
      setBuses(busRes.data || []);
      setDrivers(driverRes.data || []);
      setRoutes(routeRes.data || []);
      setError(null);
    } catch (err: any) {
      console.error(err);
      if (showLoad) setError('Unable to load emergency events.');
    } finally {
      if (showLoad) setLoading(false);
    }
  };

  const handleAction = async () => {
    if (!actionEventId || !actionType) return;
    setIsProcessing(true);
    try {
      if (actionType === 'ACKNOWLEDGE') {
        await emergencyService.acknowledge(actionEventId);
      } else if (actionType === 'RESOLVE') {
        await emergencyService.resolve(actionEventId);
      }
      await fetchData(false);
      setActionEventId(null);
      setActionType(null);
      
      // Update local selected event if open
      if (selectedEvent?.id === actionEventId) {
        setSelectedEvent(prev => prev ? { 
          ...prev, 
          status: actionType === 'ACKNOWLEDGE' ? 'ACKNOWLEDGED' : 'RESOLVED',
          acknowledged_at: actionType === 'ACKNOWLEDGE' ? new Date().toISOString() : prev.acknowledged_at,
          resolved_at: actionType === 'RESOLVE' ? new Date().toISOString() : prev.resolved_at
        } : null);
      }
    } catch (err) {
      console.error(err);
      alert(`Failed to ${actionType.toLowerCase()} emergency.`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Join data
  const augmentedEmergencies = emergencies.map(e => ({
    ...e,
    bus: buses.find(b => b.id === e.bus_id),
    driver: drivers.find(d => d.id === e.driver_id),
    route: routes.find(r => r.id === e.route_id)
  }));

  // Filter
  const filteredEmergencies = augmentedEmergencies.filter(e => {
    const searchLower = searchTerm.toLowerCase();
    const matchesSearch = 
      `EMG-${e.id}`.toLowerCase().includes(searchLower) ||
      (e.bus?.bus_number || '').toLowerCase().includes(searchLower) ||
      (e.driver?.full_name || '').toLowerCase().includes(searchLower) ||
      e.type.toLowerCase().includes(searchLower);

    const matchesStatus = filterStatus === 'ALL' || e.status === filterStatus;
    const matchesType = filterType === 'ALL' || e.type === filterType;

    return matchesSearch && matchesStatus && matchesType;
  });

  const activeEmergencies = augmentedEmergencies.filter(e => e.status === 'ACTIVE');
  const stats = {
    active: activeEmergencies.length,
    critical: activeEmergencies.filter(e => e.severity === 'CRITICAL').length,
    acknowledged: augmentedEmergencies.filter(e => e.status === 'ACKNOWLEDGED').length,
    resolvedToday: augmentedEmergencies.filter(e => e.status === 'RESOLVED' && new Date(e.resolved_at!).toDateString() === new Date().toDateString()).length
  };

  const formatTime = (isoString: string | null) => {
    if (!isoString) return '—';
    return new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
      month: 'short', day: 'numeric'
    }).format(new Date(isoString));
  };

  const formatType = (type: string) => {
    if (type === 'MANUAL_SOS') return 'Manual SOS';
    if (type === 'AUTOMATIC_ACCIDENT') return 'Accident Detected';
    return type;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            <Siren className="w-6 h-6 mr-2 text-red-600 animate-pulse" />
            Emergency Center
          </h1>
          <p className="text-sm text-gray-500">Monitor and respond to active safety emergencies.</p>
        </div>
        <div className="flex items-center">
          <span className="flex items-center text-sm text-green-700 bg-green-50 px-3 py-1.5 rounded-full border border-green-200">
            <span className="w-2 h-2 rounded-full bg-green-500 mr-2 animate-pulse"></span>
            Live Event Feed Connected
          </span>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg flex items-center shadow-sm border border-red-100">
          <ShieldAlert className="w-5 h-5 mr-2" />
          {error}
        </div>
      )}

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className={`p-4 md:p-6 rounded-xl border shadow-sm ${stats.active > 0 ? 'bg-red-600 text-white border-red-700 animate-pulse' : 'bg-white border-gray-200'}`}>
          <div className={`text-sm font-bold mb-1 ${stats.active > 0 ? 'text-red-100' : 'text-gray-500'}`}>ACTIVE EMERGENCIES</div>
          <div className={`text-3xl font-bold ${stats.active > 0 ? 'text-white' : 'text-gray-900'}`}>{stats.active}</div>
        </div>
        <div className={`p-4 md:p-6 rounded-xl border shadow-sm ${stats.critical > 0 ? 'border-red-300 bg-red-50' : 'bg-white border-gray-200'}`}>
          <div className={`text-sm font-bold mb-1 ${stats.critical > 0 ? 'text-red-700' : 'text-gray-500'}`}>CRITICAL</div>
          <div className={`text-2xl font-bold ${stats.critical > 0 ? 'text-red-700' : 'text-gray-900'}`}>{stats.critical}</div>
        </div>
        <div className="bg-white p-4 md:p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-sm font-bold text-orange-600 mb-1">ACKNOWLEDGED</div>
          <div className="text-2xl font-bold text-gray-900">{stats.acknowledged}</div>
        </div>
        <div className="bg-white p-4 md:p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-sm font-bold text-gray-500 mb-1">RESOLVED TODAY</div>
          <div className="text-2xl font-bold text-gray-900">{stats.resolvedToday}</div>
        </div>
      </div>

      {/* Prominent Active Emergencies Section */}
      {activeEmergencies.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-bold text-red-700 flex items-center">
            <AlertOctagon className="w-5 h-5 mr-2" />
            REQUIRES IMMEDIATE ACTION
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeEmergencies.map((em: any) => (
              <div key={em.id} className="bg-white rounded-xl shadow-lg border-2 border-red-500 overflow-hidden flex flex-col">
                <div className="bg-red-600 text-white p-3 flex justify-between items-center">
                  <div className="font-bold flex items-center">
                    <Siren className="w-4 h-4 mr-1.5" />
                    {formatType(em.type).toUpperCase()}
                  </div>
                  <div className="text-xs font-bold bg-white/20 px-2 py-0.5 rounded">
                    EMG-{em.id}
                  </div>
                </div>
                <div className="p-4 space-y-3 flex-1">
                  <div className="flex justify-between items-start text-sm">
                    <span className="text-gray-500 font-bold w-20">BUS:</span>
                    <span className="font-bold text-gray-900 text-right">{em.bus?.bus_number || '—'}</span>
                  </div>
                  <div className="flex justify-between items-start text-sm">
                    <span className="text-gray-500 font-bold w-20">DRIVER:</span>
                    <span className="font-bold text-gray-900 text-right">{em.driver?.full_name || '—'}</span>
                  </div>
                  <div className="flex justify-between items-start text-sm">
                    <span className="text-gray-500 font-bold w-20">TIME:</span>
                    <span className="font-bold text-red-600 text-right">{formatTime(em.created_at)}</span>
                  </div>
                  {em.latitude ? (
                    <div className="flex justify-between items-start text-sm pt-2 border-t border-gray-100">
                      <span className="text-gray-500 font-bold w-20">LOCATION:</span>
                      <Link to="/live" className="text-blue-600 font-bold hover:underline flex items-center text-right">
                        <MapIcon className="w-3 h-3 mr-1" /> View on Map
                      </Link>
                    </div>
                  ) : (
                    <div className="flex justify-between items-start text-sm pt-2 border-t border-gray-100">
                      <span className="text-gray-500 font-bold w-20">LOCATION:</span>
                      <span className="text-gray-400 italic text-right">Unavailable</span>
                    </div>
                  )}
                </div>
                <div className="p-3 bg-gray-50 border-t border-gray-200 flex gap-2">
                  <button onClick={() => { setActionEventId(em.id); setActionType('ACKNOWLEDGE'); }} className="flex-1 bg-orange-100 text-orange-700 font-bold py-2 rounded border border-orange-300 hover:bg-orange-200 transition-colors">
                    ACKNOWLEDGE
                  </button>
                  <button onClick={() => setSelectedEvent(em)} className="flex-1 bg-white border border-gray-300 text-gray-700 font-bold py-2 rounded hover:bg-gray-50 transition-colors">
                    DETAILS
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-wrap gap-4">
        <div className="flex-1 min-w-[200px] relative">
          <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search emergencies..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>
        <div className="w-full md:w-40">
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg outline-none text-sm text-gray-700">
            <option value="ALL">All Status</option>
            <option value="ACTIVE">Active</option>
            <option value="ACKNOWLEDGED">Acknowledged</option>
            <option value="RESOLVED">Resolved</option>
          </select>
        </div>
        <div className="w-full md:w-48">
          <select value={filterType} onChange={(e) => setFilterType(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg outline-none text-sm text-gray-700">
            <option value="ALL">All Emergency Types</option>
            <option value="MANUAL_SOS">Manual SOS</option>
            <option value="AUTOMATIC_ACCIDENT">Accident Detected</option>
          </select>
        </div>
      </div>

      {/* History Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm overflow-x-auto">
        <div className="bg-gray-50 px-6 py-3 border-b border-gray-200 font-bold text-gray-700 flex items-center">
          Emergency History
        </div>
        {loading ? (
          <div className="p-12 text-center text-gray-500">Loading emergency events...</div>
        ) : filteredEmergencies.length === 0 ? (
          <div className="p-16 text-center flex flex-col items-center justify-center">
            <CheckCircle className="w-12 h-12 text-green-400 mb-4" />
            <p className="text-gray-900 font-bold text-lg">No emergency events found.</p>
            <p className="text-sm text-gray-500 mt-1">All monitored trips are currently clear.</p>
          </div>
        ) : (
          <table className="w-full text-left text-sm text-gray-600 min-w-[900px]">
            <thead className="bg-gray-50 border-b border-gray-200 text-gray-700">
              <tr>
                <th className="px-6 py-4 font-bold">Event ID</th>
                <th className="px-6 py-4 font-bold">Type</th>
                <th className="px-6 py-4 font-bold">Bus / Driver</th>
                <th className="px-6 py-4 font-bold">Location</th>
                <th className="px-6 py-4 font-bold">Created</th>
                <th className="px-6 py-4 font-bold">Status</th>
                <th className="px-6 py-4 font-bold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredEmergencies.map((em: any) => {
                return (
                  <tr key={em.id} className={`hover:bg-gray-50 transition-colors ${em.status === 'ACTIVE' ? 'bg-red-50/30' : ''}`}>
                    <td className="px-6 py-4">
                      <div className="font-bold text-gray-900">EMG-{em.id.toString().padStart(3, '0')}</div>
                      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold mt-1 ${em.severity === 'CRITICAL' ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'}`}>
                        {em.severity}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-bold text-gray-900">
                      {formatType(em.type)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-bold text-gray-900">{em.bus?.bus_number || '—'}</div>
                      <div className="text-xs text-gray-500 mt-0.5">{em.driver?.full_name || '—'}</div>
                    </td>
                    <td className="px-6 py-4">
                      {em.latitude ? (
                        <div className="text-xs text-blue-600 font-medium">Valid GPS</div>
                      ) : (
                        <div className="text-xs text-gray-400 italic">Unavailable</div>
                      )}
                    </td>
                    <td className="px-6 py-4 font-medium text-gray-700">
                      {formatTime(em.created_at)}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                        em.status === 'ACTIVE' ? 'bg-red-600 text-white' : 
                        em.status === 'ACKNOWLEDGED' ? 'bg-orange-100 text-orange-700 border border-orange-200' : 
                        'bg-gray-100 text-gray-600 border border-gray-200'
                      }`}>
                        {em.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <button onClick={() => setSelectedEvent(em)} className="text-blue-600 hover:text-blue-800 font-bold px-2 py-1 transition-colors">
                        Details
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Details Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className={`p-6 flex justify-between items-center ${
              selectedEvent.status === 'ACTIVE' ? 'bg-red-600 text-white' : 
              selectedEvent.status === 'ACKNOWLEDGED' ? 'bg-orange-500 text-white' : 
              'bg-gray-800 text-white'
            }`}>
              <div>
                <h2 className="text-xl font-bold flex items-center">
                  {selectedEvent.status === 'ACTIVE' && <Siren className="w-6 h-6 mr-2 animate-pulse" />}
                  EMERGENCY DETAILS: EMG-{selectedEvent.id.toString().padStart(3, '0')}
                </h2>
                <div className="text-white/80 text-sm font-bold mt-1">STATUS: {selectedEvent.status}</div>
              </div>
              <button onClick={() => setSelectedEvent(null)} className="text-white/70 hover:text-white transition-colors">
                <X className="w-8 h-8" />
              </button>
            </div>
            
            <div className="p-6 space-y-6 overflow-y-auto flex-1">
              {/* Event Info */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <div className="text-xs font-bold text-gray-500 mb-1">TYPE</div>
                  <div className="font-bold text-gray-900">{formatType(selectedEvent.type)}</div>
                </div>
                <div>
                  <div className="text-xs font-bold text-gray-500 mb-1">CREATED</div>
                  <div className="font-bold text-gray-900">{formatTime(selectedEvent.created_at)}</div>
                </div>
                {selectedEvent.acknowledged_at && (
                  <div>
                    <div className="text-xs font-bold text-gray-500 mb-1">ACKNOWLEDGED</div>
                    <div className="font-bold text-orange-600">{formatTime(selectedEvent.acknowledged_at)}</div>
                  </div>
                )}
                {selectedEvent.resolved_at && (
                  <div>
                    <div className="text-xs font-bold text-gray-500 mb-1">RESOLVED</div>
                    <div className="font-bold text-gray-600">{formatTime(selectedEvent.resolved_at)}</div>
                  </div>
                )}
              </div>

              {/* Related Entities */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                   <h3 className="text-xs font-bold text-gray-400 mb-3 flex items-center"><Truck className="w-4 h-4 mr-1.5"/> BUS INFORMATION</h3>
                   <div className="space-y-2">
                     <div className="flex justify-between"><span className="text-gray-500">Bus Number:</span> <span className="font-bold text-gray-900">{(selectedEvent as any).bus?.bus_number || '—'}</span></div>
                     <div className="flex justify-between"><span className="text-gray-500">Registration:</span> <span className="font-bold text-gray-900">{(selectedEvent as any).bus?.registration_number || '—'}</span></div>
                     <Link to="/buses" className="text-blue-600 text-xs font-bold hover:underline block mt-2">View Bus Module</Link>
                   </div>
                </div>

                <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                   <h3 className="text-xs font-bold text-gray-400 mb-3 flex items-center"><User className="w-4 h-4 mr-1.5"/> DRIVER INFORMATION</h3>
                   <div className="space-y-2">
                     <div className="flex justify-between"><span className="text-gray-500">Name:</span> <span className="font-bold text-gray-900">{(selectedEvent as any).driver?.full_name || '—'}</span></div>
                     <div className="flex justify-between"><span className="text-gray-500">Email:</span> <span className="font-bold text-gray-900 truncate ml-2">{(selectedEvent as any).driver?.email || '—'}</span></div>
                   </div>
                </div>

                <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                   <h3 className="text-xs font-bold text-gray-400 mb-3 flex items-center"><Calendar className="w-4 h-4 mr-1.5"/> TRIP INFORMATION</h3>
                   <div className="space-y-2">
                     <div className="flex justify-between"><span className="text-gray-500">Trip ID:</span> <span className="font-bold text-gray-900">{selectedEvent.trip_id ? `TRIP-${selectedEvent.trip_id.toString().padStart(3, '0')}` : '—'}</span></div>
                     <div className="flex justify-between"><span className="text-gray-500">Route:</span> <span className="font-bold text-gray-900 truncate ml-2">{(selectedEvent as any).route?.name || '—'}</span></div>
                     {selectedEvent.trip_id && <Link to="/trips" className="text-blue-600 text-xs font-bold hover:underline block mt-2">View Trip Details</Link>}
                   </div>
                </div>

                <div className="border border-gray-200 rounded-lg p-4 bg-blue-50/50">
                   <h3 className="text-xs font-bold text-blue-600 mb-3 flex items-center"><MapIcon className="w-4 h-4 mr-1.5"/> EMERGENCY LOCATION</h3>
                   <div className="space-y-2">
                     {selectedEvent.latitude ? (
                       <>
                         <div className="flex justify-between"><span className="text-gray-500">Latitude:</span> <span className="font-mono font-bold text-gray-900">{selectedEvent.latitude.toFixed(6)}</span></div>
                         <div className="flex justify-between"><span className="text-gray-500">Longitude:</span> <span className="font-mono font-bold text-gray-900">{selectedEvent.longitude!.toFixed(6)}</span></div>
                         <Link to="/live" className="inline-flex items-center justify-center w-full bg-blue-600 text-white font-bold text-xs py-2 rounded mt-2 hover:bg-blue-700 transition-colors">
                           <MapIcon className="w-3.5 h-3.5 mr-1" /> VIEW ON MAP
                         </Link>
                       </>
                     ) : (
                       <div className="text-gray-400 italic py-4 text-center">Location unavailable</div>
                     )}
                   </div>
                </div>
              </div>
              
              {selectedEvent.description && (
                <div>
                  <h3 className="text-xs font-bold text-gray-500 mb-2">ADDITIONAL DETAILS</h3>
                  <div className="bg-gray-50 p-4 border border-gray-200 rounded-lg text-sm text-gray-800">
                    {selectedEvent.description}
                  </div>
                </div>
              )}

            </div>
            <div className="p-4 bg-gray-100 border-t border-gray-200 flex justify-end space-x-3">
              {selectedEvent.status === 'ACTIVE' && (
                <button onClick={() => { setActionEventId(selectedEvent.id); setActionType('ACKNOWLEDGE'); }} className="px-6 py-2 bg-orange-100 text-orange-700 border border-orange-300 rounded-lg hover:bg-orange-200 font-bold shadow-sm">
                  ACKNOWLEDGE
                </button>
              )}
              {(selectedEvent.status === 'ACTIVE' || selectedEvent.status === 'ACKNOWLEDGED') && (
                <button onClick={() => { setActionEventId(selectedEvent.id); setActionType('RESOLVE'); }} className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-bold shadow-sm">
                  RESOLVE
                </button>
              )}
              <button onClick={() => setSelectedEvent(null)} className="px-6 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-bold shadow-sm">
                CLOSE
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Action Confirmation Modal */}
      {actionEventId && actionType && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm overflow-hidden p-6 text-center">
            {actionType === 'ACKNOWLEDGE' ? (
              <AlertTriangle className="w-12 h-12 text-orange-500 mx-auto mb-4" />
            ) : (
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
            )}
            
            <h3 className="text-lg font-bold text-gray-900 mb-2">
              {actionType === 'ACKNOWLEDGE' ? 'Acknowledge Emergency?' : 'Resolve Emergency?'}
            </h3>
            
            <p className="text-sm text-gray-500 mb-6">
              {actionType === 'ACKNOWLEDGE' 
                ? 'This confirms you are investigating the situation. It does not resolve the emergency.' 
                : 'Marking this as resolved indicates the situation has been completely handled.'}
              <br/><br/>
              Your Admin identity and timestamp will be permanently logged.
            </p>
            
            <div className="flex justify-center space-x-3">
              <button onClick={() => { setActionEventId(null); setActionType(null); }} className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-bold">
                Cancel
              </button>
              <button 
                onClick={handleAction} 
                disabled={isProcessing} 
                className={`px-4 py-2 text-white rounded-lg font-bold disabled:opacity-50 flex items-center ${actionType === 'ACKNOWLEDGE' ? 'bg-orange-600 hover:bg-orange-700' : 'bg-green-600 hover:bg-green-700'}`}
              >
                {isProcessing ? 'Processing...' : `Confirm ${actionType}`}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}


