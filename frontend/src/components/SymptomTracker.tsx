import { useState } from 'react'
import type { Symptom } from '../types'

interface Props {
  symptoms: Symptom[]
  onAdd: (symptom: Symptom) => void
}

export default function SymptomTracker({ symptoms, onAdd }: Props) {
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState<Symptom>({
    name: '',
    severity: 5,
    date: new Date().toISOString().split('T')[0],
    notes: ''
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onAdd({ ...formData, id: Date.now().toString() })
    setFormData({ name: '', severity: 5, date: new Date().toISOString().split('T')[0], notes: '' })
    setShowForm(false)
  }

  const getSeverityColor = (severity: number) => {
    if (severity <= 3) return 'from-success-400 to-success-500'
    if (severity <= 6) return 'from-warning-400 to-warning-500'
    return 'from-danger-400 to-danger-500'
  }

  const getSeverityDot = (severity: number) => {
    if (severity <= 3) return 'bg-success-500'
    if (severity <= 6) return 'bg-warning-500'
    return 'bg-danger-500'
  }

  return (
    <div className="glass-card-strong p-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-br from-warning-500 to-warning-600 rounded-xl flex items-center justify-center shadow-soft">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900">Symptom Tracker</h2>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className={showForm ? 'px-6 py-3 bg-gray-200 text-gray-700 rounded-xl hover:bg-gray-300 transition-all duration-200 font-medium' : 'px-6 py-3 bg-gradient-to-r from-warning-500 to-warning-600 text-white rounded-xl hover:from-warning-600 hover:to-warning-700 transition-all duration-200 shadow-soft hover:shadow-medium font-medium'}
        >
          {showForm ? 'Cancel' : '+ Log Symptom'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 p-6 bg-gradient-to-br from-warning-50 to-warning-100 rounded-2xl space-y-4 border-2 border-warning-200">
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">Symptom</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., Headache, Nausea"
              className="input-field"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">
              Severity: {formData.severity}/10
            </label>
            <input
              type="range"
              min="1"
              max="10"
              value={formData.severity}
              onChange={(e) => setFormData({ ...formData, severity: parseInt(e.target.value) })}
              className="w-full h-3 bg-gray-200 rounded-full appearance-none cursor-pointer accent-warning-500"
            />
            <div className="flex justify-between text-xs font-semibold text-gray-600 mt-2">
              <span>Mild</span>
              <span>Severe</span>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">Date</label>
            <input
              type="date"
              value={formData.date}
              onChange={(e) => setFormData({ ...formData, date: e.target.value })}
              className="input-field"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">Notes (optional)</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Any additional details..."
              className="input-field resize-none"
              rows={3}
            />
          </div>
          
          <button
            type="submit"
            className="w-full px-6 py-3 bg-gradient-to-r from-warning-500 to-warning-600 text-white rounded-xl hover:from-warning-600 hover:to-warning-700 transition-all duration-200 shadow-soft hover:shadow-medium font-medium"
          >
            Log Symptom
          </button>
        </form>
      )}

      <div className="space-y-3">
        {symptoms.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-gray-100 to-gray-200 rounded-2xl flex items-center justify-center">
              <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <p className="text-gray-500 font-medium">No symptoms logged yet</p>
            <p className="text-sm text-gray-400 mt-1">Click "Log Symptom" to track your symptoms</p>
          </div>
        ) : (
          symptoms.map((symptom) => (
            <div
              key={symptom.id}
              className="group relative overflow-hidden p-5 bg-gradient-to-r from-white to-warning-50 rounded-xl border-2 border-warning-200 hover:border-warning-400 transition-all duration-200 shadow-soft hover:shadow-medium"
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-warning-200 to-warning-300 rounded-full blur-2xl opacity-0 group-hover:opacity-30 transition-opacity duration-200 -mr-16 -mt-16"></div>
              <div className="relative flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-bold text-gray-900 text-lg">{symptom.name}</h3>
                  <p className="text-sm text-gray-600 mt-1 font-medium">
                    {new Date(symptom.date).toLocaleDateString()}
                  </p>
                  {symptom.notes && (
                    <p className="text-sm text-gray-700 mt-3 p-3 bg-white/60 rounded-lg">{symptom.notes}</p>
                  )}
                </div>
                <div className="ml-4 flex flex-col items-end space-y-2">
                  <div className="flex items-center space-x-2">
                    <div className={`w-3 h-3 rounded-full ${getSeverityDot(symptom.severity)} shadow-soft`} />
                    <span className="text-sm font-bold text-gray-700">{symptom.severity}/10</span>
                  </div>
                  <div className={`px-3 py-1 bg-gradient-to-r ${getSeverityColor(symptom.severity)} text-white rounded-lg text-xs font-bold shadow-soft`}>
                    {symptom.severity <= 3 ? 'MILD' : symptom.severity <= 6 ? 'MODERATE' : 'SEVERE'}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
