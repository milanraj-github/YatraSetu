import { useState, useEffect } from 'react';
import { analyticsService } from '../services/api';
import { BarChart3, TrendingUp, AlertTriangle, Siren, Bus, Route as RouteIcon, User, RefreshCw } from 'lucide-react';

export default function Analytics() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState('7'); // 'today', '7', '30'
  const [data, setData] = useState<any>(null);

  const fetchAnalytics = async (range: string) => {
    setLoading(true);
    setError(null);
    try {
      const end = new Date();
      const start = new Date();
      if (range === 'today') {
        // Today
      } else if (range === '7') {
        start.setDate(end.getDate() - 7);
      } else if (range === '30') {
        start.setDate(end.getDate() - 30);
      }
      
      const formatString = (d: Date) => {
        // Simple YYYY-MM-DD in local time
        const offset = d.getTimezoneOffset()
        d = new Date(d.getTime() - (offset*60*1000))
        return d.toISOString().split('T')[0]
      };

      const res = await analyticsService.getSummary(formatString(start), formatString(end));
      setData(res.data);
    } catch (err: any) {
      console.error(err);
      setError('Unable to load analytics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics(dateRange);
  }, [dateRange]);

  const SimpleBarChart = ({ trends, colorClass, title }: { trends: any[], colorClass: string, title: string }) => {
    if (!trends || trends.length === 0) return <div className="text-gray-400 italic py-4">No data available.</div>;
    const maxCount = Math.max(...trends.map(t => t.count), 1);
    
    return (
      <div className="w-full">
        <h4 className="text-xs font-bold text-gray-500 mb-4 uppercase tracking-wider">{title}</h4>
        <div className="flex items-end h-40 gap-2">
          {trends.map((t, idx) => (
            <div key={idx} className="flex-1 flex flex-col justify-end group relative h-full">
              <div 
                className={`w-full rounded-t-sm transition-all duration-300 ${colorClass}`} 
                style={{ height: `${(t.count / maxCount) * 100}%`, minHeight: t.count > 0 ? '4px' : '0' }}
              >
              </div>
              <div className="text-[10px] text-gray-400 mt-2 text-center truncate">{t.date.split('-').slice(1).join('/')}</div>
              {/* Tooltip */}
              <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white text-xs font-bold py-1 px-2 rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-10">
                {t.count} ({t.date})
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-10">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            <BarChart3 className="w-6 h-6 mr-2 text-blue-600" />
            Analytics
          </h1>
          <p className="text-sm text-gray-500">Monitor transport operations, trip performance, GPS activity and safety events.</p>
        </div>
        <div className="flex items-center gap-3">
          <select 
            value={dateRange} 
            onChange={(e) => setDateRange(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm font-medium text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="today">Today</option>
            <option value="7">Last 7 Days</option>
            <option value="30">Last 30 Days</option>
          </select>
          <button 
            onClick={() => fetchAnalytics(dateRange)} 
            disabled={loading}
            className="flex items-center px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg flex items-center shadow-sm border border-red-100">
          <AlertTriangle className="w-5 h-5 mr-2" />
          {error}
        </div>
      )}

      {loading && !data && (
        <div className="py-20 text-center flex flex-col items-center">
          <RefreshCw className="w-8 h-8 text-blue-500 animate-spin mb-4" />
          <p className="text-gray-500 font-medium">Loading analytics...</p>
        </div>
      )}

      {data && !loading && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
            <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col">
              <span className="text-xs font-bold text-gray-500 mb-1">TOTAL TRIPS</span>
              <span className="text-2xl font-bold text-gray-900">{data.trips.total}</span>
            </div>
            <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col">
              <span className="text-xs font-bold text-green-600 mb-1">COMPLETED</span>
              <span className="text-2xl font-bold text-green-700">{data.trips.completed}</span>
            </div>
            <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col">
              <span className="text-xs font-bold text-gray-500 mb-1">CANCELLED</span>
              <span className="text-2xl font-bold text-gray-700">{data.trips.cancelled}</span>
            </div>
            <div className="bg-white p-4 rounded-xl border border-blue-200 bg-blue-50 shadow-sm flex flex-col">
              <span className="text-xs font-bold text-blue-700 mb-1">ACTIVE</span>
              <span className="text-2xl font-bold text-blue-800">{data.trips.active}</span>
            </div>
            <div className="bg-white p-4 rounded-xl border border-orange-200 bg-orange-50 shadow-sm flex flex-col">
              <span className="text-xs font-bold text-orange-700 mb-1">ALERTS</span>
              <span className="text-2xl font-bold text-orange-800">{data.alerts.total}</span>
            </div>
            <div className="bg-white p-4 rounded-xl border border-red-200 bg-red-50 shadow-sm flex flex-col">
              <span className="text-xs font-bold text-red-700 mb-1">EMERGENCIES</span>
              <span className="text-2xl font-bold text-red-800">{data.emergencies.total}</span>
            </div>
          </div>

          {/* Trends Row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
              <div className="flex items-center mb-6">
                <TrendingUp className="w-5 h-5 text-blue-500 mr-2" />
                <h3 className="font-bold text-gray-900">Trip Activity Trend</h3>
              </div>
              <SimpleBarChart trends={data.trips.trend} colorClass="bg-blue-500 group-hover:bg-blue-600" title="Trips by Date" />
            </div>
            
            <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
              <div className="flex items-center mb-6">
                <AlertTriangle className="w-5 h-5 text-orange-500 mr-2" />
                <h3 className="font-bold text-gray-900">Alert Trend</h3>
              </div>
              <SimpleBarChart trends={data.alerts.trend} colorClass="bg-orange-400 group-hover:bg-orange-500" title="Alerts by Date" />
            </div>

            <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
              <div className="flex items-center mb-6">
                <Siren className="w-5 h-5 text-red-500 mr-2" />
                <h3 className="font-bold text-gray-900">Emergency Trend</h3>
              </div>
              <SimpleBarChart trends={data.emergencies.trend} colorClass="bg-red-500 group-hover:bg-red-600" title="Emergencies by Date" />
            </div>
          </div>

          {/* Safety & Alerts Overview */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex items-center">
                <AlertTriangle className="w-5 h-5 text-gray-500 mr-2" />
                <h3 className="font-bold text-gray-900">Alert Overview</h3>
              </div>
              <div className="p-6 grid grid-cols-2 gap-4">
                <div className="space-y-4">
                  <div>
                    <div className="text-xs font-bold text-gray-500 mb-1">ACTIVE ALERTS</div>
                    <div className="text-xl font-bold text-red-600">{data.alerts.active}</div>
                  </div>
                  <div>
                    <div className="text-xs font-bold text-gray-500 mb-1">RESOLVED</div>
                    <div className="text-xl font-bold text-green-600">{data.alerts.resolved}</div>
                  </div>
                </div>
                <div>
                   <div className="text-xs font-bold text-gray-500 mb-3">BREAKDOWN BY TYPE</div>
                   {Object.entries(data.alerts.by_type || {}).length === 0 ? (
                     <div className="text-sm text-gray-400 italic">No alerts recorded.</div>
                   ) : (
                     <div className="space-y-2">
                       {Object.entries(data.alerts.by_type).map(([k, v]: any) => (
                         <div key={k} className="flex justify-between items-center text-sm">
                           <span className="font-medium text-gray-700">{k}</span>
                           <span className="font-bold bg-gray-100 px-2 py-0.5 rounded">{v}</span>
                         </div>
                       ))}
                     </div>
                   )}
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex items-center">
                <Siren className="w-5 h-5 text-red-500 mr-2" />
                <h3 className="font-bold text-gray-900">Emergency Overview</h3>
              </div>
              <div className="p-6 grid grid-cols-2 gap-4">
                <div className="space-y-4">
                  <div>
                    <div className="text-xs font-bold text-gray-500 mb-1">ACTIVE / ACKNOWLEDGED</div>
                    <div className="text-xl font-bold text-red-600">{data.emergencies.active} / <span className="text-orange-600">{data.emergencies.acknowledged}</span></div>
                  </div>
                  <div>
                    <div className="text-xs font-bold text-gray-500 mb-1">RESOLVED</div>
                    <div className="text-xl font-bold text-green-600">{data.emergencies.resolved}</div>
                  </div>
                </div>
                <div>
                   <div className="text-xs font-bold text-gray-500 mb-3">BREAKDOWN BY TYPE</div>
                   {Object.entries(data.emergencies.by_type || {}).length === 0 ? (
                     <div className="text-sm text-gray-400 italic">No emergencies recorded.</div>
                   ) : (
                     <div className="space-y-2">
                       {Object.entries(data.emergencies.by_type).map(([k, v]: any) => (
                         <div key={k} className="flex justify-between items-center text-sm">
                           <span className="font-medium text-gray-700">{k.replace('_', ' ')}</span>
                           <span className="font-bold bg-red-100 text-red-700 px-2 py-0.5 rounded">{v}</span>
                         </div>
                       ))}
                     </div>
                   )}
                </div>
              </div>
            </div>
          </div>

          {/* Tables Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            {/* Bus Utilization */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden flex flex-col">
              <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex items-center">
                <Bus className="w-5 h-5 text-gray-500 mr-2" />
                <h3 className="font-bold text-gray-900">Bus Utilization</h3>
              </div>
              <div className="overflow-x-auto flex-1">
                {data.buses.length === 0 ? (
                  <div className="p-8 text-center text-gray-400 italic text-sm">No bus activity recorded.</div>
                ) : (
                  <table className="w-full text-left text-sm text-gray-600">
                    <thead className="bg-white border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wider">
                      <tr>
                        <th className="px-6 py-3 font-bold">Bus</th>
                        <th className="px-6 py-3 font-bold text-right">Trips</th>
                        <th className="px-6 py-3 font-bold text-right text-green-600">Done</th>
                        <th className="px-6 py-3 font-bold text-right text-red-500">Canc</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {data.buses.map((b: any) => (
                        <tr key={b.bus_id} className="hover:bg-gray-50">
                          <td className="px-6 py-3 font-bold text-gray-900">{b.bus_number}</td>
                          <td className="px-6 py-3 font-bold text-right">{b.trips}</td>
                          <td className="px-6 py-3 font-medium text-right text-green-700">{b.completed}</td>
                          <td className="px-6 py-3 font-medium text-right text-red-600">{b.cancelled}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            {/* Route Performance */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden flex flex-col">
              <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex items-center">
                <RouteIcon className="w-5 h-5 text-gray-500 mr-2" />
                <h3 className="font-bold text-gray-900">Route Performance</h3>
              </div>
              <div className="overflow-x-auto flex-1">
                {data.routes.length === 0 ? (
                  <div className="p-8 text-center text-gray-400 italic text-sm">No route activity recorded.</div>
                ) : (
                  <table className="w-full text-left text-sm text-gray-600">
                    <thead className="bg-white border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wider">
                      <tr>
                        <th className="px-6 py-3 font-bold">Route</th>
                        <th className="px-6 py-3 font-bold text-right">Trips</th>
                        <th className="px-6 py-3 font-bold text-right text-orange-500">Alerts</th>
                        <th className="px-6 py-3 font-bold text-right text-red-600">Emg</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {data.routes.map((r: any) => (
                        <tr key={r.route_id} className="hover:bg-gray-50">
                          <td className="px-6 py-3 font-bold text-gray-900 truncate max-w-[150px]">{r.route_name}</td>
                          <td className="px-6 py-3 font-bold text-right">{r.trips}</td>
                          <td className="px-6 py-3 font-medium text-right text-orange-600">{r.alerts}</td>
                          <td className="px-6 py-3 font-medium text-right text-red-600">{r.emergencies}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

          </div>
          
          {/* Driver Operations */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden mt-6">
            <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex items-center">
              <User className="w-5 h-5 text-gray-500 mr-2" />
              <h3 className="font-bold text-gray-900">Driver Operations</h3>
            </div>
            <div className="overflow-x-auto">
              {data.drivers.length === 0 ? (
                <div className="p-8 text-center text-gray-400 italic text-sm">No driver activity recorded.</div>
              ) : (
                <table className="w-full text-left text-sm text-gray-600">
                  <thead className="bg-white border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wider">
                    <tr>
                      <th className="px-6 py-3 font-bold">Driver Name</th>
                      <th className="px-6 py-3 font-bold text-right">Total Trips</th>
                      <th className="px-6 py-3 font-bold text-right">Completed</th>
                      <th className="px-6 py-3 font-bold text-right text-red-600">Emergencies</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.drivers.map((d: any) => (
                      <tr key={d.driver_id} className="hover:bg-gray-50">
                        <td className="px-6 py-3 font-bold text-gray-900">{d.driver_name}</td>
                        <td className="px-6 py-3 font-medium text-right">{d.trips}</td>
                        <td className="px-6 py-3 font-medium text-right text-green-700">{d.completed}</td>
                        <td className="px-6 py-3 font-medium text-right text-red-600">{d.emergencies}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
