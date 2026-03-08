import type { Alert } from '../types'

interface Props {
  alerts: Alert[]
  onDismiss: (id: string) => void
}

export default function AlertsPanel({ alerts, onDismiss }: Props) {
  const getSeverityStyles = (severity: string) => {
    switch (severity) {
      case 'critical':
        return {
          bg: 'from-danger-100 to-danger-200',
          border: 'border-danger-500',
          text: 'text-danger-900'
        }
      case 'high':
        return {
          bg: 'from-orange-100 to-orange-200',
          border: 'border-orange-500',
          text: 'text-orange-900'
        }
      case 'medium':
        return {
          bg: 'from-warning-100 to-warning-200',
          border: 'border-warning-500',
          text: 'text-warning-900'
        }
      case 'low':
        return {
          bg: 'from-primary-100 to-primary-200',
          border: 'border-primary-500',
          text: 'text-primary-900'
        }
      default:
        return {
          bg: 'from-gray-100 to-gray-200',
          border: 'border-gray-500',
          text: 'text-gray-900'
        }
    }
  }

  const getIcon = (type: string) => {
    switch (type) {
      case 'interaction':
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        )
      case 'contraindication':
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
          </svg>
        )
      default:
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )
    }
  }

  return (
    <div className="space-y-3">
      {alerts.map((alert) => {
        const styles = getSeverityStyles(alert.severity)
        return (
          <div
            key={alert.id}
            className={`relative overflow-hidden flex items-start space-x-4 p-5 bg-gradient-to-r ${styles.bg} border-l-4 ${styles.border} rounded-xl shadow-medium ${styles.text}`}
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-white rounded-full blur-3xl opacity-20 -mr-16 -mt-16"></div>
            <div className="relative flex-shrink-0 w-10 h-10 bg-white/80 rounded-xl flex items-center justify-center shadow-soft">
              {getIcon(alert.type)}
            </div>
            <div className="relative flex-1">
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="font-bold capitalize text-lg">{alert.type} Alert</h4>
                  <p className="mt-1 text-sm font-medium">{alert.message}</p>
                  <p className="mt-2 text-xs opacity-75 font-semibold">
                    {new Date(alert.timestamp).toLocaleString()}
                  </p>
                </div>
                <button
                  onClick={() => onDismiss(alert.id)}
                  className="ml-4 p-2 hover:bg-white/40 rounded-xl transition-all duration-200 hover:scale-110"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
