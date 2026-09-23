import React, { useState, useEffect } from 'react';
import { adminStudentService, busService } from '../services/api';


interface Bus {
  id: number;
  bus_number: string;
  registration_number: string;
  status: string;
}

interface Student {
  id: number;
  full_name: string;
  email: string;
  status: string;
  current_bus_number: string | null;
}

const Students: React.FC = () => {
  const [students, setStudents] = useState<Student[]>([]);
  const [buses, setBuses] = useState<Bus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [selectedBusId, setSelectedBusId] = useState<number | ''>('');
  const [assigning, setAssigning] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [studentsRes, busesRes] = await Promise.all([
        adminStudentService.getStudents(),
        busService.getAll()
      ]);
      setStudents(studentsRes.data);
      setBuses(busesRes.data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenAssign = (student: Student) => {
    setSelectedStudent(student);
    setSelectedBusId('');
    setShowAssignModal(true);
  };

  const handleAssignBus = async () => {
    if (!selectedStudent || selectedBusId === '') return;
    try {
      setAssigning(true);
      await adminStudentService.assignBus(selectedStudent.id, Number(selectedBusId));
      setShowAssignModal(false);
      fetchData(); // Refresh list
    } catch (err: any) {
      alert(err.message || 'Failed to assign bus');
    } finally {
      setAssigning(false);
    }
  };

  const handleRemoveBus = async (studentId: number) => {
    if (!window.confirm("Are you sure you want to remove this assignment?")) return;
    try {
      setAssigning(true);
      await adminStudentService.removeAssignment(studentId);
      fetchData(); // Refresh list
    } catch (err: any) {
      alert(err.message || 'Failed to remove assignment');
    } finally {
      setAssigning(false);
    }
  };

  if (loading) return <div className="p-6">Loading students...</div>;
  if (error) return <div className="p-6 text-red-500">Error: {error}</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Student Assignments</h1>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Current Bus</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {students.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-sm text-gray-500">
                  No students found.
                </td>
              </tr>
            ) : (
              students.map((student) => (
              <tr key={student.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{student.full_name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{student.email}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${student.status === 'ACTIVE' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                    {student.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {student.current_bus_number ? (
                    <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-bold">{student.current_bus_number}</span>
                  ) : (
                    <span className="text-gray-400">Not Assigned</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  {student.current_bus_number ? (
                    <div className="space-x-3">
                      <button onClick={() => handleOpenAssign(student)} className="text-indigo-600 hover:text-indigo-900">Change</button>
                      <button onClick={() => handleRemoveBus(student.id)} className="text-red-600 hover:text-red-900">Remove</button>
                    </div>
                  ) : (
                    <button onClick={() => handleOpenAssign(student)} className="text-indigo-600 hover:text-indigo-900">Assign Bus</button>
                  )}
                </td>
              </tr>
            )))}
          </tbody>
        </table>
      </div>

      {showAssignModal && (
        <div className="fixed z-10 inset-0 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 transition-opacity" aria-hidden="true" onClick={() => setShowAssignModal(false)}>
              <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
            </div>
            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                    <h3 className="text-lg leading-6 font-medium text-gray-900">
                      {selectedStudent?.current_bus_number ? 'Change Bus Assignment' : 'Assign Bus'}
                    </h3>
                    <div className="mt-4">
                      <p className="text-sm text-gray-500 mb-2">Select a bus for <strong>{selectedStudent?.full_name}</strong>.</p>
                      <select 
                        className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md border"
                        value={selectedBusId}
                        onChange={(e) => setSelectedBusId(e.target.value ? Number(e.target.value) : '')}
                      >
                        <option value="">Select a Bus</option>
                        {buses.map(bus => (
                          <option key={bus.id} value={bus.id}>{bus.bus_number} ({bus.status})</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button
                  type="button"
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50"
                  onClick={handleAssignBus}
                  disabled={assigning || selectedBusId === ''}
                >
                  {assigning ? 'Saving...' : 'Confirm'}
                </button>
                <button
                  type="button"
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                  onClick={() => setShowAssignModal(false)}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Students;
