import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useWebSocket } from '../contexts/WebSocketContext';
import TelemetryService from '../services/telemetryService';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts';

const DeviceDetails = () => {
  const { deviceId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { isConnected, subscribeToDeviceTelemetry, unsubscribeFromDeviceTelemetry } = useWebSocket();
  const [device, setDevice] = useState(null);
  const [telemetryData, setTelemetryData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timePeriod, setTimePeriod] = useState('7d'); // 7d, 24h, 1m, 1y
  const [chartType, setChartType] = useState('line'); // line, bar, area
  const [isLiveMode, setIsLiveMode] = useState(true);
  const [liveData, setLiveData] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const wsSubscriptionRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Load device details and telemetry data
  const loadDeviceData = useCallback(async () => {
    if (!user?.id || !deviceId) return;

    setIsLoading(true);
    setError(null);

    try {
      // Check if telemetry service is available
      const isHealthy = await TelemetryService.checkHealth();
      if (!isHealthy) {
        throw new Error('Telemetry service is not available');
      }

      // Load device summary
      const deviceSummary = await TelemetryService.getDeviceSummary(deviceId);
      setDevice(deviceSummary);

      // Load telemetry data based on time period
      const hours = getHoursFromPeriod(timePeriod);
      const telemetry = await TelemetryService.getDeviceTelemetryWithTimeFilter(deviceId, hours);
      
      // Process data for charts
      const processedData = processTelemetryData(telemetry, hours);
      setTelemetryData(processedData);

    } catch (error) {
      console.error('Error loading device data:', error);
      setError(error.message || 'Failed to load device data');
    } finally {
      setIsLoading(false);
    }
  }, [user?.id, deviceId, timePeriod]);

  // WebSocket connection management
  useEffect(() => {
    if (isConnected && deviceId) {
      setConnectionStatus('connected');
      
      // Subscribe to device telemetry updates
      subscribeToDeviceTelemetry(deviceId, user?.id);
      wsSubscriptionRef.current = { deviceId, userId: user?.id };
      
      console.log('🔌 WebSocket subscribed to device telemetry:', deviceId);
    } else {
      setConnectionStatus('disconnected');
      
      // Cleanup subscription on disconnect
      if (wsSubscriptionRef.current) {
        unsubscribeFromDeviceTelemetry(wsSubscriptionRef.current.deviceId, wsSubscriptionRef.current.userId);
        wsSubscriptionRef.current = null;
      }
    }

    return () => {
      // Cleanup on unmount
      if (wsSubscriptionRef.current) {
        unsubscribeFromDeviceTelemetry(wsSubscriptionRef.current.deviceId, wsSubscriptionRef.current.userId);
        wsSubscriptionRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [isConnected, deviceId, user?.id, subscribeToDeviceTelemetry, unsubscribeFromDeviceTelemetry]);

  // Handle WebSocket messages for live updates
  useEffect(() => {
    const handleLiveUpdate = (message) => {
      if (message.detail.type === "device_telemetry_update" && 
          message.detail.device_id === deviceId && 
          isLiveMode) {
        
        const newDataPoint = {
          energy: parseFloat(message.detail.energy_watts || 0),
          timestamp: message.detail.timestamp || new Date().toLocaleString(),
          // Convert timestamp into date, hour, and day
          ...(function() {
            const ts = message.detail.timestamp ? new Date(message.detail.timestamp) : new Date();
            return {
              date: ts.toLocaleDateString(),
              hour: ts.getHours(),
              day: ts.getDate()
            };
          })()
        };

        setLiveData(prev => {
          const updated = [...prev, newDataPoint];
          // Keep only last 100 points for performance
          return updated.slice(-100);
        });

        // Keep only data within current time period
        const hours = getHoursFromPeriod(timePeriod);
        const cutoff = new Date(Date.now() - (hours * 60 * 60 * 1000));

        if (new Date(newDataPoint.timestamp) >= cutoff) {
          // Update main telemetry data with live point
          setTelemetryData(prev => {
            return [...prev, newDataPoint];
          });  
        }
      }
    };

    // Add message handler to WebSocket context
    if (window.addEventListener) {
      window.addEventListener('websocket-message', handleLiveUpdate);
    }

    return () => {
      if (window.removeEventListener) {
        window.removeEventListener('websocket-message', handleLiveUpdate);
      }
    };
  }, [deviceId, isLiveMode, timePeriod]);

  // Toggle live mode
  const toggleLiveMode = useCallback(() => {
    setIsLiveMode(prev => !prev);
    if (!isLiveMode) {
      // Clear live data when starting live mode
      setLiveData([]);
    }
  }, [isLiveMode]);

  // Get hours from time period string
  const getHoursFromPeriod = (period) => {
    switch (period) {
      case '24h': return 24;
      case '7d': return 24 * 7;
      case '1m': return 24 * 30;
      case '1y': return 24 * 365;
      default: return 24 * 7;
    }
  };

  // Process telemetry data for charts
  const processTelemetryData = (data, hours) => {
    if (!data || !Array.isArray(data)) return [];

    const now = new Date();
    const cutoff = new Date(now.getTime() - (hours * 60 * 60 * 1000));

    return data
      .filter(item => new Date(item.timestamp) >= cutoff)
      .map(item => ({
        timestamp: new Date(item.timestamp).toLocaleString(),
        energy: parseFloat(item.energy_watts || 0),
        date: new Date(item.timestamp).toLocaleDateString(),
        hour: new Date(item.timestamp).getHours(),
        day: new Date(item.timestamp).getDate()
      }))
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  };

  // Load data on component mount and when time period changes
  useEffect(() => {
    loadDeviceData();
  }, [loadDeviceData]);

  // Calculate statistics
  const calculateStats = () => {
    if (!telemetryData.length) return {};

    const energies = telemetryData.map(d => d.energy);
    const total = energies.reduce((sum, e) => sum + e, 0);
    const average = total / energies.length;
    const peak = Math.max(...energies);
    const min = Math.min(...energies);

    return {
      total: total / 1000, // Convert to kWh
      average: average / 1000,
      peak: peak / 1000,
      min: min / 1000,
      dataPoints: telemetryData.length
    };
  };

  // Get device icon
  const getDeviceIcon = (deviceName) => {
    const name = deviceName?.toLowerCase() || '';
    if (name.includes('fridge') || name.includes('refrigerator')) {
      return (
        <svg className="w-12 h-12 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
        </svg>
      );
    } else if (name.includes('ac') || name.includes('air') || name.includes('conditioner')) {
      return (
        <svg className="w-12 h-12 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      );
    } else if (name.includes('light') || name.includes('lamp')) {
      return (
        <svg className="w-12 h-12 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m12.728 0l-.707.707M6.343 6.343l-.707-.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      );
    } else if (name.includes('computer') || name.includes('pc') || name.includes('laptop')) {
      return (
        <svg className="w-12 h-12 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      );
    } else {
      return (
        <svg className="w-12 h-12 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
        </svg>
      );
    }
  };

  // Render chart based on type
  const renderChart = () => {
    if (!telemetryData.length) {
      return (
        <div className="text-center py-12 text-gray-500">
          No data available for the selected time period
        </div>
      );
    }

    const data = timePeriod === '24h' 
      ? telemetryData.filter((_, index) => index % 2 === 0) // Show every 2nd point for 24h
      : telemetryData;

    if (chartType === 'line') {
      return (
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey={timePeriod === '24h' ? 'hour' : 'date'} 
              tick={{ fontSize: 12 }}
            />
            <YAxis 
              tick={{ fontSize: 12 }}
              label={{ value: 'Energy (W)', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip 
              formatter={(value) => [`${value} W`, 'Energy']}
              labelFormatter={(label) => `Time: ${label}`}
            />
            <Legend />
            <Line 
              type="monotone" 
              dataKey="energy" 
              stroke="#3B82F6" 
              strokeWidth={2}
              dot={{ fill: '#3B82F6', strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6, stroke: '#3B82F6', strokeWidth: 2 }}
            />
            
          </LineChart>
        </ResponsiveContainer>
      );
    } else if (chartType === 'bar') {
      return (
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey={timePeriod === '24h' ? 'hour' : 'date'} 
              tick={{ fontSize: 12 }}
            />
            <YAxis 
              tick={{ fontSize: 12 }}
              label={{ value: 'Energy (W)', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip 
              formatter={(value) => [`${value} W`, 'Energy']}
              labelFormatter={(label) => `Time: ${label}`}
            />
            <Legend />
            <Bar dataKey="energy" fill="#3B82F6" />
            
          </BarChart>
        </ResponsiveContainer>
      );
    } else if (chartType === 'area') {
      return (
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey={timePeriod === '24h' ? 'hour' : 'date'} 
              tick={{ fontSize: 12 }}
            />
            <YAxis 
              tick={{ fontSize: 12 }}
              label={{ value: 'Energy (W)', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip 
              formatter={(value) => [`${value} W`, 'Energy']}
              labelFormatter={(label) => `Time: ${label}`}
            />
            <Legend />
            <Area 
              type="monotone" 
              dataKey="energy" 
              stroke="#3B82F6" 
              fill="#3B82F6" 
              fillOpacity={0.3}
            />
            
          </AreaChart>
        </ResponsiveContainer>
      );
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
        <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Device</h3>
        <p className="text-gray-600 mb-4">{error}</p>
        <button
          onClick={loadDeviceData}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md mr-2"
        >
          Retry
        </button>
        <button
          onClick={() => navigate('/devices')}
          className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md"
        >
          Back to Devices
        </button>
      </div>
    );
  }

  if (!device) {
    return (
      <div className="text-center py-8">
        <h3 className="text-lg font-medium text-gray-900 mb-2">Device Not Found</h3>
        <button
          onClick={() => navigate('/devices')}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md"
        >
          Back to Devices
        </button>
      </div>
    );
  }

  const stats = calculateStats();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => navigate('/devices')}
          className="flex items-center text-blue-600 hover:text-blue-800 mb-4"
        >
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Devices
        </button>
        
        <div className="flex items-center">
          <div className="flex-shrink-0 mr-4">
            {getDeviceIcon(device.device_name)}
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{device.device_name}</h1>
            <p className="text-gray-600 mt-1">
              {device.device_type || 'Smart Device'} • {device.location || 'Home'}
            </p>
          </div>
        </div>
      </div>



      {/* WebSocket Status */}
      <div className="mb-6">
        <div className="flex items-center space-x-4">
          <div className={`flex items-center space-x-2 ${
            connectionStatus === 'connected' ? 'text-green-600' : 'text-red-600'
          }`}>
            <div className={`w-3 h-3 rounded-full ${
              connectionStatus === 'connected' ? 'bg-green-500' : 'bg-red-500'
            }`}></div>
            <span className="text-sm font-medium">
              {connectionStatus === 'connected' ? 'Live Connected' : 'Disconnected'}
            </span>
          </div>
          
          <button
            onClick={toggleLiveMode}
            disabled={connectionStatus !== 'connected'}
            className={`px-3 py-1 text-sm rounded-md ${
              isLiveMode
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-green-600 text-white hover:bg-green-700'
            } disabled:bg-gray-400 disabled:cursor-not-allowed`}
          >
            {isLiveMode ? 'Stop Live' : 'Start Live'}
          </button>
          
          {isLiveMode && (
            <div className="flex items-center space-x-2 text-sm text-gray-600">
              <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
              <span>Live updates active</span>
            </div>
          )}
        </div>
      </div>

      {/* Device Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Average Power</p>
              <p className="text-2xl font-semibold text-gray-900">
                {TelemetryService.formatPower(device.average_power || 0)}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Peak Power</p>
              <p className="text-2xl font-semibold text-gray-900">
                {TelemetryService.formatPower(device.peak_power || 0)}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total Energy</p>
              <p className="text-2xl font-semibold text-gray-900">
                {stats.total ? `${stats.total.toFixed(2)} kWh` : 'N/A'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Data Points</p>
              <p className="text-2xl font-semibold text-gray-900">
                {stats.dataPoints || 0}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Chart Controls */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-4">
            <label className="text-sm font-medium text-gray-700">Time Period:</label>
            <select
              value={timePeriod}
              onChange={(e) => setTimePeriod(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
              <option value="1m">Last Month</option>
              <option value="1y">Last Year</option>
            </select>
          </div>

          <div className="flex items-center space-x-4">
            <label className="text-sm font-medium text-gray-700">Chart Type:</label>
            <div className="flex space-x-2">
              <button
                onClick={() => setChartType('line')}
                className={`px-3 py-2 text-sm rounded-md ${
                  chartType === 'line'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Line
              </button>
              <button
                onClick={() => setChartType('bar')}
                className={`px-3 py-2 text-sm rounded-md ${
                  chartType === 'bar'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Bar
              </button>
              <button
                onClick={() => setChartType('area')}
                className={`px-3 py-2 text-sm rounded-md ${
                  chartType === 'area'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Area
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">
          Energy Consumption - {timePeriod === '24h' ? 'Last 24 Hours' : 
                               timePeriod === '7d' ? 'Last 7 Days' : 
                               timePeriod === '1m' ? 'Last Month' : 'Last Year'}
          {isLiveMode && ' (Live Updates)'}
        </h3>
        {renderChart()}
      </div>

      {/* Device Details */}
      <div className="bg-white rounded-lg shadow p-6 mt-8">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Device Information</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <dl className="space-y-3">
              <div>
                <dt className="text-sm font-medium text-gray-500">Device Name</dt>
                <dd className="text-sm text-gray-900">{device.device_name}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Type</dt>
                <dd className="text-sm text-gray-900">{device.device_type || 'Smart Device'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Location</dt>
                <dd className="text-sm text-gray-900">{device.location || 'Home'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Status</dt>
                <dd className="text-sm text-gray-900">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    device.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                  }`}>
                    {device.is_active ? 'Active' : 'Inactive'}
                  </span>
                </dd>
              </div>
            </dl>
          </div>
          <div>
            <dl className="space-y-3">
              <div>
                <dt className="text-sm font-medium text-gray-500">Manufacturer</dt>
                <dd className="text-sm text-gray-900">{device.manufacturer || 'Unknown'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Model</dt>
                <dd className="text-sm text-gray-900">{device.model || 'Unknown'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Serial Number</dt>
                <dd className="text-sm text-gray-900">{device.serial_number || 'Unknown'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Power Rating</dt>
                <dd className="text-sm text-gray-900">{device.power_rating_watts || 'Unknown'}</dd>
              </div>
            </dl>
          </div>
        </div>
        {device.description && (
          <div className="mt-6">
            <dt className="text-sm font-medium text-gray-500">Description</dt>
            <dd className="text-sm text-gray-900 mt-1">{device.description}</dd>
          </div>
        )}
      </div>
    </div>
  );
};

export default DeviceDetails;
