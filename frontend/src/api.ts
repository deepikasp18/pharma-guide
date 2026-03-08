import axios from 'axios';
import type { PatientProfile, Medication, QueryResponse, Alert, Symptom } from './types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to all requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const queryAPI = {
  processQuery: async (query: string, patientId?: string): Promise<QueryResponse> => {
    const response = await api.post('/query/process', { query, patient_id: patientId });
    return response.data;
  },
};

export const patientAPI = {
  getProfile: async (): Promise<PatientProfile | null> => {
    try {
      const response = await api.get('/patient/profile');
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 401) {
        // Token expired, redirect to login
        localStorage.removeItem('token');
        window.location.reload();
      }
      return null;
    }
  },
  
  createProfile: async (profile: Omit<PatientProfile, 'id'>): Promise<PatientProfile> => {
    const response = await api.post('/patient/profile', profile);
    return response.data;
  },
  
  updateProfile: async (profile: Omit<PatientProfile, 'id'>): Promise<PatientProfile> => {
    const response = await api.post('/patient/profile', profile);
    return response.data;
  },
  
  getMedications: async (): Promise<Medication[]> => {
    try {
      const response = await api.get('/patient/medications');
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 401) {
        localStorage.removeItem('token');
        window.location.reload();
      }
      return [];
    }
  },
  
  addMedication: async (medication: Omit<Medication, 'id'>): Promise<Medication> => {
    const response = await api.post('/patient/medications', medication);
    return response.data;
  },
  
  deleteMedication: async (medicationId: string): Promise<void> => {
    await api.delete(`/patient/medications/${medicationId}`);
  },
  
  getSymptoms: async (): Promise<Symptom[]> => {
    try {
      const response = await api.get('/patient/symptoms');
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 401) {
        localStorage.removeItem('token');
        window.location.reload();
      }
      return [];
    }
  },
  
  addSymptom: async (symptom: Omit<Symptom, 'id'>): Promise<Symptom> => {
    const response = await api.post('/patient/symptoms', symptom);
    return response.data;
  },
  
  deleteSymptom: async (symptomId: string): Promise<void> => {
    await api.delete(`/patient/symptoms/${symptomId}`);
  },
};

export const alertsAPI = {
  getAlerts: async (patientId: string): Promise<Alert[]> => {
    const response = await api.get(`/alerts/active?patient_id=${patientId}`);
    return response.data;
  },
  
  acknowledgeAlert: async (alertId: string): Promise<void> => {
    await api.post(`/alerts/acknowledge/${alertId}`);
  },
};

export default api;

export const authAPI = {
  register: async (username: string, password: string): Promise<{ access_token: string; token_type: string }> => {
    const response = await api.post('/auth/register', { username, password });
    return response.data;
  },
  
  login: async (username: string, password: string): Promise<{ access_token: string; token_type: string }> => {
    const response = await api.post('/auth/login', { username, password });
    return response.data;
  },
  
  getCurrentUser: async (): Promise<{ username: string; user_id: string }> => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};
