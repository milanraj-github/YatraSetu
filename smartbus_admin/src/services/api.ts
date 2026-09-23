import axios from 'axios';
import { auth } from './firebase';
import { signInWithEmailAndPassword, signOut } from 'firebase/auth';

// Backend Base URL
const API_URL = 'http://localhost:8000/api/v1';

// Create Axios instance
const api = axios.create({
  baseURL: API_URL,
});

// Intercept requests to attach the Bearer token
api.interceptors.request.use(async (config) => {
  try {
    const user = auth.currentUser;
    if (user) {
      const token = await user.getIdToken(true); // Always fetch fresh token
      if (config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
  } catch (error) {
    console.error("Error obtaining Firebase token", error);
  }
  return config;
});

export const authService = {
  login: async (email: string, password?: string) => {
    if (!password) {
      throw new Error("Password is required for admin login.");
    }
    await signInWithEmailAndPassword(auth, email, password);
    
    // Explicitly do not store mock-tokens in localStorage.
    // Call sync-user to ensure the user is registered in the DB and get their role
    // The Axios interceptor automatically attaches the Firebase ID token for this call.
    const response = await api.post('/auth/sync-user', { full_name: "Admin User" });
    return response.data;
  },
  
  getMe: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
  syncUser: async (data: { full_name: string }) => {
    const response = await api.post('/auth/sync-user', data);
    return response.data;
  },
  logout: async () => {
    await signOut(auth);
    localStorage.removeItem('admin_token'); // Clear any stale development state
  },

  isAuthenticated: () => {
    // Kept for backward compatibility if any old components use it, but App.tsx handles auth state natively now.
    return !!auth.currentUser;
  }
};

export const dashboardService = {
  getStats: async () => {
    // Fetch counts from the actual Phase 2 management APIs
    try {
      const [busesRes, driversRes, tripsRes] = await Promise.all([
        api.get('/buses'),
        api.get('/drivers'),
        api.get('/trips'), // Note: this gets today's trips or all recent trips depending on backend
      ]);
      
      return {
        buses: busesRes.data.data?.length || 0,
        drivers: driversRes.data.data?.length || 0,
        trips: tripsRes.data.data?.length || 0,
      };
    } catch (error) {
      console.error("Failed to fetch dashboard stats", error);
      throw error;
    }
  }
};

export const busService = {
  getAll: async () => {
    const response = await api.get('/buses');
    return response.data;
  },
  getById: async (id: number) => {
    const response = await api.get(`/buses/${id}`);
    return response.data;
  },
  create: async (data: any) => {
    const response = await api.post('/buses', data);
    return response.data;
  },
  update: async (id: number, data: any) => {
    const response = await api.patch(`/buses/${id}`, data);
    return response.data;
  },
  deactivate: async (id: number) => {
    const response = await api.delete(`/buses/${id}`);
    return response.data;
  }
};

export const routeService = {
  getAll: async () => {
    const response = await api.get('/routes');
    return response.data;
  },
  getById: async (id: number) => {
    const response = await api.get(`/routes/${id}`);
    return response.data;
  },
  create: async (payload: any) => {
    const response = await api.post('/routes', payload);
    return response.data;
  },
  update: async (id: number, payload: any) => {
    const response = await api.patch(`/routes/${id}`, payload);
    return response.data;
  },
  delete: async (id: number) => {
    const response = await api.delete(`/routes/${id}`);
    return response.data;
  },
  addStop: async (id: number, payload: any) => {
    const response = await api.post(`/routes/${id}/stops`, payload);
    return response.data;
  },
  removeStop: async (routeId: number, stopId: number) => {
    const response = await api.delete(`/routes/${routeId}/stops/${stopId}`);
    return response.data;
  },
  reorderStops: async (routeId: number, payload: { route_stop_id: number; new_sequence_order: number }[]) => {
    const response = await api.put(`/routes/${routeId}/stops/reorder`, payload);
    return response.data;
  }
};

export const boardingPointService = {
  getAll: async () => {
    const response = await api.get('/stops');
    return response.data;
  },
  getById: async (id: number) => {
    const response = await api.get(`/stops/${id}`);
    return response.data;
  },
  create: async (data: any) => {
    const response = await api.post('/stops', data);
    return response.data;
  },
  update: async (id: number, data: any) => {
    const response = await api.patch(`/stops/${id}`, data);
    return response.data;
  },
  delete: async (id: number) => {
    const response = await api.delete(`/stops/${id}`);
    return response.data;
  }
};

export const driverService = {
  getAll: async () => {
    const response = await api.get('/drivers');
    return response.data;
  },
  getAllAssignments: async () => {
    const response = await api.get('/drivers/assignments/all');
    return response.data;
  },
  getById: async (id: number) => {
    const response = await api.get(`/drivers/${id}`);
    return response.data;
  },
  getAssignments: async (id: number) => {
    const response = await api.get(`/drivers/${id}/assignments`);
    return response.data;
  },
  assignBus: async (driverId: number, busId: number) => {
    const response = await api.post(`/drivers/${driverId}/assign-bus`, { bus_id: busId });
    return response.data;
  },
  unassignBus: async (driverId: number) => {
    const response = await api.delete(`/drivers/${driverId}/assign-bus`);
    return response.data;
  }
};

export default api;

export const scheduleService = {
  getAll: async () => {
    const response = await api.get('/schedules');
    return response.data;
  },
  getById: async (id: number) => {
    const response = await api.get(`/schedules/${id}`);
    return response.data;
  },
  create: async (data: any) => {
    const response = await api.post('/schedules', data);
    return response.data;
  },
  update: async (id: number, data: any) => {
    const response = await api.patch(`/schedules/${id}`, data);
    return response.data;
  },
  delete: async (id: number) => {
    const response = await api.delete(`/schedules/${id}`);
    return response.data;
  }
};

export const tripService = {
  getAll: async (params?: { session_date?: string, trip_status?: string, bus_id?: number }) => {
    const response = await api.get('/trips', { params });
    return response.data;
  },
  getById: async (id: number) => {
    const response = await api.get(`/trips/${id}`);
    return response.data;
  }
};

export const trackingService = {
  getActiveBuses: async () => {
    const response = await api.get('/tracking/active-buses');
    return response.data;
  }
};

export const alertService = {
  getAll: async (params?: { status?: string, severity?: string, alert_type?: string, bus_id?: number }) => {
    const response = await api.get('/alerts', { params });
    return response.data;
  },
  resolve: async (id: number) => {
    const response = await api.patch(`/alerts/${id}`, { status: 'RESOLVED' });
    return response.data;
  }
};

export const emergencyService = {
  getAll: async (params?: { status?: string, severity?: string, emergency_type?: string, bus_id?: number, driver_id?: number }) => {
    const response = await api.get('/emergencies', { params });
    return response.data;
  },
  acknowledge: async (id: number) => {
    const response = await api.patch(`/emergencies/${id}`, { status: 'ACKNOWLEDGED' });
    return response.data;
  },
  resolve: async (id: number) => {
    const response = await api.patch(`/emergencies/${id}`, { status: 'RESOLVED' });
    return response.data;
  }
};

export const analyticsService = {
  getSummary: async (startDate: string, endDate: string) => {
    const response = await api.get('/analytics/summary', { params: { start_date: startDate, end_date: endDate } });
    return response.data;
  }
};

export const adminStudentService = {
  getStudents: async () => {
    const res = await api.get('/students');
    return res.data;
  },
  assignBus: async (studentId: number, busId: number) => {
    const res = await api.post(`/students/${studentId}/assignment`, { bus_id: busId });
    return res.data;
  },
  removeAssignment: async (studentId: number) => {
    const res = await api.delete(`/students/${studentId}/assignment`);
    return res.data;
  },
};
