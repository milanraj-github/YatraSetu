import React, { useEffect, useState } from 'react';
import { busService, routeService } from '../services/api';
import { Bus as BusIcon, Plus, Edit2, Trash2, Map, AlertTriangle, X, MapPin } from 'lucide-react';

interface Bus {
  id: number;
  bus_number: string;
  registration_number: string;
  capacity: number;
  status: string;
  route_id: number | null;
  route?: { id: number, name: string, code: string };
}

interface Route {
  id: number;
  name: string;
  code: string;
  stops?: any[];
}

const Buses: React.FC = () => {
  const [buses, setBuses] = useState<Bus[]>([]);
  const [routes, setRoutes] = useState<Route[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals state
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isViewOpen, setIsViewOpen] = useState(false);
  const [currentBus, setCurrentBus] = useState<Bus | null>(null);
  const [currentRouteDetails, setCurrentRouteDetails] = useState<Route | null>(null);

  // Form State
  const [formData, setFormData] = useState({
    bus_number: '',
    registration_number: '',
    capacity: 50,
    status: 'IDLE',
    route_id: '' as string | number,
  });

  const fetchData = async () => {
    try {
      setLoading(true);
      const [busRes, routeRes] = await Promise.all([
        busService.getAll(),
        routeService.getAll()
      ]);
      setBuses(busRes.data);
      setRoutes(routeRes.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail?.message || 'Failed to fetch data. Ensure you have admin access.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleOpenForm = (bus: Bus | null = null) => {
    setError(null);
    if (bus) {
      setCurrentBus(bus);
      setFormData({
        bus_number: bus.bus_number,
        registration_number: bus.registration_number,
        capacity: bus.capacity,
        status: bus.status,
        route_id: bus.route_id || '',
      });
    } else {
      setCurrentBus(null);
      setFormData({
        bus_number: '',
        registration_number: '',
        capacity: 50,
        status: 'IDLE',
        route_id: '',
      });
    }
    setIsFormOpen(true);
  };

  const handleView = async (bus: Bus) => {
    setCurrentBus(bus);
    setCurrentRouteDetails(null);
    setIsViewOpen(true);
    
    // Fetch deeper route details if assigned
    if (bus.route_id) {
      try {
        const res = await routeService.getById(bus.route_id);
        if (res.success) {
          setCurrentRouteDetails(res.data);
        }
      } catch (e) {
        console.error("Failed to fetch route details", e);
      }
    }
  };

  const handleDelete = async (bus: Bus) => {
    if (window.confirm(`Are you sure you want to deactivate ${bus.bus_number}?`)) {
      try {
        await busService.deactivate(bus.id);
        fetchData();
      } catch (err: any) {
        alert(err.response?.data?.detail?.message || 'Failed to deactivate bus.');
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: any = {
        bus_number: formData.bus_number,
        registration_number: formData.registration_number,
        capacity: Number(formData.capacity),
      };
      if (formData.route_id) {
        payload.route_id = Number(formData.route_id);
      }

      if (currentBus) {
        // Only capacity, status, and route_id are updatable currently per our API
        await busService.update(currentBus.id, {
          capacity: payload.capacity,
          status: formData.status,
          route_id: payload.route_id,
        });
      } else {
        // Create does not take status
        await busService.create(payload);
      }
      setIsFormOpen(false);
      fetchData();
    } catch (err: any) {
      let errorMsg = 'Failed to save bus.';
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          // FastAPI 422 Validation Error
          errorMsg = err.response.data.detail.map((d: any) => `${d.loc.join('.')} ${d.msg}`).join(', ');
        } else {
          errorMsg = err.response.data.detail.message || err.response.data.detail;
        }
      }
      alert(errorMsg);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-slate-800">Bus Management</h1>
        <button 
          onClick={() => handleOpenForm(null)}
          className="bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 rounded-lg flex items-center font-medium transition-colors"
        >
          <Plus className="w-5 h-5 mr-2" />
          Add Bus
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 p-4 rounded-lg flex items-start border border-red-200">
          <AlertTriangle className="w-5 h-5 mr-3 flex-shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600">
            <thead className="bg-slate-50 text-slate-500 border-b border-slate-200 uppercase text-xs font-semibold">
              <tr>
                <th className="px-6 py-4">Bus</th>
                <th className="px-6 py-4">Registration</th>
                <th className="px-6 py-4">Capacity</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Assigned Route</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {loading ? (
                <tr><td colSpan={6} className="px-6 py-8 text-center text-slate-400">Loading buses...</td></tr>
              ) : buses.length === 0 ? (
                <tr><td colSpan={6} className="px-6 py-8 text-center text-slate-400">No buses found.</td></tr>
              ) : (
                buses.map((bus) => (
                  <tr key={bus.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div className="w-8 h-8 rounded bg-brand-50 text-brand-500 flex items-center justify-center mr-3">
                          <BusIcon className="w-4 h-4" />
                        </div>
                        <span className="font-semibold text-slate-800">{bus.bus_number}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">{bus.registration_number}</td>
                    <td className="px-6 py-4">{bus.capacity} seats</td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                        bus.status === 'IDLE' ? 'bg-slate-100 text-slate-600' :
                        bus.status === 'IN_TRIP' ? 'bg-blue-100 text-blue-700' :
                        bus.status === 'INACTIVE' ? 'bg-red-100 text-red-700' :
                        'bg-amber-100 text-amber-700'
                      }`}>
                        {bus.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {bus.route ? (
                        <div className="flex items-center text-brand-600">
                          <Map className="w-4 h-4 mr-2" />
                          <span className="font-medium text-xs">{bus.route.name}</span>
                        </div>
                      ) : (
                        <span className="text-slate-400 text-xs italic">Unassigned</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <button onClick={() => handleView(bus)} className="p-1.5 text-blue-500 hover:bg-blue-50 rounded" title="View Details">
                        <MapPin className="w-4 h-4" />
                      </button>
                      <button onClick={() => handleOpenForm(bus)} className="p-1.5 text-slate-500 hover:bg-slate-100 rounded" title="Edit/Assign Route">
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button onClick={() => handleDelete(bus)} className="p-1.5 text-red-500 hover:bg-red-50 rounded" title="Deactivate">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Form Modal */}
      {isFormOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden flex flex-col max-h-full">
            <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center">
              <h2 className="text-lg font-bold text-slate-800">{currentBus ? 'Edit Bus / Assign Route' : 'Add New Bus'}</h2>
              <button onClick={() => setIsFormOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto">
              <form id="bus-form" onSubmit={handleSubmit} className="space-y-4">
                {!currentBus && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Bus Number *</label>
                      <input required value={formData.bus_number} onChange={(e) => setFormData({...formData, bus_number: e.target.value})} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 outline-none" placeholder="e.g. BUS-01" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Registration Number *</label>
                      <input required value={formData.registration_number} onChange={(e) => setFormData({...formData, registration_number: e.target.value})} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 outline-none" placeholder="e.g. KA-20-F-1234" />
                    </div>
                  </>
                )}
                
                {currentBus && (
                  <div className="bg-slate-50 p-3 rounded-lg text-sm text-slate-600 mb-4">
                    <strong>Bus:</strong> {currentBus.bus_number} <br/>
                    <strong>Reg:</strong> {currentBus.registration_number}
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Capacity</label>
                  <input type="number" min="1" max="200" required value={formData.capacity} onChange={(e) => setFormData({...formData, capacity: parseInt(e.target.value)})} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 outline-none" />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Status</label>
                  <select value={formData.status} onChange={(e) => setFormData({...formData, status: e.target.value})} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 outline-none">
                    <option value="IDLE">IDLE</option>
                    <option value="IN_TRIP">IN_TRIP</option>
                    <option value="MAINTENANCE">MAINTENANCE</option>
                    <option value="INACTIVE">INACTIVE</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Assigned Route</label>
                  <select value={formData.route_id} onChange={(e) => setFormData({...formData, route_id: e.target.value})} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 outline-none">
                    <option value="">-- No Route Assigned --</option>
                    {routes.map(r => (
                      <option key={r.id} value={r.id}>{r.name} ({r.code})</option>
                    ))}
                  </select>
                  <p className="text-xs text-slate-500 mt-1">Assigning a route sets the primary coverage area for this bus.</p>
                </div>
              </form>
            </div>
            <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex justify-end space-x-3">
              <button onClick={() => setIsFormOpen(false)} className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-200 rounded-lg transition-colors">Cancel</button>
              <button type="submit" form="bus-form" className="px-4 py-2 bg-brand-500 text-white font-medium hover:bg-brand-600 rounded-lg transition-colors">Save Bus</button>
            </div>
          </div>
        </div>
      )}

      {/* View Details Modal */}
      {isViewOpen && currentBus && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-full">
            <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-900 text-white">
              <h2 className="text-lg font-bold flex items-center"><BusIcon className="w-5 h-5 mr-2 text-brand-500"/> {currentBus.bus_number} Details</h2>
              <button onClick={() => setIsViewOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto space-y-6">
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-slate-500 font-semibold uppercase">Registration</p>
                  <p className="font-medium text-slate-800">{currentBus.registration_number}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 font-semibold uppercase">Capacity</p>
                  <p className="font-medium text-slate-800">{currentBus.capacity} passengers</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 font-semibold uppercase">Status</p>
                  <span className={`inline-block mt-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        currentBus.status === 'IDLE' ? 'bg-slate-100 text-slate-600' :
                        currentBus.status === 'IN_TRIP' ? 'bg-blue-100 text-blue-700' :
                        currentBus.status === 'INACTIVE' ? 'bg-red-100 text-red-700' :
                        'bg-amber-100 text-amber-700'
                      }`}>
                        {currentBus.status}
                  </span>
                </div>
              </div>

              <div className="border-t border-slate-200 pt-4">
                <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4 flex items-center">
                  <Map className="w-4 h-4 mr-2 text-brand-500" /> Route Information
                </h3>
                
                {currentBus.route ? (
                  <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
                    <p className="font-semibold text-slate-800 text-lg mb-1">{currentBus.route.name}</p>
                    <p className="text-xs text-slate-500 mb-4">Route Code: {currentBus.route.code}</p>
                    
                    {currentRouteDetails ? (
                      <div className="relative pl-4 border-l-2 border-brand-200 space-y-4">
                        {currentRouteDetails.stops?.sort((a: any,b: any) => a.sequence_order - b.sequence_order).map((stop: any) => (
                          <div key={stop.id} className="relative">
                            <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-brand-500 border-2 border-white"></div>
                            <p className="text-sm font-medium text-slate-700">{stop.boarding_point.name}</p>
                            <p className="text-xs text-slate-400 text-left">Stop #{stop.sequence_order} • Direction: {stop.direction}</p>
                          </div>
                        ))}
                        {(!currentRouteDetails.stops || currentRouteDetails.stops.length === 0) && (
                          <p className="text-sm text-slate-500 italic">No stops configured for this route.</p>
                        )}
                      </div>
                    ) : (
                      <div className="text-sm text-slate-500 flex items-center">
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-brand-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Loading route stops from database...
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="bg-slate-50 rounded-lg p-6 text-center border border-slate-200 border-dashed">
                    <p className="text-slate-500 text-sm">This bus does not have an assigned route yet.</p>
                    <button onClick={() => { setIsViewOpen(false); handleOpenForm(currentBus); }} className="mt-3 text-brand-600 text-sm font-medium hover:underline">
                      Assign a Route now
                    </button>
                  </div>
                )}
              </div>

            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Buses;
