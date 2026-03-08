import { useState, useEffect } from 'react'
import { patientAPI } from '../api'
import type { PatientProfile } from '../types'

interface Props {
  onProfileUpdate: (profile: PatientProfile | null) => void
}

export default function PatientProfileForm({ onProfileUpdate }: Props) {
  const [loading, setLoading] = useState(true)
  const [isEditing, setIsEditing] = useState(false)
  const [profile, setProfile] = useState<PatientProfile | null>(null)
  const [formData, setFormData] = useState<Omit<PatientProfile, 'id'>>({
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
    loadProfile()
  }, [])

  const loadProfile = async () => {
    setLoading(true)
    try {
      const data = await patientAPI.getProfile()
      if (data) {
        setProfile(data)
        setFormData({
          name: data.name,
          age: data.age,
          gender: data.gender,
          weight: data.weight,
          height: data.height,
          conditions: data.conditions,
          allergies: data.allergies
        })
        onProfileUpdate(data)
      } else {
        setIsEditing(true) // No profile exists, show form
      }
    } catch (error) {
      console.error('Error loading profile:', error)
      setIsEditing(true)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const savedProfile = profile 
        ? await patientAPI.updateProfile(formData)
        : await patientAPI.createProfile(formData)
      
      setProfile(savedProfile)
      setIsEditing(false)
      onProfileUpdate(savedProfile)
    } catch (error) {
      console.error('Error saving profile:', error)
      alert('Failed to save profile. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = () => {
    setIsEditing(true)
  }

  const handleCancel = () => {
    if (profile) {
      // Reset form to saved data
      setFormData({
        name: profile.name,
        age: profile.age,
        gender: profile.gender,
        weight: profile.weight,
        height: profile.height,
        conditions: profile.conditions,
        allergies: profile.allergies
      })
      setIsEditing(false)
    }
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

  if (loading) {
    return (
      <div className="glass-card-strong p-8">
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      </div>
    )
  }

  // Read-only view
  if (profile && !isEditing) {
    return (
      <div className="glass-card-strong p-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-accent-500 to-accent-600 rounded-xl flex items-center justify-center shadow-soft">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Patient Profile</h2>
          </div>
          <button onClick={handleEdit} className="btn-primary">
            Edit Profile
          </button>
        </div>

        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-gradient-to-r from-primary-50 to-accent-50 rounded-xl">
              <p className="text-sm font-medium text-gray-600 mb-1">Name</p>
              <p className="text-lg font-bold text-gray-900">{profile.name}</p>
            </div>
            <div className="p-4 bg-gradient-to-r from-accent-50 to-success-50 rounded-xl">
              <p className="text-sm font-medium text-gray-600 mb-1">Age</p>
              <p className="text-lg font-bold text-gray-900">{profile.age} years</p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 bg-gradient-to-r from-success-50 to-primary-50 rounded-xl">
              <p className="text-sm font-medium text-gray-600 mb-1">Gender</p>
              <p className="text-lg font-bold text-gray-900 capitalize">{profile.gender}</p>
            </div>
            <div className="p-4 bg-gradient-to-r from-primary-50 to-accent-50 rounded-xl">
              <p className="text-sm font-medium text-gray-600 mb-1">Weight</p>
              <p className="text-lg font-bold text-gray-900">{profile.weight} kg</p>
            </div>
            <div className="p-4 bg-gradient-to-r from-accent-50 to-success-50 rounded-xl">
              <p className="text-sm font-medium text-gray-600 mb-1">Height</p>
              <p className="text-lg font-bold text-gray-900">{profile.height} cm</p>
            </div>
          </div>

          <div className="p-4 bg-gradient-to-r from-primary-50 to-primary-100 rounded-xl">
            <p className="text-sm font-bold text-gray-700 mb-3">Medical Conditions</p>
            {profile.conditions.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {profile.conditions.map((condition, idx) => (
                  <span key={idx} className="px-4 py-2 bg-white text-primary-800 rounded-xl text-sm font-medium shadow-soft">
                    {condition}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 italic">No conditions listed</p>
            )}
          </div>

          <div className="p-4 bg-gradient-to-r from-danger-50 to-danger-100 rounded-xl">
            <p className="text-sm font-bold text-gray-700 mb-3">Allergies</p>
            {profile.allergies.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {profile.allergies.map((allergy, idx) => (
                  <span key={idx} className="px-4 py-2 bg-white text-danger-800 rounded-xl text-sm font-medium shadow-soft">
                    {allergy}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 italic">No allergies listed</p>
            )}
          </div>
        </div>
      </div>
    )
  }

  // Edit form
  return (
    <div className="glass-card-strong p-8">
      <div className="flex items-center space-x-3 mb-6">
        <div className="w-10 h-10 bg-gradient-to-br from-accent-500 to-accent-600 rounded-xl flex items-center justify-center shadow-soft">
          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-gray-900">
          {profile ? 'Edit Profile' : 'Create Profile'}
        </h2>
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

        <div className="flex space-x-4">
          <button
            type="submit"
            disabled={loading}
            className="flex-1 btn-secondary disabled:opacity-50"
          >
            {loading ? 'Saving...' : 'Save Profile'}
          </button>
          {profile && (
            <button
              type="button"
              onClick={handleCancel}
              className="px-6 py-3 bg-gray-200 text-gray-700 rounded-xl hover:bg-gray-300 transition-all duration-200 font-medium"
            >
              Cancel
            </button>
          )}
        </div>
      </form>
    </div>
  )
}
