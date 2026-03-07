import { useState, useEffect } from 'react'
import { patientAPI } from '../api'
import type { Medication } from '../types'

export default function MedicationList() {
  const [loading, setLoading] = useState(true)
  const [medications, setMedications] = useState<Medication[]>([])
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState<Omit<Medication, 'id'>>({
    name: '',
    dosage: '',
    frequency: '',
    startDate: new Date().toISOString().split('T')[0]
  })

  useEffect(() => {
    loadMedications()
  }, [])

  const loadMedications = async () => {
    setLoading(true)
    try {
      const data = await patientAPI.getMedications()
      setMedications(data)
    } catch (error) {
      console.error('Error loading medications:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const newMed = await patientAPI.addMedication(formData)
      setMedications([...medications, newMed])
      setFormData({ name: '', dosage: '', frequency: '', startDate: new Date().toISOString().split('T')[0] })
      setShowForm(false)
    } catch (error) {
      console.error('Error adding medication:', error)
      alert('Failed to add medication. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this medication?')) return
    
    setLoading(true)
    try {
      await patientAPI.deleteMedication(id)
      setMedications(medications.filter(m => m.id !== id))
    } catch (error) {
      console.error('Error deleting medication:', error)
      alert('Failed to delete medication. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (loading && medications.length === 0) {
    return (
      <div className="glass-card-strong p-8">
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="glass-card-strong p-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-br from-success-500 to-success-600 rounded-xl flex items-center justify-center shadow-soft">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900">Medications</h2>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          disabled={loading}
          className={showForm ? 'px-6 py-3 bg-gray-200 text-gray-700 rounded-xl hover:bg-gray-300 transition-all duration-200 font-medium' : 'btn-primary'}
        >
          {showForm ? 'Cancel' : '+ Add Medication'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 p-6 bg-gradient-to-br from-success-50 to-success-100 rounded-2xl space-y-4 border-2 border-success-200">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">Medication Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="input-field"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">Dosage</label>
              <input
                type="text"
                value={formData.dosage}
                onChange={(e) => setFormData({ ...formData, dosage: e.target.value })}
                placeholder="e.g., 10mg"
                className="input-field"
                required
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">Frequency</label>
              <input
                type="text"
                value={formData.frequency}
                onChange={(e) => setFormData({ ...formData, frequency: e.target.value })}
                placeholder="e.g., Once daily"
                className="input-field"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">Start Date</label>
              <input
                type="date"
                value={formData.startDate}
                onChange={(e) => setFormData({ ...formData, startDate: e.target.value })}
                className="input-field"
                required
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full btn-primary disabled:opacity-50"
          >
            {loading ? 'Adding...' : 'Add Medication'}
          </button>
        </form>
      )}

      <div className="space-y-3">
        {medications.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-gray-100 to-gray-200 rounded-2xl flex items-center justify-center">
              <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <p className="text-gray-500 font-medium">No medications added yet</p>
            <p className="text-sm text-gray-400 mt-1">Click "Add Medication" to get started</p>
          </div>
        ) : (
          medications.map((med) => (
            <div
              key={med.id}
              className="group relative overflow-hidden flex items-center justify-between p-5 bg-gradient-to-r from-white to-success-50 rounded-xl border-2 border-success-200 hover:border-success-400 transition-all duration-200 shadow-soft hover:shadow-medium"
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-success-200 to-success-300 rounded-full blur-2xl opacity-0 group-hover:opacity-30 transition-opacity duration-200 -mr-16 -mt-16"></div>
              <div className="relative flex-1">
                <h3 className="font-bold text-gray-900 text-lg">{med.name}</h3>
                <div className="flex items-center space-x-3 mt-2 text-sm text-gray-600">
                  <span className="px-3 py-1 bg-success-100 text-success-700 rounded-lg font-medium">{med.dosage}</span>
                  <span className="px-3 py-1 bg-primary-100 text-primary-700 rounded-lg font-medium">{med.frequency}</span>
                  <span className="text-gray-500">Since {new Date(med.startDate).toLocaleDateString()}</span>
                </div>
              </div>
              <button
                onClick={() => med.id && handleDelete(med.id)}
                disabled={loading}
                className="relative ml-4 p-3 text-danger-600 hover:bg-danger-50 rounded-xl transition-all duration-200 hover:scale-110 disabled:opacity-50"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}