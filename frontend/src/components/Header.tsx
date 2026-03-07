export default function Header() {
  return (
    <header className="glass-card-strong border-b-0 rounded-b-none sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 py-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-primary-500 to-accent-500 rounded-2xl blur opacity-75"></div>
              <div className="relative w-12 h-12 bg-gradient-to-br from-primary-500 to-accent-600 rounded-2xl flex items-center justify-center shadow-medium">
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
            </div>
            <div>
              <h1 className="text-3xl font-bold gradient-text">PharmaGuide</h1>
              <p className="text-sm text-gray-600 font-medium">AI-Powered Health Companion</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-3 px-4 py-2 bg-gradient-to-r from-success-50 to-success-100 rounded-xl border border-success-200">
              <div className="relative">
                <div className="w-2.5 h-2.5 bg-success-500 rounded-full animate-pulse"></div>
                <div className="absolute inset-0 w-2.5 h-2.5 bg-success-400 rounded-full animate-ping"></div>
              </div>
              <span className="text-sm font-semibold text-success-700">System Online</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
