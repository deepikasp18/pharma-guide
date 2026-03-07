import { useState, useEffect } from 'react'
import type { PatientProfile } from '../types'

interface Props {
  profile: PatientProfile | null
  onSave: (profile: PatientProfile) => void
}

export default function PatientProfileForm({ profile, onSave }: Props) {
  const [formData, setFormData] = useState<PatientProfile>({
    name: '',
    age: 0,
    gender: '',
    weight: 0,
    height: 0,
    conditions: [],
    allergies: []
  })
  const [conditionInput, setConditionInput] = useState('')
  const [allergyInput, setAllergyInput] = useState('')

  useEffect(() => {
    if (profile) {
      setFormData(profile)
    }
  }, [profile])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
  }

  const addCondition = () => {
    if (conditionInput.trim()) {
      setFormData({ ...formData, conditions: [...formData.conditions, conditionInput.trim()] })
      setConditionInput('')
    }
  }

  const addAllergy = () => {
    if (allergyInput.trim()) {
      setFormData({ ...formData, allergies: [...formData.allergies, allergyInput.trim()] })
      setAllergyInput('')
    }
  }

  return (
    <div className="glass-card-strong p-8">
      <div className="flex items-center space-x-3 mb-6">
        <div className="w-10 h-10 bg-gradient-to-br from-accent-500 to-accent-600 rounded-xl flex items-center justify-center shadow-soft">
          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-gray-900">Patient Profile</h2>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="input-field"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">Age</label>
            <input
              type="number"
              value={formData.age || ''}
              onChange={(e) => setFormData({ ...formData, age: parseInt(e.target.value) })}
              className="input-field"
              required
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">Gender</label>
            <select
              value={formData.gender}
              onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
              className="input-field"
              required
            >
              <option value="">Select</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">Weight (kg)</label>
            <input
              type="number"
              value={formData.weight || ''}
              onChange={(e) => setFormData({ ...formData, weight: parseFloat(e.target.value) })}
              className="input-field"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">Height (cm)</label>
            <input
              type="number"
              value={formData.height || ''}
              onChange={(e) => setFormData({ ...formData, height: parseFloat(e.target.value) })}
              className="input-field"
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-bold text-gray-700 mb-2">Medical Conditions</label>
          <div className="flex space-x-2 mb-3">
            <input
              type="text"
              value={conditionInput}
              onChange={(e) => setConditionInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addCondition())}
              placeholder="Add condition"
              className="input-field flex-1"
            />
            <button
              type="button"
              onClick={addCondition}
              className="px-6 py-3 bg-gradient-to-r from-primary-100 to-primary-200 text-primary-700 rounded-xl hover:from-primary-200 hover:to-primary-300 transition-all duration-200 font-medium"
            >
              Add
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {formData.conditions.map((condition, idx) => (
              <span
                key={idx}
                className="px-4 py-2 bg-gradient-to-r from-primary-100 to-primary-200 text-primary-800 rounded-xl text-sm font-medium flex items-center space-x-2 shadow-soft"
              >
                <span>{condition}</span>
                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, conditions: formData.conditions.filter((_, i) => i !== idx) })}
                  className="text-primary-600 hover:text-primary-800 font-bold text-lg"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-bold text-gray-700 mb-2">Allergies</label>
          <div className="flex space-x-2 mb-3">
            <input
              type="text"
              value={allergyInput}
              onChange={(e) => setAllergyInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addAllergy())}
              placeholder="Add allergy"
              className="input-field flex-1"
            />
            <button
              type="button"
              onClick={addAllergy}
              className="px-6 py-3 bg-gradient-to-r from-danger-100 to-danger-200 text-danger-700 rounded-xl hover:from-danger-200 hover:to-danger-300 transition-all duration-200 font-medium"
            >
              Add
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {formData.allergies.map((allergy, idx) => (
              <span
                key={idx}
                className="px-4 py-2 bg-gradient-to-r from-danger-100 to-danger-200 text-danger-800 rounded-xl text-sm font-medium flex items-center space-x-2 shadow-soft"
              >
                <span>{allergy}</span>
                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, allergies: formData.allergies.filter((_, i) => i !== idx) })}
                  className="text-danger-600 hover:text-danger-800 font-bold text-lg"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>

        <button
          type="submit"
          className="w-full btn-secondary"
        >
          Save Profile
        </button>
      </form>
    </div>
  )
}
