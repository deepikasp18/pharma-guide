import { useState } from 'react'
import { queryAPI } from '../api'
import type { QueryResponse } from '../types'

interface Props {
  patientId?: string
}

export default function QueryInterface({ patientId }: Props) {
  const [query, setQuery] = useState('')
  const [response, setResponse] = useState<QueryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError(null)
    try {
      const result = await queryAPI.processQuery(query, patientId)
      setResponse(result)
    } catch (error: any) {
      console.error('Query failed:', error)
      if (error.response?.status === 401) {
        // Token expired or invalid - clear and reload
        localStorage.removeItem('token')
        window.location.reload()
      } else {
        setError(error.response?.data?.detail || 'Failed to process query. Please try again.')
      }
      setResponse(null)
    } finally {
      setLoading(false)
    }
  }

  const getSeverityColor = (severity?: string) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
      case 'major':
        return 'from-red-100 to-red-50 border-red-300 text-red-800'
      case 'moderate':
        return 'from-yellow-100 to-yellow-50 border-yellow-300 text-yellow-800'
      case 'minor':
        return 'from-blue-100 to-blue-50 border-blue-300 text-blue-800'
      default:
        return 'from-gray-100 to-gray-50 border-gray-300 text-gray-800'
    }
  }

  return (
    <div className="glass-card-strong p-8">
      <div className="flex items-center space-x-3 mb-6">
        <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-xl flex items-center justify-center shadow-soft">
          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-gray-900">Ask About Your Medications</h2>
      </div>
      
      <form onSubmit={handleSubmit} className="mb-8">
        <div className="relative">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask me anything about your medications, side effects, interactions..."
            className="input-field resize-none shadow-soft"
            rows={4}
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="absolute bottom-4 right-4 btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <div className="flex items-center space-x-2">
                <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Processing...</span>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <span>Ask</span>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </div>
            )}
          </button>
        </div>
      </form>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border-2 border-red-200 rounded-xl">
          <div className="flex items-start space-x-3">
            <svg className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-red-800">{error}</p>
          </div>
        </div>
      )}

      {response && (
        <div className="space-y-6">
          {/* Query Info */}
          <div className="glass-card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-gray-900">Query Analysis</h3>
              <span className="px-3 py-1 bg-primary-100 text-primary-700 text-sm font-medium rounded-lg">
                {response.intent.replace('_', ' ').toUpperCase()}
              </span>
            </div>
            
            {/* Entities */}
            {response.entities && response.entities.length > 0 && (
              <div className="mb-4">
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Detected Entities:</h4>
                <div className="flex flex-wrap gap-2">
                  {response.entities.map((entity, idx) => (
                    <div
                      key={idx}
                      className="px-3 py-1 bg-gradient-to-r from-accent-100 to-primary-100 border border-accent-200 rounded-lg"
                    >
                      <span className="text-sm font-medium text-gray-800">{entity.text}</span>
                      <span className="text-xs text-gray-600 ml-2">({entity.type})</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Confidence */}
            <div className="p-4 bg-gradient-to-r from-primary-50 to-accent-50 rounded-xl">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-gray-700">Confidence Level</span>
                <span className="text-sm font-bold text-primary-600">
                  {Math.round(response.confidence * 100)}%
                </span>
              </div>
              <div className="relative w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                <div
                  className="absolute top-0 left-0 h-full bg-gradient-to-r from-success-400 to-success-600 rounded-full transition-all duration-500 shadow-soft"
                  style={{ width: `${response.confidence * 100}%` }}
                >
                  <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
                </div>
              </div>
            </div>
          </div>

          {/* Results */}
          {response.results && response.results.length > 0 && (
            <div className="space-y-4">
              <h3 className="text-lg font-bold text-gray-900 flex items-center space-x-2">
                <svg className="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>Results ({response.results.length})</span>
              </h3>
              
              {response.results.map((result, idx) => (
                <div
                  key={idx}
                  className={`p-6 bg-gradient-to-r ${getSeverityColor(result.severity)} border-2 rounded-2xl shadow-soft`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <h4 className="text-lg font-bold">{result.name}</h4>
                    {result.severity && (
                      <span className="px-3 py-1 bg-white/80 backdrop-blur-sm rounded-lg text-sm font-semibold">
                        {result.severity}
                      </span>
                    )}
                  </div>
                  
                  {result.frequency && (
                    <p className="text-sm font-medium mb-2">
                      <span className="font-semibold">Frequency:</span> {result.frequency}
                    </p>
                  )}
                  
                  {result.description && (
                    <p className="text-sm mb-3">{result.description}</p>
                  )}
                  
                  {result.management && (
                    <div className="mt-3 p-3 bg-white/60 backdrop-blur-sm rounded-lg">
                      <p className="text-sm">
                        <span className="font-semibold">Management:</span> {result.management}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Evidence Sources */}
          {response.evidence_sources && response.evidence_sources.length > 0 && (
            <div className="glass-card p-6">
              <h4 className="text-sm font-bold text-gray-700 mb-3 flex items-center space-x-2">
                <svg className="w-5 h-5 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
                <span>Evidence Sources</span>
              </h4>
              <div className="flex flex-wrap gap-2">
                {response.evidence_sources.map((source, idx) => (
                  <span
                    key={idx}
                    className="px-4 py-2 bg-gradient-to-r from-primary-100 to-accent-100 text-primary-700 text-sm font-medium rounded-xl border border-primary-200 shadow-soft"
                  >
                    {source}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
