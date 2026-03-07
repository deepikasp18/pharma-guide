export interface PatientProfile {
  id?: string;
  name: string;
  age: number;
  gender: string;
  weight: number;
  height: number;
  conditions: string[];
  allergies: string[];
}

export interface Medication {
  id?: string;
  name: string;
  dosage: string;
  frequency: string;
  startDate: string;
}

export interface SideEffect {
  name: string;
  severity: string;
  frequency: string;
  description: string;
}

export interface Interaction {
  drugA: string;
  drugB: string;
  severity: string;
  description: string;
  management: string;
}

export interface Alert {
  id: string;
  type: 'interaction' | 'contraindication' | 'dosing' | 'monitoring';
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  timestamp: string;
}

export interface QueryResponse {
  answer: string;
  confidence: number;
  sources: string[];
  relatedInfo?: string[];
}

export interface Symptom {
  id?: string;
  name: string;
  severity: number;
  date: string;
  notes?: string;
}
