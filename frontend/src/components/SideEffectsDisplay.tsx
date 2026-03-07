import type { Medication } from '../types'

interface Props {
  medications: Medication[]
}

export default function SideEffectsDisplay({ medications }: Props) {
  // Mock side effects data - in real app, this would come from API
  const sideEffects = medications.length > 0 ? [
    { name: 'Nausea', severity: 'mild', frequency: 'common' },
    { name: 'Dizziness', severity: 'mild', frequency: 'uncommon' },
    { name: 'Headache', severity: 'moderate', frequency: 'common' },
  ] : []

  const getSeverityStyles = (severity: string) => {
    switch (severity) {
      case 'mild': 
        return {
          gradient: 'from-yellow-400 to-yellow-500',
          bg: 'from-yellow-50 to-yellow-100',
          border: 'border-yellow-200'
        }
      case 'moderate': 
        return {
          gradient: 'from-orange-400 to-orange-500',
          bg: 'from-orange-50 to-orange-100',
          border: 'border-orange-200'
        }
      case 'severe': 
        return {
          gradient: 'from-red-400 to-red-500',
          bg: 'from-red-50 to-red-100',
          border: 'border-red-200'
        }
      default: 
        return {
          gradient: 'from-gray-400 to-gray-500',
          bg: 'from-gray-50 to-gray-100',
          border: 'border-gray-200'
        }
    }
  }

  return (
    <div className="glass-card p-6">
      <div className="flex items-center space-x-2 mb-4">
        <div className="w-8 h-8 bg-gradient-to-br from-warning-500 to-warning-600 rounded-lg flex items-center justify-center">
          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h3 className="text-lg font-bold text-gray-900">Potential Side Effects</h3>
      </div>
      
      {medications.length === 0 ? (
        <p className="text-gray-500 text-sm">Add medications to see potential side effects</p>
      ) : (
        <div className="space-y-3">
          {sideEffects.map((effect, idx) => {
            const styles = getSeverityStyles(effect.severity)
            return (
              <div key={idx} className={`relative overflow-hidden p-4 bg-gradient-to-r ${styles.bg} rounded-xl border-2 ${styles.border} shadow-soft`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-gray-900">{effect.name}</span>
                  <div className={`px-3 py-1 bg-gradient-to-r ${styles.gradient} text-white rounded-lg text-xs font-bold shadow-soft`}>
                    {effect.severity.toUpperCase()}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="flex-1 bg-white/60 rounded-full h-1.5">
                    <div className={`h-1.5 rounded-full bg-gradient-to-r ${styles.gradient} ${effect.frequency === 'common' ? 'w-3/4' : 'w-1/3'}`}></div>
                  </div>
                  <span className="text-xs font-semibold text-gray-600 capitalize">{effect.frequency}</span>
                </div>
              </div>
            )
          })}
          
          <div className="mt-4 p-4 bg-gradient-to-r from-primary-50 to-accent-50 border-2 border-primary-200 rounded-xl">
            <div className="flex items-start space-x-2">
              <svg className="w-5 h-5 text-primary-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm text-primary-800 font-medium">
                This is general information. Consult your healthcare provider for personalized advice.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
