import React, { useState, useEffect, useRef } from 'react';
import { boardingPointService } from '../services/api';
import { AlertCircle, MapPin, Plus, Search, X, Edit, Trash2 } from 'lucide-react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

interface BoardingPoint {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  radius_meters: number;
}

export default function Stops() {
  const [stops, setStops] = useState<BoardingPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  // Modals
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [editingStop, setEditingStop] = useState<BoardingPoint | null>(null);

  // Form State
  const [name, setName] = useState('');
  const [latitude, setLatitude] = useState<string>('');
  const [longitude, setLongitude] = useState<string>('');
  const [radius, setRadius] = useState<number>(100);

  // Map elements
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<maplibregl.Map | null>(null);
  const markerInstance = useRef<maplibregl.Marker | null>(null);

  // View Map Elements
  const viewMapContainer = useRef<HTMLDivElement>(null);
  const viewMapInstance = useRef<maplibregl.Map | null>(null);
  const viewMarkerInstance = useRef<maplibregl.Marker | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await boardingPointService.getAll();
      setStops(res.data || []);
      setError(null);
    } catch (err: any) {
      setError('Failed to load boarding points.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const openAddModal = () => {
    setEditingStop(null);
    setName('');
    setLatitude('');
    setLongitude('');
    setRadius(100);
    setIsModalOpen(true);
  };

  const openEditModal = (stop: BoardingPoint) => {
    setEditingStop(stop);
    setName(stop.name);
    setLatitude(stop.latitude === 0.0 ? '' : stop.latitude.toString());
    setLongitude(stop.longitude === 0.0 ? '' : stop.longitude.toString());
    setRadius(stop.radius_meters);
    setIsModalOpen(true);
  };

  const openViewModal = (stop: BoardingPoint) => {
    setEditingStop(stop);
    setIsViewModalOpen(true);
  };

  // Initialize Edit/Create Map
  useEffect(() => {
    if (isModalOpen && mapContainer.current) {
      const initLat = parseFloat(latitude) || 13.3409;
      const initLng = parseFloat(longitude) || 74.7421;
      const hasCoords = latitude !== '' && longitude !== '';

      const map = new maplibregl.Map({
        container: mapContainer.current,
        style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
        center: [initLng, initLat],
        zoom: hasCoords ? 14 : 9
      });
      mapInstance.current = map;

      if (hasCoords) {
        markerInstance.current = new maplibregl.Marker({ color: '#2563eb' })
          .setLngLat([initLng, initLat])
          .addTo(map);
      }

      map.on('click', (e: any) => {
        const lng = e.lngLat.lng;
        const lat = e.lngLat.lat;
        setLatitude(lat.toFixed(6));
        setLongitude(lng.toFixed(6));

        if (!markerInstance.current) {
          markerInstance.current = new maplibregl.Marker({ color: '#2563eb' })
            .setLngLat([lng, lat])
            .addTo(map);
        } else {
          markerInstance.current.setLngLat([lng, lat]);
        }
      });

      return () => {
        map.remove();
        mapInstance.current = null;
        markerInstance.current = null;
      };
    }
  }, [isModalOpen]);

  // Initialize View Map
  useEffect(() => {
    if (isViewModalOpen && viewMapContainer.current && editingStop) {
      const hasCoords = editingStop.latitude !== 0.0 && editingStop.longitude !== 0.0;
      
      if (!hasCoords) return;

      const map = new maplibregl.Map({
        container: viewMapContainer.current,
        style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
        center: [editingStop.longitude, editingStop.latitude],
        zoom: 15
      });
      viewMapInstance.current = map;

      viewMarkerInstance.current = new maplibregl.Marker({ color: '#2563eb' })
        .setLngLat([editingStop.longitude, editingStop.latitude])
        .addTo(map);

      return () => {
        map.remove();
        viewMapInstance.current = null;
        viewMarkerInstance.current = null;
      };
    }
  }, [isViewModalOpen, editingStop]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name) return;

    // Default to 0.0 if left blank (Not configured)
    const payload = {
      name,
      latitude: latitude ? parseFloat(latitude) : 0.0,
      longitude: longitude ? parseFloat(longitude) : 0.0,
      radius_meters: radius
    };

    if (payload.latitude < -90 || payload.latitude > 90 || payload.longitude < -180 || payload.longitude > 180) {
      alert("Invalid coordinates.");
      return;
    }

    try {
      if (editingStop) {
        await boardingPointService.update(editingStop.id, payload);
      } else {
        await boardingPointService.create(payload);
      }
      setIsModalOpen(false);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail?.message || 'Unable to save boarding point');
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to deactivate/delete this boarding point? Warning: Because the backend has CASCADE rules, deleting this will completely remove it from all assigned routes and history.')) return;
    try {
      await boardingPointService.delete(id);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail?.message || 'Failed to delete boarding point');
    }
  };

  const filteredStops = stops.filter(s => 
    s.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Boarding Points</h1>
          <p className="text-sm text-gray-500">Manage verified bus boarding locations.</p>
        </div>
        <button
          onClick={openAddModal}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition flex items-center"
        >
          <Plus className="w-5 h-5 mr-1" />
          Add Boarding Point
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
            placeholder="Search boarding points..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Loading boarding points...</div>
        ) : filteredStops.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-500 mb-4">No boarding points configured.</p>
            <button onClick={openAddModal} className="text-blue-600 font-medium hover:underline">
              + Add Boarding Point
            </button>
          </div>
        ) : (
          <table className="w-full text-left text-sm text-gray-600">
            <thead className="bg-gray-50 border-b border-gray-200 text-gray-700">
              <tr>
                <th className="px-6 py-4 font-medium">Name</th>
                <th className="px-6 py-4 font-medium">Coordinates</th>
                <th className="px-6 py-4 font-medium">Radius</th>
                <th className="px-6 py-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredStops.map((stop) => {
                const hasCoords = stop.latitude !== 0.0 || stop.longitude !== 0.0;
                return (
                  <tr key={stop.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 font-medium text-gray-900">{stop.name}</td>
                    <td className="px-6 py-4">
                      {hasCoords ? (
                        <span className="flex items-center text-gray-600">
                          <MapPin className="w-4 h-4 mr-1 text-gray-400" />
                          {stop.latitude.toFixed(6)}, {stop.longitude.toFixed(6)}
                        </span>
                      ) : (
                        <span className="text-orange-500 text-xs font-medium bg-orange-50 px-2 py-1 rounded">Coordinates not configured</span>
                      )}
                    </td>
                    <td className="px-6 py-4">{stop.radius_meters} m</td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => openViewModal(stop)}
                        className="text-gray-500 hover:text-blue-600 font-medium mr-4"
                        title="View"
                      >
                        <Search className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => openEditModal(stop)}
                        className="text-gray-500 hover:text-blue-600 font-medium mr-4"
                        title="Edit"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(stop.id)}
                        className="text-red-500 hover:text-red-700 font-medium"
                        title="Deactivate / Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Add / Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl overflow-hidden flex flex-col md:flex-row h-[70vh]">
            <div className="w-full md:w-1/2 p-6 overflow-y-auto flex flex-col border-r border-gray-100">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold text-gray-900">{editingStop ? 'Edit' : 'Add'} Boarding Point</h2>
                <button onClick={() => setIsModalOpen(false)} className="text-gray-400 hover:text-gray-600 md:hidden">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleSubmit} className="flex-1 flex flex-col">
                <div className="space-y-4 flex-1">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                    <input
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                      placeholder="e.g. Santhakatte"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Latitude</label>
                      <input
                        type="number"
                        step="0.000001"
                        min="-90" max="90"
                        value={latitude}
                        onChange={(e) => setLatitude(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                        placeholder="Optional"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Longitude</label>
                      <input
                        type="number"
                        step="0.000001"
                        min="-180" max="180"
                        value={longitude}
                        onChange={(e) => setLongitude(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                        placeholder="Optional"
                      />
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Leave coordinates blank if location is unknown. Click on the map to set them automatically.</p>
                  
                  <div className="pt-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Geofence Radius (meters)</label>
                    <input
                      type="number"
                      required
                      min="10" max="1000"
                      value={radius}
                      onChange={(e) => setRadius(Number(e.target.value))}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                  </div>
                </div>
                <div className="mt-8 flex gap-3">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700"
                  >
                    {editingStop ? 'Save Changes' : 'Create'}
                  </button>
                </div>
              </form>
            </div>
            
            <div className="w-full md:w-1/2 bg-gray-100 relative">
              <div className="absolute top-4 right-4 z-10 hidden md:block">
                <button onClick={() => setIsModalOpen(false)} className="bg-white p-2 rounded-full shadow-md text-gray-500 hover:text-gray-800">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div ref={mapContainer} className="w-full h-full" />
              <div className="absolute bottom-4 left-4 right-4 md:right-auto bg-white/90 backdrop-blur px-3 py-2 rounded shadow text-xs font-medium text-gray-700 pointer-events-none text-center">
                Click anywhere on the map to set coordinates
              </div>
            </div>
          </div>
        </div>
      )}

      {/* View Modal */}
      {isViewModalOpen && editingStop && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="flex justify-between items-center p-6 border-b border-gray-100">
              <h2 className="text-xl font-bold text-gray-900">{editingStop.name}</h2>
              <button onClick={() => setIsViewModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6">
              <div className="space-y-4 mb-6">
                <div>
                  <div className="text-sm text-gray-500 mb-1">Status</div>
                  <div className="font-medium text-green-700">ACTIVE</div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-gray-500 mb-1">Geofence Radius</div>
                    <div className="font-medium">{editingStop.radius_meters} m</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500 mb-1">Coordinates</div>
                    <div className="font-medium text-sm">
                      {(editingStop.latitude !== 0.0 && editingStop.longitude !== 0.0) 
                        ? `${editingStop.latitude.toFixed(5)}, ${editingStop.longitude.toFixed(5)}`
                        : 'Not configured'}
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-xl overflow-hidden border border-gray-200 h-64 relative bg-gray-50 flex items-center justify-center">
                {(editingStop.latitude !== 0.0 && editingStop.longitude !== 0.0) ? (
                  <div ref={viewMapContainer} className="w-full h-full" />
                ) : (
                  <div className="text-center p-6">
                    <MapPin className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                    <p className="text-gray-500 font-medium">Location not configured.</p>
                    <p className="text-xs text-gray-400 mt-1">Edit this boarding point to set its coordinates on the map.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
