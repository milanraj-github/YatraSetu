import { useState, useEffect } from 'react';
import { alertService, busService, driverService, routeService } from '../services/api';
import { AlertTriangle, CheckCircle, Search, Info, ShieldAlert, AlertCircle, X, Bell, Truck, User, Map as MapIcon, Calendar } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Alert {
  id: number;
  type: string;
  severity: string;
  status: string;
  bus_id: number | null;
  driver_id: number | null;
  route_id: number | null;
  trip_id: number | null;
  description: string;
  source: string;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

// Minimal joins
interface Bus { id: number; bus_number: string; }
interface Driver { id: number; full_name: string; }
interface Route { id: number; name: string; }

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [buses, setBuses] = useState<Bus[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [routes, setRoutes] = useState<Route[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [filterSeverity, setFilterSeverity] = useState('ALL');
  const [filterStatus, setFilterStatus] = useState('ACTIVE');
  const [filterType, setFilterType] = useState('ALL');

  // Modals
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [isResolveModalOpen, setIsResolveModalOpen] = useState(false);
  const [alertToResolve, setAlertToResolve] = useState<number | null>(null);
  const [resolving, setResolving] = useState(false);

  useEffect(() => {
    fetchData();
    // Use simple polling to simulate live alert feed (since WS not fully present)
    const interval = setInterval(() => {
      fetchData(false);
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async (showLoad = true) => {
    if (showLoad) setLoading(true);
    try {
      const [alertRes, busRes, driverRes, routeRes] = await Promise.all([
        alertService.getAll(), // Fetch up to 100 recent
        busService.getAll(),
        driverService.getAll(),
        routeService.getAll()
      ]);
      setAlerts(alertRes.data || []);
      setBuses(busRes.data || []);
      setDrivers(driverRes.data || []);
      setRoutes(routeRes.data || []);
      setError(null);
    } catch (err: any) {
      console.error(err);
      if (showLoad) setError('Unable to load alerts.');
    } finally {
      if (showLoad) setLoading(false);
    }
  };

  const handleResolve = async () => {
    if (!alertToResolve) return;
    setResolving(true);
    try {
      await alertService.resolve(alertToResolve);
      await fetchData(false);
      setIsResolveModalOpen(false);
      setAlertToResolve(null);
      if (selectedAlert?.id === alertToResolve) {
        setSelectedAlert(prev => prev ? { ...prev, status: 'RESOLVED', resolved_at: new Date().toISOString() } : null);
      }
    } catch (err) {
      console.error(err);
      alert('Failed to resolve alert.');
    } finally {
      setResolving(false);
    }
  };

  // Join data
  const augmentedAlerts = alerts.map(a => ({
    ...a,
    bus: buses.find(b => b.id === a.bus_id),
    driver: drivers.find(d => d.id === a.driver_id),
    route: routes.find(r => r.id === a.route_id)
  }));

  // Filter
  const filteredAlerts = augmentedAlerts.filter(a => {
    const searchLower = searchTerm.toLowerCase();
    const matchesSearch = 
      `ALT-${a.id}`.toLowerCase().includes(searchLower) ||
      (a.bus?.bus_number || '').toLowerCase().includes(searchLower) ||
      (a.driver?.full_name || '').toLowerCase().includes(searchLower) ||
      a.type.toLowerCase().includes(searchLower);

    const matchesSeverity = filterSeverity === 'ALL' || a.severity === filterSeverity;
    const matchesStatus = filterStatus === 'ALL' || a.status === filterStatus;
    const matchesType = filterType === 'ALL' || a.type === filterType;

    return matchesSearch && matchesSeverity && matchesStatus && matchesType;
  });

  const activeAlerts = augmentedAlerts.filter(a => a.status === 'ACTIVE');
  const stats = {
    active: activeAlerts.length,
    critical: activeAlerts.filter(a => a.severity === 'CRITICAL').length,
    warning: activeAlerts.filter(a => a.severity === 'WARNING').length,
    info: activeAlerts.filter(a => a.severity === 'INFO').length,
    resolvedToday: augmentedAlerts.filter(a => a.status === 'RESOLVED' && new Date(a.resolved_at!).toDateString() === new Date().toDateString()).length
  };

  const severityConfig: Record<string, { color: string; bg: string; icon: any }> = {
    CRITICAL: { color: 'text-red-700', bg: 'bg-red-100', icon: ShieldAlert },
    WARNING: { color: 'text-orange-700', bg: 'bg-orange-100', icon: AlertTriangle },
    INFO: { color: 'text-blue-700', bg: 'bg-blue-100', icon: Info },
  };

  const formatTime = (isoString: string) => {
    return new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
      month: 'short', day: 'numeric'
    }).format(new Date(isoString));
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            <Bell className="w-6 h-6 mr-2 text-red-600" />
            Alerts
          </h1>
          <p className="text-sm text-gray-500">Monitor operational and system alerts across the SMARTBUS network.</p>
        </div>
        <div className="flex items-center">
          <span className="flex items-center text-sm text-green-700 bg-green-50 px-3 py-1.5 rounded-full border border-green-200">
            <span className="w-2 h-2 rounded-full bg-green-500 mr-2 animate-pulse"></span>
            Live Alert Feed
          </span>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg flex items-center shadow-sm border border-red-100">
          <AlertCircle className="w-5 h-5 mr-2" />
          {error}
        </div>
      )}

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white p-4 md:p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-sm text-gray-500 font-medium mb-1">Active Alerts</div>
          <div className="text-2xl font-bold text-gray-900">{stats.active}</div>
        </div>
        <div className={`bg-white p-4 md:p-6 rounded-xl border shadow-sm ${stats.critical > 0 ? 'border-red-300 bg-red-50' : 'border-gray-200'}`}>
          <div className={`text-sm font-medium mb-1 ${stats.critical > 0 ? 'text-red-700' : 'text-gray-500'}`}>Critical</div>
          <div className={`text-2xl font-bold ${stats.critical > 0 ? 'text-red-700' : 'text-gray-900'}`}>{stats.critical}</div>
        </div>
        <div className={`bg-white p-4 md:p-6 rounded-xl border shadow-sm ${stats.warning > 0 ? 'border-orange-300 bg-orange-50' : 'border-gray-200'}`}>
          <div className={`text-sm font-medium mb-1 ${stats.warning > 0 ? 'text-orange-700' : 'text-gray-500'}`}>Warning</div>
          <div className={`text-2xl font-bold ${stats.warning > 0 ? 'text-orange-700' : 'text-gray-900'}`}>{stats.warning}</div>
        </div>
        <div className="bg-white p-4 md:p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-sm text-blue-600 font-medium mb-1">Info</div>
          <div className="text-2xl font-bold text-gray-900">{stats.info}</div>
        </div>
        <div className="bg-white p-4 md:p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-sm text-green-600 font-medium mb-1">Resolved Today</div>
          <div className="text-2xl font-bold text-gray-900">{stats.resolvedToday}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-wrap gap-4">
        <div className="flex-1 min-w-[200px] relative">
          <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search alerts..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>
        <div className="w-full md:w-36">
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg outline-none text-sm text-gray-700">
            <option value="ALL">All Status</option>
            <option value="ACTIVE">Active</option>
            <option value="RESOLVED">Resolved</option>
          </select>
        </div>
        <div className="w-full md:w-36">
          <select value={filterSeverity} onChange={(e) => setFilterSeverity(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg outline-none text-sm text-gray-700">
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="WARNING">Warning</option>
            <option value="INFO">Info</option>
          </select>
        </div>
        <div className="w-full md:w-40">
          <select value={filterType} onChange={(e) => setFilterType(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg outline-none text-sm text-gray-700">
            <option value="ALL">All Types</option>
            <option value="GPS_STALE">GPS Stale</option>
            <option value="GPS_DISCONNECTED">GPS Disconnected</option>
            <option value="ROUTE_DEVIATION">Route Deviation</option>
            <option value="TRIP_ISSUE">Trip Issue</option>
            <option value="BUS_ISSUE">Bus Issue</option>
            <option value="SCHEDULE_ISSUE">Schedule Issue</option>
            <option value="SYSTEM">System</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm overflow-x-auto">
        {loading ? (
          <div className="p-12 text-center text-gray-500">Loading alerts...</div>
        ) : filteredAlerts.length === 0 ? (
          <div className="p-16 text-center flex flex-col items-center justify-center">
            <CheckCircle className="w-12 h-12 text-green-400 mb-4" />
            <p className="text-gray-900 font-bold text-lg">All systems are currently clear.</p>
            <p className="text-sm text-gray-500 mt-1">No alerts match your current filters.</p>
          </div>
        ) : (
          <table className="w-full text-left text-sm text-gray-600 min-w-[900px]">
            <thead className="bg-gray-50 border-b border-gray-200 text-gray-700">
              <tr>
                <th className="px-6 py-4 font-medium">Alert</th>
                <th className="px-6 py-4 font-medium">Severity</th>
                <th className="px-6 py-4 font-medium">Bus</th>
                <th className="px-6 py-4 font-medium">Type</th>
                <th className="px-6 py-4 font-medium">Created</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredAlerts.map((alert: any) => {
                const config = severityConfig[alert.severity] || severityConfig.INFO;
                const Icon = config.icon;
                return (
                  <tr key={alert.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-bold text-gray-900">ALT-{alert.id.toString().padStart(3, '0')}</div>
                      <div className="text-xs text-gray-500 truncate max-w-[200px]" title={alert.description}>{alert.description}</div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold ${config.bg} ${config.color}`}>
                        <Icon className="w-3 h-3 mr-1" />
                        {alert.severity}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-medium text-gray-900">
                      {alert.bus?.bus_number || '—'}
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-xs font-mono bg-gray-100 px-2 py-1 rounded text-gray-700 border border-gray-200">
                        {alert.type}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-medium text-gray-700">
                      {formatTime(alert.created_at)}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded text-xs font-bold ${alert.status === 'ACTIVE' ? 'bg-red-100 text-red-700 border border-red-200' : 'bg-gray-100 text-gray-600 border border-gray-200'}`}>
                        {alert.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <button onClick={() => setSelectedAlert(alert)} className="text-blue-600 hover:text-blue-800 font-medium px-2 py-1 transition-colors">
                        View
                      </button>
                      {alert.status === 'ACTIVE' && (
                        <button onClick={() => { setAlertToResolve(alert.id); setIsResolveModalOpen(true); }} className="text-green-600 hover:text-green-800 font-medium px-2 py-1 transition-colors border border-green-200 bg-green-50 hover:bg-green-100 rounded">
                          Resolve
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Details Modal */}
      {selectedAlert && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl overflow-hidden">
            <div className="flex justify-between items-center p-6 border-b border-gray-100">
              <h2 className="text-xl font-bold text-gray-900">Alert Details: ALT-{selectedAlert.id.toString().padStart(3, '0')}</h2>
              <button onClick={() => setSelectedAlert(null)} className="text-gray-400 hover:text-gray-600">
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="p-6 space-y-6">
              
              <div className="flex justify-between items-center p-4 bg-gray-50 rounded-lg border border-gray-200">
                <div className="space-y-1">
                  <div className="text-sm font-bold text-gray-500">TYPE</div>
                  <div className="font-mono text-sm text-gray-900 font-bold">{selectedAlert.type}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-sm font-bold text-gray-500">SEVERITY</div>
                  <div className={`font-bold text-sm ${severityConfig[selectedAlert.severity]?.color}`}>{selectedAlert.severity}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-sm font-bold text-gray-500">STATUS</div>
                  <div className={`font-bold text-sm ${selectedAlert.status === 'ACTIVE' ? 'text-red-600' : 'text-gray-600'}`}>{selectedAlert.status}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-sm font-bold text-gray-500">CREATED</div>
                  <div className="font-bold text-sm text-gray-900">{formatTime(selectedAlert.created_at)}</div>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-bold text-gray-900 mb-2">Description</h3>
                <p className="text-gray-700 bg-gray-50 p-4 rounded-lg border border-gray-100">{selectedAlert.description}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {selectedAlert.bus_id && (
                   <div className="border border-gray-200 p-4 rounded-lg">
                     <div className="text-xs font-bold text-gray-400 mb-2 flex items-center"><Truck className="w-4 h-4 mr-1"/> BUS</div>
                     <div className="font-bold text-gray-900 mb-2">{(selectedAlert as any).bus?.bus_number || `ID: ${selectedAlert.bus_id}`}</div>
                     <Link to="/live" className="text-blue-600 text-sm hover:underline">View on Live Map</Link>
                   </div>
                )}
                {selectedAlert.driver_id && (
                   <div className="border border-gray-200 p-4 rounded-lg">
                     <div className="text-xs font-bold text-gray-400 mb-2 flex items-center"><User className="w-4 h-4 mr-1"/> DRIVER</div>
                     <div className="font-bold text-gray-900">{(selectedAlert as any).driver?.full_name || `ID: ${selectedAlert.driver_id}`}</div>
                   </div>
                )}
                {selectedAlert.route_id && (
                   <div className="border border-gray-200 p-4 rounded-lg">
                     <div className="text-xs font-bold text-gray-400 mb-2 flex items-center"><MapIcon className="w-4 h-4 mr-1"/> ROUTE</div>
                     <div className="font-bold text-gray-900 mb-2">{(selectedAlert as any).route?.name || `ID: ${selectedAlert.route_id}`}</div>
                     <Link to="/routes" className="text-blue-600 text-sm hover:underline">View Route Details</Link>
                   </div>
                )}
                {selectedAlert.trip_id && (
                   <div className="border border-gray-200 p-4 rounded-lg">
                     <div className="text-xs font-bold text-gray-400 mb-2 flex items-center"><Calendar className="w-4 h-4 mr-1"/> TRIP</div>
                     <div className="font-bold text-gray-900 mb-2">TRIP-{selectedAlert.trip_id.toString().padStart(3, '0')}</div>
                     <Link to="/trips" className="text-blue-600 text-sm hover:underline">View Trip Details</Link>
                   </div>
                )}
              </div>

            </div>
            <div className="p-6 bg-gray-50 border-t border-gray-100 flex justify-end space-x-3">
              <button onClick={() => setSelectedAlert(null)} className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 bg-white hover:bg-gray-50 font-medium">
                Close
              </button>
              {selectedAlert.status === 'ACTIVE' && (
                <button onClick={() => { setAlertToResolve(selectedAlert.id); setIsResolveModalOpen(true); }} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium">
                  Resolve Alert
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Resolve Confirmation Modal */}
      {isResolveModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm overflow-hidden p-6 text-center">
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
            <h3 className="text-lg font-bold text-gray-900 mb-2">Resolve Alert?</h3>
            <p className="text-sm text-gray-500 mb-6">Are you sure you want to mark this alert as resolved? This action will be logged.</p>
            <div className="flex justify-center space-x-3">
              <button onClick={() => setIsResolveModalOpen(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium">
                Cancel
              </button>
              <button onClick={handleResolve} disabled={resolving} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium disabled:opacity-50 flex items-center">
                {resolving ? 'Resolving...' : 'Confirm Resolve'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
