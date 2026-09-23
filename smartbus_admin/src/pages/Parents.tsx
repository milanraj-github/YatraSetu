import { useState, useEffect } from 'react';
import api from '../services/api';
import { useNavigate } from 'react-router-dom';
import { User, Eye, Mail, Clock } from 'lucide-react';

export default function Parents() {
  const [parents, setParents] = useState<any[]>([]);
  const [requests, setRequests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'parents' | 'requests'>('parents');
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [parentsRes, requestsRes] = await Promise.all([
        api.get('/admin/parents'),
        api.get('/admin/parents/requests/all')
      ]);
      if (parentsRes.data.success) {
        setParents(parentsRes.data.data.parents);
      }
      if (requestsRes.data.success) {
        setRequests(requestsRes.data.data.requests);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Parents Management</h1>
          <p className="text-slate-500">Manage parent accounts and pending registration requests</p>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden mb-6">
        <div className="border-b border-slate-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setActiveTab('parents')}
              className={`w-1/2 py-4 px-1 text-center border-b-2 font-medium text-sm ${
                activeTab === 'parents'
                  ? 'border-brand-500 text-brand-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              }`}
            >
              Registered Parents
            </button>
            <button
              onClick={() => setActiveTab('requests')}
              className={`w-1/2 py-4 px-1 text-center border-b-2 font-medium text-sm ${
                activeTab === 'requests'
                  ? 'border-brand-500 text-brand-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              }`}
            >
              Pending & Historical Requests
            </button>
          </nav>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-500">Loading data...</div>
        ) : activeTab === 'parents' ? (
          parents.length === 0 ? (
            <div className="p-12 text-center text-slate-500">No parents found in the system.</div>
          ) : (
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Parent</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Contact</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">Linked Students</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {parents.map((parent) => (
                  <tr key={parent.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="h-10 w-10 flex-shrink-0 bg-blue-100 rounded-full flex items-center justify-center text-blue-600">
                          <User className="h-5 w-5" />
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-slate-900">{parent.full_name}</div>
                          <div className="text-sm text-slate-500">ID: {parent.id}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-slate-900">{parent.email}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                        {parent.linked_students_count}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${parent.status === 'ACTIVE' ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-800'}`}>
                        {parent.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button 
                        onClick={() => navigate(`/parents/${parent.id}`)}
                        className="text-brand-600 hover:text-brand-900 bg-brand-50 p-2 rounded-lg"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        ) : (
          requests.length === 0 ? (
            <div className="p-12 text-center text-slate-500">No requests found.</div>
          ) : (
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Student Email</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Relationship</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Date Requested</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {requests.map((req) => (
                  <tr key={req.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <Mail className="h-4 w-4 text-slate-400 mr-2" />
                        <span className="text-sm font-medium text-slate-900">{req.student_email}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-slate-600">{req.relationship_type}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium 
                        ${req.status === 'PENDING' ? 'bg-yellow-100 text-yellow-800' : 
                          req.status === 'APPROVED' ? 'bg-green-100 text-green-800' : 
                          req.status === 'REJECTED' ? 'bg-red-100 text-red-800' : 'bg-slate-100 text-slate-800'}`}>
                        {req.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-slate-500">
                        <Clock className="h-4 w-4 mr-2" />
                        {new Date(req.created_at).toLocaleString()}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}
      </div>
    </div>
  );
}
