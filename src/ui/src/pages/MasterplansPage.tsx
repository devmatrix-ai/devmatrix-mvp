import React from 'react'
import { MasterplansList } from '../components/masterplans/MasterplansList'

export const MasterplansPage: React.FC = () => {
  return (
    <div className="h-screen overflow-auto bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="text-5xl">🎯</div>
            <h1 className="text-4xl font-bold text-white">
              Mission Control
            </h1>
          </div>
          <p className="text-gray-400 text-lg">
            Manage and monitor all your development masterplans
          </p>
        </div>

        {/* Masterplans List */}
        <MasterplansList />
      </div>
    </div>
  )
}
