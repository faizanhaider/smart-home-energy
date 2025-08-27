import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import TelemetryService from '../services/telemetryService';

const Devices = () => {
  const { user } = useAuth();
  const [devices, setDevices] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timePeriod, setTimePeriod] = useState(24); // hours

  // Load devices data
  const loadDevices = useCallback(async () => {
    if (!user?.id) return;

    setIsLoading(true);
    setError(null);

    try {
      // Check if telemetry service is available
      const isHealthy = await TelemetryService.checkHealth();
      if (!isHealthy) {
        throw new Error('Telemetry service is not available');
      }

      // Load user devices summary
      const deviceSummaries = await TelemetryService.getUserDevicesSummary(user.id, timePeriod);
      setDevices(deviceSummaries);
    } catch (error) {
      console.error('Error loading devices:', error);
      setError(error.message || 'Failed to load devices');
    } finally {
      setIsLoading(false);
    }
  }, [user?.id, timePeriod]);

  // Load data on component mount and when time period changes
  useEffect(() => {
    loadDevices();
  }, [loadDevices]);

  // Calculate efficiency based on power consumption
  const calculateEfficiency = (averagePower, peakPower) => {
    if (peakPower === 0) return 'Unknown';
    
    const efficiency = (averagePower / peakPower) * 100;
    if (efficiency >= 80) return 'High';
    if (efficiency >= 50) return 'Medium';
    return 'Low';
  };

  // Get device type icon based on device name
  const getDeviceIcon = (deviceName) => {
    const name = deviceName.toLowerCase();
    if (name.includes('fridge') || name.includes('refrigerator')) {
      return (
        <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
        </svg>
      );
    } else if (name.includes('ac') || name.includes('air') || name.includes('conditioner')) {
      return (
        <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      );
    } else if (name.includes('light') || name.includes('lamp')) {
      return (
        <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m12.728 0l-.707.707M6.343 6.343l-.707-.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      );
    } else if (name.includes('computer') || name.includes('pc') || name.includes('laptop')) {
      return (
        <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      );
    } else if (name.includes('garage') || name.includes('door')) {
      return (
        <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      );
    } else {
      return (
        <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
        </svg>
      );
    }
  };

  // Get device type based on device name
  const getDeviceType = (deviceName) => {
    const name = deviceName.toLowerCase();
    if (name.includes('fridge') || name.includes('refrigerator')) return 'Refrigerator';
    if (name.includes('ac') || name.includes('air') || name.includes('conditioner')) return 'Air Conditioner';
    if (name.includes('light') || name.includes('lamp')) return 'Lighting';
    if (name.includes('computer') || name.includes('pc') || name.includes('laptop')) return 'Computer';
    if (name.includes('garage') || name.includes('door')) return 'Garage Door';
    return 'Smart Device';
  };

  // Get device location (you can enhance this with actual location data)
  const getDeviceLocation = (deviceName) => {
    const name = deviceName.toLowerCase();
    if (name.includes('kitchen')) return 'Kitchen';
    if (name.includes('living') || name.includes('room')) return 'Living Room';
    if (name.includes('bedroom')) return 'Bedroom';
    if (name.includes('office')) return 'Home Office';
    if (name.includes('garage')) return 'Garage';
    return 'Home';
  };

  const getStatusColor = (status) => {
    return status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800';
  };

  const getEfficiencyColor = (efficiency) => {
    switch (efficiency) {
      case 'High':
        return 'bg-green-100 text-green-800';
      case 'Medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'Low':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
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
        <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Devices</h3>
        <p className="text-gray-600 mb-4">{error}</p>
        <button
          onClick={loadDevices}
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
          <h1 className="text-2xl font-semibold text-gray-900">Devices</h1>
          <p className="mt-2 text-gray-600">
            Monitor and manage your smart home devices
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

      {devices.length > 0 ? (
        <div className="mt-6">
          <div className="bg-white shadow overflow-hidden sm:rounded-md">
            <ul className="divide-y divide-gray-200">
              {devices.map((device) => {
                const efficiency = calculateEfficiency(device.average_power, device.peak_power);
                const status = device.average_power > 0 ? 'active' : 'inactive';
                const deviceType = getDeviceType(device.device_name);
                const location = getDeviceLocation(device.device_name);
                
                return (
                  <li key={device.device_id} className="px-6 py-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <div className="flex-shrink-0">
                          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                            {getDeviceIcon(device.device_name)}
                          </div>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">
                            {device.device_name}
                          </div>
                          <div className="text-sm text-gray-500">
                            {deviceType} • {location}
                          </div>
                          <div className="text-xs text-gray-400 mt-1">
                            {device.data_points} data points • Last reading: {device.last_reading ? 
                              new Date(device.last_reading).toLocaleString() : 'Never'
                            }
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(status)}`}>
                          {status}
                        </span>
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getEfficiencyColor(efficiency)}`}>
                          {efficiency}
                        </span>
                        <div className="text-right">
                          <div className="text-sm text-gray-900 font-medium">
                            {TelemetryService.formatPower(device.average_power)}
                          </div>
                          <div className="text-xs text-gray-500">
                            Peak: {TelemetryService.formatPower(device.peak_power)}
                          </div>
                        </div>
                        <button className="text-blue-600 hover:text-blue-900 text-sm font-medium">
                          Details
                        </button>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      ) : (
        <div className="mt-6 text-center py-12">
          <div className="text-gray-400 mb-4">
            <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Devices Found</h3>
          <p className="text-gray-600 mb-4">
            You don't have any devices configured yet. Add your first smart home device to get started.
          </p>
        </div>
      )}

      <div className="mt-6">
        <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium">
          Add New Device
        </button>
      </div>
    </div>
  );
};

export default Devices;
