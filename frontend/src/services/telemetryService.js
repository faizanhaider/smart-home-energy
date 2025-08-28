/**
 * Telemetry Service API client
 * Handles communication with the telemetry service backend
 */

import axios from 'axios';

const TELEMETRY_SERVICE_URL = process.env.REACT_APP_TELEMETRY_API_URL || 'http://localhost:8001';

// Helper function to get auth token from localStorage
const getAuthToken = () => {
  return localStorage.getItem('token');
};

// Helper function to create axios instance with auth headers
const createAuthenticatedRequest = () => {
  const token = getAuthToken();
  const config = {
    headers: {}
  };
  
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  return config;
};

class TelemetryService {
  /**
   * Get energy consumption summary for all user devices
   * @param {string} userId - The user's ID
   * @param {number} hours - Time period in hours (default: 24)
   * @returns {Promise<Array>} Array of device summaries
   */
  static async getUserDevicesSummary(userId, hours = 24) {
    try {
      const response = await axios.get(
        `${TELEMETRY_SERVICE_URL}/user/${userId}/devices?hours=${hours}`,
        createAuthenticatedRequest()
      );

      return response.data;
    } catch (error) {
      console.error('Error fetching user devices summary:', error);
      throw error;
    }
  }

  /**
   * Get overall energy consumption summary for a user
   * @param {string} userId - The user's ID
   * @param {number} hours - Time period in hours (default: 24)
   * @returns {Promise<Object>} User devices summary
   */
  static async getUserSummary(userId, hours = 24) {
    try {
      const response = await axios.get(
        `${TELEMETRY_SERVICE_URL}/user/${userId}/summary?hours=${hours}`,
        createAuthenticatedRequest()
      );

      return response.data;
    } catch (error) {
      console.error('Error fetching user summary:', error);
      throw error;
    }
  }

  /**
   * Get telemetry data for a specific device
   * @param {string} deviceId - The device ID
   * @returns {Promise<Array>} Array of telemetry data points
   */
  static async getDeviceTelemetry(deviceId) {
    try {
      const response = await axios.get(
        `${TELEMETRY_SERVICE_URL}/device/${deviceId}`,
        createAuthenticatedRequest()
      );

      return response.data;
    } catch (error) {
      console.error('Error fetching device telemetry:', error);
      throw error;
    }
  }

  /**
   * Get telemetry data for a specific device with time filtering
   * @param {string} deviceId - The device ID
   * @param {number} hours - Number of hours to look back
   * @returns {Promise<Array>} Array of telemetry data points
   */
  static async getDeviceTelemetryWithTimeFilter(deviceId, hours = 168) {
    try {
      const response = await axios.get(
        `${TELEMETRY_SERVICE_URL}/device/${deviceId}?hours=${hours}`,
        createAuthenticatedRequest()
      );

      return response.data;
    } catch (error) {
      console.error('Error fetching device telemetry with time filter:', error);
      throw error;
    }
  }

  /**
   * Get device summary
   * @param {string} deviceId - The device ID
   * @returns {Promise<Object>} Device summary
   */
  static async getDeviceSummary(deviceId) {
    try {
      const response = await axios.get(
        `${TELEMETRY_SERVICE_URL}/device/${deviceId}/summary`,
        createAuthenticatedRequest()
      );

      return response.data;
    } catch (error) {
      console.error('Error fetching device summary:', error);
      throw error;
    }
  }

  /**
   * Get hourly telemetry data for a device
   * @param {string} deviceId - The device ID
   * @returns {Promise<Array>} Array of hourly data
   */
  static async getDeviceHourlyData(deviceId) {
    try {
      const response = await axios.get(
        `${TELEMETRY_SERVICE_URL}/device/${deviceId}/hourly`,
        createAuthenticatedRequest()
      );

      return response.data;
    } catch (error) {
      console.error('Error fetching device hourly data:', error);
      throw error;
    }
  }

  /**
   * Check if the telemetry service is healthy
   * @returns {Promise<boolean>} True if service is healthy
   */
  static async checkHealth() {
    try {
      const response = await axios.get(`${TELEMETRY_SERVICE_URL}/health`);
      return response.status === 200;
    } catch (error) {
      console.error('Error checking telemetry service health:', error);
      return false;
    }
  }

  /**
   * Calculate energy cost based on consumption
   * @param {number} energyKwh - Energy consumption in kWh
   * @param {number} ratePerKwh - Rate per kWh (default: $0.12)
   * @returns {number} Cost in dollars
   */
  static calculateEnergyCost(energyKwh, ratePerKwh = 0.12) {
    return energyKwh * ratePerKwh;
  }

  /**
   * Format energy consumption for display
   * @param {number} watts - Power in watts
   * @returns {string} Formatted power string
   */
  static formatPower(watts) {
    if (watts >= 1000) {
      return `${(watts / 1000).toFixed(1)} kW`;
    }
    return `${Math.round(watts)} W`;
  }

  /**
   * Format energy consumption for display
   * @param {number} wattHours - Energy in watt-hours
   * @returns {string} Formatted energy string
   */
  static formatEnergy(wattHours) {
    if (wattHours >= 1000) {
      return `${(wattHours / 1000).toFixed(1)} kWh`;
    }
    return `${Math.round(wattHours)} Wh`;
  }
}

export default TelemetryService;
