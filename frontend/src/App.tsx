import { useState, useEffect } from 'react'
import Header from './components/Header'
import Auth from './components/Auth'
import QueryInterface from './components/QueryInterface'
import PatientProfileForm from './components/PatientProfileForm'
import MedicationList from './components/MedicationList'
import SideEffectsDisplay from './components/SideEffectsDisplay'
import SymptomTracker from './components/SymptomTracker'
import AlertsPanel from './components/AlertsPanel'
import type { PatientProfile, Medication, Alert, Symptom } from './types'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [patientProfile, setPatientProfile] = useState<PatientProfile | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [activeTab, setActiveTab] = useState<'query' | 'profile' | 'medications' | 'symptoms'>('query')

  useEffect(() => {
    // Check for existing token on mount
    const storedToken = localStorage.getItem('token')
    if (storedToken) {
      setIsAuthenticated(true)
    }
  }, [])

  const handleAuthSuccess = (newToken: string) => {
    setIsAuthenticated(true)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    setIsAuthenticated(false)
    setPatientProfile(null)
    setAlerts([])
  }

  if (!isAuthenticated) {
    return <Auth onAuthSuccess={handleAuthSuccess} />
  }

  return (
    <div className="min-h-screen pb-12">
      <Header onLogout={handleLogout} />
      
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Alerts Banner */}
        {alerts.length > 0 && (
          <div className="mb-6">
            <AlertsPanel alerts={alerts} onDismiss={(id) => setAlerts(alerts.filter(a => a.id !== id))} />
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="glass-card mb-6 p-2">
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('query')}
              className={`flex-1 px-6 py-4 font-semibold rounded-xl transition-all duration-200 ${
                activeTab === 'query'
                  ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-medium'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center justify-center space-x-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                <span>Ask Questions</span>
              </div>
            </button>
            <button
              onClick={() => setActiveTab('profile')}
              className={`flex-1 px-6 py-4 font-semibold rounded-xl transition-all duration-200 ${
                activeTab === 'profile'
                  ? 'bg-gradient-to-r from-accent-500 to-accent-600 text-white shadow-medium'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center justify-center space-x-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                <span>Patient Profile</span>
              </div>
            </button>
            <button
              onClick={() => setActiveTab('medications')}
              className={`flex-1 px-6 py-4 font-semibold rounded-xl transition-all duration-200 ${
                activeTab === 'medications'
                  ? 'bg-gradient-to-r from-primary-600 to-accent-500 text-white shadow-medium'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center justify-center space-x-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
                <span>Medications</span>
              </div>
            </button>
            <button
              onClick={() => setActiveTab('symptoms')}
              className={`flex-1 px-6 py-4 font-semibold rounded-xl transition-all duration-200 ${
                activeTab === 'symptoms'
                  ? 'bg-gradient-to-r from-accent-600 to-primary-500 text-white shadow-medium'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center justify-center space-x-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>Symptom Tracker</span>
              </div>
            </button>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            {activeTab === 'query' && (
              <QueryInterface patientId={patientProfile?.id} />
            )}
            
            {activeTab === 'profile' && (
              <PatientProfileForm onProfileUpdate={setPatientProfile} />
            )}
            
            {activeTab === 'medications' && (
              <MedicationList />
            )}
            
            {activeTab === 'symptoms' && (
              <SymptomTracker />
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            <SideEffectsDisplay medications={[]} />
            
            {patientProfile && (
              <div className="glass-card p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center space-x-2">
                  <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <span>Quick Info</span>
                </h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 bg-gradient-to-r from-primary-50 to-accent-50 rounded-xl">
                    <span className="text-sm font-medium text-gray-700">Age</span>
                    <span className="text-lg font-bold text-primary-600">{patientProfile.age}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-gradient-to-r from-success-50 to-primary-50 rounded-xl">
                    <span className="text-sm font-medium text-gray-700">Conditions</span>
                    <span className="text-lg font-bold text-success-600">{patientProfile.conditions.length}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
