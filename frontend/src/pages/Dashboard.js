import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import TelemetryService from '../services/telemetryService';

const Dashboard = () => {
  const { user } = useAuth();
  const [userSummary, setUserSummary] = useState(null);
  const [deviceSummaries, setDeviceSummaries] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timePeriod, setTimePeriod] = useState(24); // hours

  // Load dashboard data
  const loadDashboardData = useCallback(async () => {
    if (!user?.id) return;

    setIsLoading(true);
    setError(null);

    try {
      // Check if telemetry service is available
      const isHealthy = await TelemetryService.checkHealth();
      if (!isHealthy) {
        throw new Error('Telemetry service is not available');
      }

      // Load user summary and device summaries in parallel
      const [summary, devices] = await Promise.all([
        TelemetryService.getUserSummary(user.id, timePeriod),
        TelemetryService.getUserDevicesSummary(user.id, timePeriod)
      ]);

      setUserSummary(summary);
      setDeviceSummaries(devices);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
      setError(error.message || 'Failed to load dashboard data');
    } finally {
      setIsLoading(false);
    }
  }, [user?.id, timePeriod]);

  // Load data on component mount and when time period changes
  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  // Calculate cost based on energy consumption
  const calculateCost = (energyWh) => {
    const energyKwh = energyWh / 1000;
    return TelemetryService.calculateEnergyCost(energyKwh);
  };

  // Get recent activity from device summaries
  const getRecentActivity = () => {
    if (!deviceSummaries.length) return [];

    return deviceSummaries
      .filter(device => device.last_reading)
      .sort((a, b) => new Date(b.last_reading) - new Date(a.last_reading))
      .slice(0, 5)
      .map(device => ({
        id: device.device_id,
        name: device.device_name,
        action: device.average_power > 0 ? 'Active' : 'Inactive',
        power: device.average_power,
        timestamp: device.last_reading,
        type: device.average_power > 0 ? 'active' : 'inactive'
      }));
  };

  // Format timestamp for display
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'Unknown';
    
    const now = new Date();
    const time = new Date(timestamp);
    const diffMs = now - time;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minutes ago`;
    if (diffHours < 24) return `${diffHours} hours ago`;
    return time.toLocaleDateString();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <div className="text-red-600 mb-4">
          <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Dashboard</h3>
        <p className="text-gray-600 mb-4">{error}</p>
        <button
          onClick={loadDashboardData}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
          <p className="mt-2 text-gray-600">
            Welcome to your Smart Home Energy Monitoring Dashboard
          </p>
        </div>
        
        {/* Time Period Selector */}
        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium text-gray-700">Time Period:</label>
          <select
            value={timePeriod}
            onChange={(e) => setTimePeriod(Number(e.target.value))}
            className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={1}>Last Hour</option>
            <option value={24}>Last 24 Hours</option>
            <option value={168}>Last Week</option>
            <option value={720}>Last Month</option>
          </select>
        </div>
      </div>
      
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {/* Energy Overview Card */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Total Energy ({timePeriod === 1 ? 'Hour' : timePeriod === 24 ? 'Day' : timePeriod === 168 ? 'Week' : 'Month'})
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {userSummary ? TelemetryService.formatEnergy(userSummary.total_energy) : '0 kWh'}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        {/* Cost Card */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                  </svg>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Estimated Cost
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {userSummary ? `$${calculateCost(userSummary.total_energy).toFixed(2)}` : '$0.00'}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        {/* Devices Card */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-purple-500 rounded-md flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                  </svg>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Active Devices
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {userSummary ? userSummary.device_count : 0}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Additional Stats */}
      {userSummary && (
        <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Average Power</dt>
                <dd className="text-lg font-medium text-gray-900">
                  {TelemetryService.formatPower(userSummary.average_power)}
                </dd>
              </dl>
            </div>
          </div>
          
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Peak Power</dt>
                <dd className="text-lg font-medium text-gray-900">
                  {TelemetryService.formatPower(userSummary.peak_power)}
                </dd>
              </dl>
            </div>
          </div>
          
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Data Points</dt>
                <dd className="text-lg font-medium text-gray-900">
                  {userSummary.data_points.toLocaleString()}
                </dd>
              </dl>
            </div>
          </div>
          
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Efficiency</dt>
                <dd className="text-lg font-medium text-gray-900">
                  {userSummary.total_energy > 0 ? 
                    `${((userSummary.average_power / userSummary.peak_power) * 100).toFixed(1)}%` : 
                    'N/A'
                  }
                </dd>
              </dl>
            </div>
          </div>
        </div>
      )}

      {/* Recent Activity */}
      <div className="mt-8">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Recent Activity</h2>
        <div className="bg-white shadow overflow-hidden sm:rounded-md">
          {deviceSummaries.length > 0 ? (
            <ul className="divide-y divide-gray-200">
              {getRecentActivity().map((activity) => (
                <li key={activity.id} className="px-6 py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                          activity.type === 'active' ? 'bg-blue-100' : 'bg-gray-100'
                        }`}>
                          <svg className={`w-4 h-4 ${
                            activity.type === 'active' ? 'text-blue-600' : 'text-gray-600'
                          }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            {activity.type === 'active' ? (
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            ) : (
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            )}
                          </svg>
                        </div>
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">
                          {activity.name} {activity.action.toLowerCase()}
                        </div>
                        <div className="text-sm text-gray-500">
                          {formatTimestamp(activity.timestamp)}
                        </div>
                      </div>
                    </div>
                    <div className="text-sm text-gray-500">
                      {TelemetryService.formatPower(activity.power)}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="px-6 py-8 text-center text-gray-500">
              <p>No recent activity to display</p>
            </div>
          )}
        </div>
      </div>

      {/* Device List */}
      {deviceSummaries.length > 0 && (
        <div className="mt-8">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Device Summary</h2>
          <div className="bg-white shadow overflow-hidden sm:rounded-md">
            <ul className="divide-y divide-gray-200">
              {deviceSummaries.map((device) => (
                <li key={device.device_id} className="px-6 py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                          <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                          </svg>
                        </div>
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">
                          {device.device_name}
                        </div>
                        <div className="text-sm text-gray-500">
                          {device.data_points} data points
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-gray-900">
                        {TelemetryService.formatEnergy(device.total_energy)}
                      </div>
                      <div className="text-sm text-gray-500">
                        Avg: {TelemetryService.formatPower(device.average_power)}
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
