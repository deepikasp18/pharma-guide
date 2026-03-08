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
  query_id: string;
  user_id: string;
  original_query: string;
  intent: string;
  entities: Array<{
    text: string;
    type: string;
    confidence: number;
    normalized_form?: string;
  }>;
  results: Array<{
    type: string;
    name: string;
    severity?: string;
    frequency?: string;
    description?: string;
    management?: string;
  }>;
  evidence_sources: string[];
  confidence: number;
  timestamp: string;
}

export interface Symptom {
  id?: string;
  name: string;
  severity: number;
  date: string;
  notes?: string;
}
