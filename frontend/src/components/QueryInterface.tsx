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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    try {
      const result = await queryAPI.processQuery(query, patientId)
      setResponse(result)
    } catch (error) {
      console.error('Query failed:', error)
      setResponse({
        answer: 'Sorry, I encountered an error processing your question. Please try again.',
        confidence: 0,
        sources: []
      })
    } finally {
      setLoading(false)
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

      {response && (
        <div className="space-y-6">
          <div className="relative overflow-hidden bg-gradient-to-br from-primary-50 via-accent-50 to-primary-50 border-2 border-primary-200 rounded-2xl p-6 shadow-soft">
            <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-accent-200 to-primary-200 rounded-full blur-3xl opacity-30 -mr-32 -mt-32"></div>
            <div className="relative flex items-start space-x-4">
              <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-xl flex items-center justify-center shadow-medium">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <div className="flex-1">
                <p className="text-gray-800 leading-relaxed text-lg">{response.answer}</p>
                
                {response.confidence > 0 && (
                  <div className="mt-4 p-4 bg-white/80 backdrop-blur-sm rounded-xl">
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
                )}
              </div>
            </div>
          </div>

          {response.sources && response.sources.length > 0 && (
            <div className="glass-card p-6">
              <h4 className="text-sm font-bold text-gray-700 mb-3 flex items-center space-x-2">
                <svg className="w-5 h-5 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
                <span>Evidence Sources</span>
              </h4>
              <div className="flex flex-wrap gap-2">
                {response.sources.map((source, idx) => (
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
