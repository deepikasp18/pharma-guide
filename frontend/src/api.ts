import axios from 'axios';
import type { PatientProfile, Medication, QueryResponse, Alert, Symptom } from './types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const queryAPI = {
  processQuery: async (query: string, patientId?: string): Promise<QueryResponse> => {
    const response = await api.post('/query/process', { query, patient_id: patientId });
    return response.data;
  },
};

export const patientAPI = {
  createProfile: async (profile: PatientProfile): Promise<PatientProfile> => {
    const response = await api.post('/patient/profile', profile);
    return response.data;
  },
  
  updateProfile: async (id: string, profile: Partial<PatientProfile>): Promise<PatientProfile> => {
    const response = await api.put(`/patient/profile/${id}`, profile);
    return response.data;
  },
  
  addMedication: async (patientId: string, medication: Medication): Promise<Medication> => {
    const response = await api.post(`/patient/${patientId}/medications`, medication);
    return response.data;
  },
  
  getMedications: async (patientId: string): Promise<Medication[]> => {
    const response = await api.get(`/patient/${patientId}/medications`);
    return response.data;
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

export const symptomsAPI = {
  logSymptom: async (patientId: string, symptom: Symptom): Promise<Symptom> => {
    const response = await api.post(`/patient/${patientId}/symptoms`, symptom);
    return response.data;
  },
  
  getSymptoms: async (patientId: string): Promise<Symptom[]> => {
    const response = await api.get(`/patient/${patientId}/symptoms`);
    return response.data;
  },
};

export default api;
