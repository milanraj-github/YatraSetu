import { useState, useEffect, useRef } from 'react';
import { trackingService } from '../services/api';
import { AlertCircle, Clock, Map as MapIcon, Search, Truck, User } from 'lucide-react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

interface LocationPoint {
  latitude: number;
  longitude: number;
  speed: number;
  heading: number;
  accuracy: number;
  recorded_at: string;
}

interface ActiveBus {
  trip_id: number;
  bus_id: number;
  route_id: number | null;
  route_name: string | null;
  bus_number: string;
  registration_number: string;
  status: string;
  direction: string;
  driver_name: string;
  location_status: string;
  location: LocationPoint | null;
}

export default function LiveMap() {
  const [buses, setBuses] = useState<ActiveBus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());
  
  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [selectedBusId, setSelectedBusId] = useState<number | null>(null);

  // Map state
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<{ [key: number]: maplibregl.Marker }>({});
  const popupRef = useRef<maplibregl.Popup | null>(null);

  const STALE_THRESHOLD_SECONDS = 45;

  const fetchData = async (isInitial = false) => {
    try {
      const res = await trackingService.getActiveBuses();
      const fetchedBuses = res.data || [];
      setBuses(fetchedBuses);
      setLastRefreshed(new Date());
      setError(null);
      
      if (isInitial && fetchedBuses.length > 0 && mapInstance.current) {
        fitBoundsToBuses(fetchedBuses, mapInstance.current);
      }
    } catch (err: any) {
      console.error(err);
      setError('Live connection lost. Reconnecting...');
    } finally {
      if (isInitial) setLoading(false);
    }
  };

  // Initial Data & Polling
  useEffect(() => {
    fetchData(true);
    const interval = setInterval(() => {
      fetchData(false);
    }, 5000); // 5 sec poll
    
    return () => clearInterval(interval);
  }, []);

  // Initialize Map
  useEffect(() => {
    if (!mapContainer.current) return;
    
    if (!mapInstance.current) {
      const map = new maplibregl.Map({
        container: mapContainer.current,
        style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
        center: [74.7421, 13.3409], // Default fallback
        zoom: 10
      });
      
      map.addControl(new maplibregl.NavigationControl(), 'top-right');
      
      popupRef.current = new maplibregl.Popup({
        closeButton: true,
        closeOnClick: false,
        offset: 25,
        maxWidth: '300px'
      });
      
      mapInstance.current = map;
    }
    
    return () => {
      // Map cleanup occurs on full unmount
    };
  }, []);

  // Sync Markers when buses update
  useEffect(() => {
    if (!mapInstance.current) return;
    const map = mapInstance.current;
    
    // Track which buses are still active to remove stale markers
    const currentBusIds = new Set<number>();
    
    buses.forEach(bus => {
      if (!bus.location) return; // Skip if no GPS
      
      currentBusIds.add(bus.bus_id);
      
      const { longitude, latitude, recorded_at } = bus.location;
      const ageSeconds = getAgeSeconds(recorded_at);
      const isStale = ageSeconds > STALE_THRESHOLD_SECONDS;
      
      // Update or Create Marker
      let marker = markersRef.current[bus.bus_id];
      
      if (!marker) {
        // Create custom HTML element for marker
        const el = document.createElement('div');
        el.className = 'w-10 h-10 flex items-center justify-center';
        el.innerHTML = `
          <div class="relative w-8 h-8 flex items-center justify-center rounded-full shadow-lg border-2 ${isStale ? 'bg-orange-100 border-orange-500 text-orange-700' : 'bg-blue-600 border-white text-white'} transition-colors duration-300">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 16H9m10 0h3v-3.15a1 1 0 0 0-.84-.99L16 11l-2.7-3.6a2 2 0 0 0-1.6-.8H5a2 2 0 0 0-2 2v7h2M14 16a2 2 0 1 0-4 0m12 0a2 2 0 1 0-4 0M3 16a2 2 0 1 0-4 0m5-5h.01"/></svg>
            ${!isStale ? `<div class="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white animate-pulse"></div>` : ''}
          </div>
        `;
        
        el.addEventListener('click', () => {
          setSelectedBusId(bus.bus_id);
          showPopup(bus, map);
        });
        
        marker = new maplibregl.Marker({ element: el })
          .setLngLat([longitude, latitude])
          .addTo(map);
          
        markersRef.current[bus.bus_id] = marker;
      } else {
        // Smoothly animate to new location
        marker.setLngLat([longitude, latitude]);
        
        // Update DOM element classes if staleness changed
        const innerDiv = marker.getElement().firstElementChild as HTMLElement;
        if (innerDiv) {
          if (isStale) {
            innerDiv.className = "relative w-8 h-8 flex items-center justify-center rounded-full shadow-lg border-2 bg-orange-100 border-orange-500 text-orange-700 transition-colors duration-300";
            innerDiv.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 16H9m10 0h3v-3.15a1 1 0 0 0-.84-.99L16 11l-2.7-3.6a2 2 0 0 0-1.6-.8H5a2 2 0 0 0-2 2v7h2M14 16a2 2 0 1 0-4 0m12 0a2 2 0 1 0-4 0M3 16a2 2 0 1 0-4 0m5-5h.01"/></svg>`;
          } else {
            innerDiv.className = "relative w-8 h-8 flex items-center justify-center rounded-full shadow-lg border-2 bg-blue-600 border-white text-white transition-colors duration-300";
            innerDiv.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 16H9m10 0h3v-3.15a1 1 0 0 0-.84-.99L16 11l-2.7-3.6a2 2 0 0 0-1.6-.8H5a2 2 0 0 0-2 2v7h2M14 16a2 2 0 1 0-4 0m12 0a2 2 0 1 0-4 0M3 16a2 2 0 1 0-4 0m5-5h.01"/></svg><div class="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white animate-pulse"></div>`;
          }
        }
      }
      
      // If this bus is currently selected, update its popup content implicitly by re-calling showPopup
      if (selectedBusId === bus.bus_id && popupRef.current?.isOpen()) {
        showPopup(bus, map, false); // false = don't pan map if already open
      }
    });
    
    // Remove markers for buses no longer active
    Object.keys(markersRef.current).forEach(key => {
      const id = Number(key);
      if (!currentBusIds.has(id)) {
        markersRef.current[id].remove();
        delete markersRef.current[id];
      }
    });
    
  }, [buses]);

  // Handle bus selection from sidebar
  useEffect(() => {
    if (selectedBusId && mapInstance.current) {
      const bus = buses.find(b => b.bus_id === selectedBusId);
      if (bus) {
        showPopup(bus, mapInstance.current, true); // true = pan map to bus
      }
    } else {
      if (popupRef.current?.isOpen()) {
        popupRef.current.remove();
      }
    }
  }, [selectedBusId]);

  const fitBoundsToBuses = (activeBuses: ActiveBus[], map: maplibregl.Map) => {
    const validBuses = activeBuses.filter(b => b.location);
    if (validBuses.length === 0) return;
    
    const bounds = new maplibregl.LngLatBounds();
    validBuses.forEach(b => {
      bounds.extend([b.location!.longitude, b.location!.latitude]);
    });
    
    map.fitBounds(bounds, { padding: 50, maxZoom: 15, duration: 1000 });
  };

  const showPopup = (bus: ActiveBus, map: maplibregl.Map, panTo = false) => {
    if (!bus.location || !popupRef.current) return;
    
    const ageSeconds = getAgeSeconds(bus.location.recorded_at);
    const isStale = ageSeconds > STALE_THRESHOLD_SECONDS;
    const speed = Math.round(bus.location.speed);
    
    const htmlContent = `
      <div class="p-1">
        <div class="flex items-center justify-between mb-2 pb-2 border-b border-gray-100">
          <div class="font-bold text-gray-900">${bus.bus_number}</div>
          <div class="text-[10px] font-bold px-1.5 py-0.5 rounded ${isStale ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700'}">
            ${isStale ? 'STALE' : 'LIVE'}
          </div>
        </div>
        <div class="space-y-1.5 text-xs text-gray-600 mb-3">
          <div class="flex items-start"><span class="w-16 font-medium text-gray-400">Driver:</span> <span class="flex-1 font-medium text-gray-800">${bus.driver_name}</span></div>
          <div class="flex items-start"><span class="w-16 font-medium text-gray-400">Route:</span> <span class="flex-1">${bus.route_name || 'Unknown'}</span></div>
          <div class="flex items-start"><span class="w-16 font-medium text-gray-400">Dir:</span> <span class="flex-1">${bus.direction}</span></div>
        </div>
        <div class="grid grid-cols-2 gap-2 mb-2">
          <div class="bg-gray-50 rounded p-1.5 text-center">
            <div class="text-[10px] text-gray-400 uppercase">Speed</div>
            <div class="font-bold text-gray-900">${speed} <span class="text-[10px] font-normal text-gray-500">km/h</span></div>
          </div>
          <div class="bg-gray-50 rounded p-1.5 text-center">
            <div class="text-[10px] text-gray-400 uppercase">Accuracy</div>
            <div class="font-bold text-gray-900">${Math.round(bus.location.accuracy)} <span class="text-[10px] font-normal text-gray-500">m</span></div>
          </div>
        </div>
        <div class="text-[10px] text-gray-400 text-center mt-2">
          Last updated: ${ageSeconds < 5 ? 'Just now' : `${ageSeconds} sec ago`}
        </div>
      </div>
    `;

    popupRef.current.setLngLat([bus.location.longitude, bus.location.latitude])
      .setHTML(htmlContent)
      .addTo(map);
      
    if (panTo) {
      map.flyTo({ center: [bus.location.longitude, bus.location.latitude], zoom: 15, duration: 1000 });
    }
  };

  const getAgeSeconds = (recordedAt: string) => {
    return Math.floor((new Date().getTime() - new Date(recordedAt).getTime()) / 1000);
  };

  // Helper mappings for filtering
  const augmentedBuses = buses.map(bus => {
    const isStale = bus.location ? getAgeSeconds(bus.location.recorded_at) > STALE_THRESHOLD_SECONDS : true;
    return { ...bus, isStale };
  });

  const filteredBuses = augmentedBuses.filter(bus => {
    const searchLower = searchTerm.toLowerCase();
    const matchesSearch = 
      bus.bus_number.toLowerCase().includes(searchLower) ||
      bus.driver_name.toLowerCase().includes(searchLower) ||
      (bus.route_name && bus.route_name.toLowerCase().includes(searchLower));

    const matchesStatus = filterStatus === 'ALL' 
      ? true 
      : filterStatus === 'LIVE' ? !bus.isStale && bus.location : bus.isStale || !bus.location;
      
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] -mx-6 -my-6 bg-gray-50">
      {/* Top Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between z-10 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center">
            <MapIcon className="w-5 h-5 mr-2 text-blue-600" />
            Live Map
          </h1>
          <p className="text-sm text-gray-500 flex items-center mt-0.5">
            Monitor active buses in real time.
          </p>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex items-center text-sm font-medium">
            {error ? (
              <span className="flex items-center text-red-600 bg-red-50 px-3 py-1.5 rounded-full">
                <span className="w-2 h-2 rounded-full bg-red-600 mr-2"></span>
                {error}
              </span>
            ) : (
              <span className="flex items-center text-green-700 bg-green-50 px-3 py-1.5 rounded-full border border-green-200 shadow-sm">
                <span className="w-2 h-2 rounded-full bg-green-500 mr-2 animate-pulse"></span>
                LIVE TRACKING Connected
              </span>
            )}
          </div>
          <div className="text-xs text-gray-500">
            Last updated: {lastRefreshed.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })}
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden relative">
        {/* Left: Map */}
        <div className="flex-1 relative bg-gray-200 h-full">
          {loading && (
            <div className="absolute inset-0 z-20 flex items-center justify-center bg-white/70 backdrop-blur-sm">
              <div className="bg-white p-4 rounded-xl shadow-lg flex items-center font-medium text-blue-700 border border-blue-100">
                <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mr-3"></div>
                Loading live buses...
              </div>
            </div>
          )}
          
          <div ref={mapContainer} className="w-full h-full" />

          {buses.length === 0 && !loading && (
             <div className="absolute top-8 left-1/2 transform -translate-x-1/2 z-10 bg-white px-6 py-3 rounded-full shadow-lg border border-gray-200 font-medium text-gray-700 flex items-center">
               <AlertCircle className="w-5 h-5 text-gray-400 mr-2" />
               No buses are currently running.
             </div>
          )}
        </div>

        {/* Right: Sidebar */}
        <div className="w-96 bg-white border-l border-gray-200 flex flex-col h-full shadow-xl z-10 overflow-hidden">
          <div className="p-4 border-b border-gray-100 bg-gray-50">
            <h2 className="text-sm font-bold text-gray-900 uppercase tracking-wider mb-4 flex items-center justify-between">
              Active Buses
              <span className="bg-blue-100 text-blue-800 py-0.5 px-2 rounded-full text-xs">{filteredBuses.length}</span>
            </h2>
            
            <div className="space-y-3">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search bus, route, driver..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>
              
              <div className="flex gap-2">
                <select 
                  value={filterStatus} 
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="flex-1 text-sm border border-gray-300 rounded-lg px-2 py-1.5 focus:ring-2 focus:ring-blue-500 outline-none"
                >
                  <option value="ALL">All Status</option>
                  <option value="LIVE">Live GPS</option>
                  <option value="STALE">Stale/Missing GPS</option>
                </select>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-2">
            {filteredBuses.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <Truck className="w-8 h-8 mx-auto text-gray-300 mb-2" />
                <div className="text-sm">No buses match filters.</div>
              </div>
            ) : (
              <div className="space-y-2">
                {filteredBuses.map(bus => (
                  <div 
                    key={bus.bus_id}
                    onClick={() => setSelectedBusId(bus.bus_id)}
                    className={`p-3 rounded-lg border cursor-pointer transition-all ${selectedBusId === bus.bus_id ? 'border-blue-500 bg-blue-50 shadow-sm ring-1 ring-blue-500' : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'}`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div className="font-bold text-gray-900 flex items-center">
                        <Truck className={`w-4 h-4 mr-1.5 ${!bus.isStale && bus.location ? 'text-blue-600' : 'text-gray-400'}`} />
                        {bus.bus_number}
                      </div>
                      {bus.location ? (
                        <div className={`text-[10px] font-bold px-1.5 py-0.5 rounded flex items-center ${bus.isStale ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700'}`}>
                          {!bus.isStale && <span className="w-1.5 h-1.5 rounded-full bg-green-500 mr-1 animate-pulse"></span>}
                          {bus.isStale ? 'STALE' : 'LIVE'}
                        </div>
                      ) : (
                        <div className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">
                          NO GPS
                        </div>
                      )}
                    </div>
                    
                    <div className="text-xs text-gray-600 space-y-1.5">
                      <div className="truncate font-medium text-gray-800" title={bus.route_name || 'Unknown'}>
                        {bus.route_name || 'Unknown Route'}
                      </div>
                      <div className="flex items-center text-gray-500">
                        <User className="w-3.5 h-3.5 mr-1" />
                        <span className="truncate">{bus.driver_name}</span>
                      </div>
                      
                      <div className="flex items-center justify-between pt-2 mt-2 border-t border-gray-100/60">
                        <div className="text-gray-400 flex items-center">
                          <Clock className="w-3 h-3 mr-1" />
                          {bus.location ? (
                            getAgeSeconds(bus.location.recorded_at) < 5 ? 'Just now' : `${getAgeSeconds(bus.location.recorded_at)} sec ago`
                          ) : 'Never'}
                        </div>
                        {bus.location && !bus.isStale && (
                          <div className="font-medium text-gray-700 flex items-center bg-white px-1.5 rounded shadow-sm border border-gray-100">
                            {Math.round(bus.location.speed)} <span className="text-[9px] ml-0.5 text-gray-400">km/h</span>
                          </div>
                        )}
                      </div>
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
}
