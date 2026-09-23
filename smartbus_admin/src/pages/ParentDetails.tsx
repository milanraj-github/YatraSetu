import { useState, useEffect } from 'react';
import api from '../services/api';
import { useParams, useNavigate } from 'react-router-dom';
import { User, ArrowLeft, Shield, Mail, Calendar } from 'lucide-react';

export default function ParentDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDetails();
  }, [id]);

  const fetchDetails = async () => {
    try {
      setLoading(true);
      const res = await api.get(`/admin/parents/${id}`);
      if (res.data.success) {
        setData(res.data.data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="p-12 text-center text-slate-500">Loading parent details...</div>;
  if (!data) return <div className="p-12 text-center text-red-500">Failed to load parent data.</div>;

  return (
    <div className="p-6">
      <div className="flex items-center mb-6">
        <button onClick={() => navigate('/parents')} className="mr-4 p-2 bg-white rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Parent Details</h1>
          <p className="text-slate-500">Manage parent {data.parent.full_name}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-1">
          <div className="bg-white p-6 rounded-lg border border-slate-200">
            <div className="flex flex-col items-center pb-6 border-b border-slate-100">
              <div className="w-24 h-24 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mb-4">
                <User className="w-12 h-12" />
              </div>
              <h2 className="text-xl font-bold text-slate-800">{data.parent.full_name}</h2>
              <span className="inline-flex items-center mt-2 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                {data.parent.status}
              </span>
            </div>
            
            <div className="pt-6 space-y-4">
              <div className="flex items-center text-sm">
                <Mail className="w-4 h-4 text-slate-400 mr-3" />
                <span className="text-slate-700">{data.parent.email}</span>
              </div>
              <div className="flex items-center text-sm">
                <Calendar className="w-4 h-4 text-slate-400 mr-3" />
                <span className="text-slate-700">Joined {new Date(data.parent.created_at).toLocaleDateString()}</span>
              </div>
              <div className="flex items-center text-sm">
                <Shield className="w-4 h-4 text-slate-400 mr-3" />
                <span className="text-slate-700">ID: {data.parent.id}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="md:col-span-2">
          <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <h3 className="text-lg font-medium text-slate-800">Linked Students</h3>
            </div>
            {data.students.length === 0 ? (
              <div className="p-8 text-center text-slate-500">No students linked to this parent yet.</div>
            ) : (
              <div className="divide-y divide-slate-100">
                {data.students.map((rel: any) => (
                  <div key={rel.id} className="p-6 hover:bg-slate-50">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center">
                        <div className="w-10 h-10 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center">
                          <User className="w-5 h-5" />
                        </div>
                        <div className="ml-4">
                          <h4 className="text-sm font-bold text-slate-900">{rel.student.full_name}</h4>
                          <p className="text-xs text-slate-500">{rel.student.email}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${rel.status === 'ACTIVE' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                          {rel.status}
                        </span>
                        <p className="text-xs text-slate-500 mt-1 uppercase font-semibold">{rel.relationship_type}</p>
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
