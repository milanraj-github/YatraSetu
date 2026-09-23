import React, { useState, useEffect } from 'react';
import { routeService, boardingPointService } from '../services/api';
import { AlertCircle, ChevronDown, ChevronUp, MapPin, Plus, Trash2, X } from 'lucide-react';

interface BoardingPoint {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
}

interface RouteStop {
  id: number;
  boarding_point_id: number;
  sequence_order: number;
  direction: string;
  boarding_point: BoardingPoint;
}

interface Route {
  id: number;
  name: string;
  code: string;
  stops: RouteStop[];
  created_at: string;
  updated_at: string;
}

export default function Routes() {
  const [routes, setRoutes] = useState<Route[]>([]);
  const [stops, setStops] = useState<BoardingPoint[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search & Filter state
  const [searchTerm, setSearchTerm] = useState('');
  const [filterDirection, setFilterDirection] = useState('ALL');

  // Modals state
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingRoute, setEditingRoute] = useState<Route | null>(null);
  const [editRouteName, setEditRouteName] = useState('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isManageStopsOpen, setIsManageStopsOpen] = useState(false);
  const [selectedRoute, setSelectedRoute] = useState<Route | null>(null);

  // Form State
  const [newRouteName, setNewRouteName] = useState('');
  const [newRouteCode, setNewRouteCode] = useState('');
  
  // Manage Stops State
  const [selectedDirection, setSelectedDirection] = useState<'MORNING' | 'EVENING'>('MORNING');
  const [newStopId, setNewStopId] = useState<number | ''>('');
  
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [routeRes, stopsRes] = await Promise.all([
        routeService.getAll(),
        boardingPointService.getAll()
      ]);
      setRoutes(routeRes.data || []);
      setStops(stopsRes.data || []);
      setError(null);
    } catch (err: any) {
      setError('Failed to load routes data.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRoute = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRouteName || !newRouteCode) return;
    try {
      await routeService.create({ name: newRouteName, code: newRouteCode });
      setIsAddModalOpen(false);
      setNewRouteName('');
      setNewRouteCode('');
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail?.message || 'Failed to create route');
    }
  };

  
  const openEditModal = (route: Route) => {
    setEditingRoute(route);
    setEditRouteName(route.name);
    setIsEditModalOpen(true);
  };

  const handleUpdateRoute = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingRoute || !editRouteName) return;
    try {
      await routeService.update(editingRoute.id, { name: editRouteName });
      setIsEditModalOpen(false);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail?.message || 'Failed to update route');
    }
  };

  const handleDeleteRoute = async (id: number) => {
    if (!window.confirm('Are you sure you want to deactivate this route? Historical trips will remain intact.')) return;
    try {
      await routeService.delete(id);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail?.message || 'Failed to deactivate route');
    }
  };

  const openManageStops = (route: Route) => {
    setSelectedRoute(route);
    setSelectedDirection('MORNING');
    setIsManageStopsOpen(true);
  };

  const handleAddStop = async () => {
    if (!selectedRoute || !newStopId) return;
    
    const existingStops = selectedRoute.stops.filter(s => s.direction === selectedDirection);
    const newSeq = existingStops.length > 0 ? Math.max(...existingStops.map(s => s.sequence_order)) + 1 : 1;

    try {
      const updatedRoute = await routeService.addStop(selectedRoute.id, {
        boarding_point_id: Number(newStopId),
        sequence_order: newSeq,
        direction: selectedDirection
      });
      setSelectedRoute(updatedRoute.data);
      setNewStopId('');
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail?.message || 'Failed to add stop');
    }
  };

  const handleRemoveStop = async (stopId: number) => {
    if (!selectedRoute) return;
    if (!window.confirm('Remove this stop from the route?')) return;
    try {
      await routeService.removeStop(selectedRoute.id, stopId);
      // Wait wait, removeStop from backend returns Dict not Route. So we need to re-fetch the route by id!
      const refreshedRoute = await routeService.getById(selectedRoute.id);
      setSelectedRoute(refreshedRoute.data);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail?.message || 'Failed to remove stop');
    }
  };

  const handleReorder = async (currentIndex: number, direction: 'up' | 'down') => {
    if (!selectedRoute) return;
    
    // Get stops for current direction, sorted by sequence order
    const directionStops = [...selectedRoute.stops]
      .filter(s => s.direction === selectedDirection)
      .sort((a, b) => a.sequence_order - b.sequence_order);

    if (direction === 'up' && currentIndex > 0) {
      const prevStop = directionStops[currentIndex - 1];
      const currentStop = directionStops[currentIndex];
      
      const payload = [
        { route_stop_id: currentStop.id, new_sequence_order: prevStop.sequence_order },
        { route_stop_id: prevStop.id, new_sequence_order: currentStop.sequence_order }
      ];
      
      try {
        const updatedRoute = await routeService.reorderStops(selectedRoute.id, payload);
        setSelectedRoute(updatedRoute.data);
        fetchData();
      } catch (err: any) {
        alert(err.response?.data?.detail?.message || 'Failed to update stop order');
      }
    } else if (direction === 'down' && currentIndex < directionStops.length - 1) {
      const currentStop = directionStops[currentIndex];
      const nextStop = directionStops[currentIndex + 1];

      const payload = [
        { route_stop_id: currentStop.id, new_sequence_order: nextStop.sequence_order },
        { route_stop_id: nextStop.id, new_sequence_order: currentStop.sequence_order }
      ];

      try {
        const updatedRoute = await routeService.reorderStops(selectedRoute.id, payload);
        setSelectedRoute(updatedRoute.data);
        fetchData();
      } catch (err: any) {
        alert(err.response?.data?.detail?.message || 'Failed to update stop order');
      }
    }
  };

  // Helper to determine route directions
  const getRouteDirections = (route: Route) => {
    const dirs = new Set(route.stops.map(s => s.direction));
    if (dirs.size === 0) return 'NONE';
    return Array.from(dirs).join(' / ');
  };

  const filteredRoutes = routes.filter(r => {
    const matchesSearch = r.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          r.code.toLowerCase().includes(searchTerm.toLowerCase());
    
    let matchesDirection = true;
    if (filterDirection !== 'ALL') {
      matchesDirection = r.stops.some(s => s.direction === filterDirection);
    }
    
    return matchesSearch && matchesDirection;
  });

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Routes</h1>
          <p className="text-sm text-gray-500">Manage bus routes, directions and stop sequences.</p>
        </div>
        <button
          onClick={() => setIsAddModalOpen(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition flex items-center"
        >
          <Plus className="w-5 h-5 mr-1" />
          Add Route
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg flex items-center">
          <AlertCircle className="w-5 h-5 mr-2" />
          {error}
        </div>
      )}

      {/* Search & Filters */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 flex flex-col md:flex-row gap-4">
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-700 mb-1">Search Routes</label>
          <input
            type="text"
            placeholder="Search by name or code..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          />
        </div>
        <div className="w-full md:w-48">
          <label className="block text-sm font-medium text-gray-700 mb-1">Direction</label>
          <select
            value={filterDirection}
            onChange={(e) => setFilterDirection(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          >
            <option value="ALL">All</option>
            <option value="MORNING">Morning</option>
            <option value="EVENING">Evening</option>
          </select>
        </div>
      </div>

      {/* Routes Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Loading routes...</div>
        ) : filteredRoutes.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-500 mb-4">No routes found.</p>
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="text-blue-600 font-medium hover:underline"
            >
              + Add your first route
            </button>
          </div>
        ) : (
          <table className="w-full text-left text-sm text-gray-600">
            <thead className="bg-gray-50 border-b border-gray-200 text-gray-700">
              <tr>
                <th className="px-6 py-4 font-medium">Route</th>
                <th className="px-6 py-4 font-medium">Code</th>
                <th className="px-6 py-4 font-medium">Direction</th>
                <th className="px-6 py-4 font-medium">Stops</th>
                <th className="px-6 py-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredRoutes.map((route) => (
                <tr key={route.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 font-medium text-gray-900">{route.name}</td>
                  <td className="px-6 py-4">{route.code}</td>
                  <td className="px-6 py-4">
                    <span className="px-2.5 py-1 bg-gray-100 text-gray-800 rounded-full text-xs font-medium">
                      {getRouteDirections(route)}
                    </span>
                  </td>
                  <td className="px-6 py-4">{route.stops.length} Stops</td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => openEditModal(route)}
                      className="text-blue-600 hover:text-blue-800 font-medium mr-4"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => openManageStops(route)}
                      className="text-blue-600 hover:text-blue-800 font-medium mr-4"
                    >
                      Manage Stops
                    </button>
                    <button
                      onClick={() => handleDeleteRoute(route.id)}
                      className="text-red-600 hover:text-red-800 font-medium"
                    >
                      Deactivate
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Add Route Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="flex justify-between items-center p-6 border-b border-gray-100">
              <h2 className="text-xl font-bold text-gray-900">Add Route</h2>
              <button onClick={() => setIsAddModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateRoute} className="p-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Route Name</label>
                  <input
                    type="text"
                    required
                    value={newRouteName}
                    onChange={(e) => setNewRouteName(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                    placeholder="e.g. Santhakatte to College"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Route Code</label>
                  <input
                    type="text"
                    required
                    value={newRouteCode}
                    onChange={(e) => setNewRouteCode(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                    placeholder="e.g. RT-01"
                  />
                </div>
                <div className="bg-blue-50 text-blue-800 text-xs p-3 rounded">
                  Note: Directions and Status are configured via route stops after the route is created.
                </div>
              </div>
              <div className="mt-8 flex gap-3">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700"
                >
                  Create Route
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      
      {/* Edit Route Modal */}
      {isEditModalOpen && editingRoute && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="flex justify-between items-center p-6 border-b border-gray-100">
              <h2 className="text-xl font-bold text-gray-900">Edit Route</h2>
              <button onClick={() => setIsEditModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleUpdateRoute} className="p-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Route Name</label>
                  <input
                    type="text"
                    required
                    value={editRouteName}
                    onChange={(e) => setEditRouteName(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>
              </div>
              <div className="mt-8 flex gap-3">
                <button
                  type="button"
                  onClick={() => setIsEditModalOpen(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Manage Stops Modal */}
      {isManageStopsOpen && selectedRoute && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl h-[85vh] flex flex-col overflow-hidden">
            <div className="flex justify-between items-center p-6 border-b border-gray-100 shrink-0">
              <div>
                <h2 className="text-xl font-bold text-gray-900">{selectedRoute.name}</h2>
                <p className="text-sm text-gray-500">Code: {selectedRoute.code}</p>
              </div>
              <button onClick={() => setIsManageStopsOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="flex flex-1 overflow-hidden">
              {/* Left Panel: Stops Management */}
              <div className="w-1/2 flex flex-col border-r border-gray-200">
                <div className="p-4 border-b border-gray-100 shrink-0">
                  <div className="flex bg-gray-100 rounded-lg p-1 mb-4">
                    <button
                      className={`flex-1 py-1.5 text-sm font-medium rounded-md ${selectedDirection === 'MORNING' ? 'bg-white shadow text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
                      onClick={() => setSelectedDirection('MORNING')}
                    >
                      MORNING
                    </button>
                    <button
                      className={`flex-1 py-1.5 text-sm font-medium rounded-md ${selectedDirection === 'EVENING' ? 'bg-white shadow text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
                      onClick={() => setSelectedDirection('EVENING')}
                    >
                      EVENING
                    </button>
                  </div>
                  
                  <div className="flex gap-2">
                    <select
                      value={newStopId}
                      onChange={(e) => setNewStopId(e.target.value ? Number(e.target.value) : '')}
                      className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                    >
                      <option value="">Select Boarding Point...</option>
                      {stops.filter(s => !selectedRoute.stops.find(rs => rs.direction === selectedDirection && rs.boarding_point_id === s.id)).map(stop => (
                        <option key={stop.id} value={stop.id}>{stop.name}</option>
                      ))}
                    </select>
                    <button
                      onClick={handleAddStop}
                      disabled={!newStopId}
                      className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg disabled:opacity-50"
                    >
                      Add
                    </button>
                  </div>
                </div>
                
                <div className="flex-1 overflow-y-auto p-4">
                  {(() => {
                    const dirStops = [...selectedRoute.stops]
                      .filter(s => s.direction === selectedDirection)
                      .sort((a, b) => a.sequence_order - b.sequence_order);

                    if (dirStops.length === 0) {
                      return (
                        <div className="text-center py-10 text-gray-500">
                          No stops configured for this direction.
                        </div>
                      );
                    }

                    return (
                      <div className="space-y-2">
                        {dirStops.map((stop, index) => (
                          <div key={stop.id} className="flex items-center bg-white border border-gray-200 p-3 rounded-lg shadow-sm">
                            <div className="flex flex-col gap-1 mr-3 shrink-0">
                              <button 
                                onClick={() => handleReorder(index, 'up')} 
                                disabled={index === 0}
                                className="text-gray-400 hover:text-gray-700 disabled:opacity-30"
                              >
                                <ChevronUp className="w-4 h-4" />
                              </button>
                              <button 
                                onClick={() => handleReorder(index, 'down')}
                                disabled={index === dirStops.length - 1}
                                className="text-gray-400 hover:text-gray-700 disabled:opacity-30"
                              >
                                <ChevronDown className="w-4 h-4" />
                              </button>
                            </div>
                            
                            <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold mr-3 shrink-0">
                              {index + 1}
                            </div>
                            
                            <div className="flex-1 min-w-0">
                              <h3 className="font-medium text-gray-900 truncate">{stop.boarding_point.name}</h3>
                              {stop.boarding_point.latitude !== 0 && (
                                <p className="text-xs text-gray-500 truncate flex items-center">
                                  <MapPin className="w-3 h-3 mr-1" />
                                  {stop.boarding_point.latitude.toFixed(4)}, {stop.boarding_point.longitude.toFixed(4)}
                                </p>
                              )}
                            </div>
                            
                            <button
                              onClick={() => handleRemoveStop(stop.id)}
                              className="p-2 text-red-500 hover:bg-red-50 rounded-lg ml-2 shrink-0 transition"
                              title="Remove Stop"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    );
                  })()}
                </div>
              </div>
              
              {/* Right Panel: Route Map Preview Placeholder */}
              <div className="w-1/2 bg-gray-50 flex flex-col items-center justify-center relative overflow-hidden">
                <div className="absolute inset-0 opacity-10" style={{
                  backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%23000000\' fill-opacity=\'1\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")'
                }} />
                
                <MapPin className="w-12 h-12 text-gray-300 mb-4" />
                <h3 className="text-lg font-medium text-gray-700">Map Preview Unavailable</h3>
                <p className="text-sm text-gray-500 max-w-xs text-center mt-2">
                  Interactive MapLibre preview will be rendered here.
                  Only stops with valid configured coordinates will be displayed.
                </p>
                
                {/* Fallback visual line summary */}
                <div className="mt-8 bg-white p-4 rounded-xl shadow-sm border border-gray-200 z-10 w-3/4 max-h-64 overflow-y-auto">
                  <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Sequence Map</h4>
                  {selectedRoute.stops
                      .filter(s => s.direction === selectedDirection)
                      .sort((a, b) => a.sequence_order - b.sequence_order)
                      .map((s, i, arr) => (
                        <div key={s.id} className="flex items-start">
                          <div className="flex flex-col items-center mr-3">
                            <div className="w-3 h-3 rounded-full bg-blue-500 mt-1" />
                            {i < arr.length - 1 && <div className="w-0.5 h-6 bg-gray-200 my-1" />}
                          </div>
                          <div className="pb-4">
                            <p className="text-sm font-medium text-gray-800">{s.boarding_point.name}</p>
                            {s.boarding_point.latitude === 0 && (
                               <p className="text-xs text-red-500">Location not configured</p>
                            )}
                          </div>
                        </div>
                  ))}
                  {selectedRoute.stops.filter(s => s.direction === selectedDirection).length === 0 && (
                    <p className="text-sm text-gray-500">No stops to visualize.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
