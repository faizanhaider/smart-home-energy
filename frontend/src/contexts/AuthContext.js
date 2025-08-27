import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';

// API configuration
const API_BASE_URL = process.env.REACT_APP_AUTH_API_URL || 'http://localhost:8000';

// Create auth context
const AuthContext = createContext();

// Custom hook to use auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Auth provider component
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('authToken'));

  // Configure axios defaults
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [token]);

  // Check if user is authenticated on mount
  useEffect(() => {
    const checkAuth = async () => {
      if (token) {
        try {
          const response = await axios.get(`${API_BASE_URL}/profile`);
          setUser(response.data);
        } catch (error) {
          console.error('Authentication check failed:', error);
          logout();
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, [token]);

  // Login function
  const login = async (email, password) => {
    try {
      setLoading(true);
      const response = await axios.post(`${API_BASE_URL}/login`, {
        email,
        password
      });

      const { access_token } = response.data;
      
      // Store token
      localStorage.setItem('authToken', access_token);
      setToken(access_token);
      
      // Set axios header
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      // Get user profile
      const userResponse = await axios.get(`${API_BASE_URL}/profile`);
      setUser(userResponse.data);
      
      toast.success('Login successful!');
      return { success: true };
      
    } catch (error) {
      console.error('Login failed:', error);
      const message = error.response?.data?.detail || 'Login failed. Please try again.';
      toast.error(message);
      return { success: false, error: message };
    } finally {
      setLoading(false);
    }
  };

  // Register function
  const register = async (userData) => {
    try {
      setLoading(true);
      const response = await axios.post(`${API_BASE_URL}/register`, userData);
      
      toast.success('Registration successful! Please log in.');
      return { success: true, user: response.data };
      
    } catch (error) {
      console.error('Registration failed:', error);
      const message = error.response?.data?.detail || 'Registration failed. Please try again.';
      toast.error(message);
      return { success: false, error: message };
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const logout = async () => {
    try {
      // Call logout endpoint if token exists
      if (token) {
        await axios.post(`${API_BASE_URL}/logout`);
      }
    } catch (error) {
      console.error('Logout request failed:', error);
    } finally {
      // Clear local state regardless of API call success
      localStorage.removeItem('authToken');
      setToken(null);
      setUser(null);
      delete axios.defaults.headers.common['Authorization'];
      
      toast.success('Logged out successfully');
    }
  };

  // Update user profile
  const updateProfile = async (profileData) => {
    try {
      setLoading(true);
      const response = await axios.put(`${API_BASE_URL}/profile`, profileData);
      setUser(response.data);
      
      toast.success('Profile updated successfully!');
      return { success: true, user: response.data };
      
    } catch (error) {
      console.error('Profile update failed:', error);
      const message = error.response?.data?.detail || 'Profile update failed. Please try again.';
      toast.error(message);
      return { success: false, error: message };
    } finally {
      setLoading(false);
    }
  };

  // Refresh user data
  const refreshUser = async () => {
    if (!token) return;
    
    try {
      const response = await axios.get(`${API_BASE_URL}/profile`);
      setUser(response.data);
    } catch (error) {
      console.error('Failed to refresh user data:', error);
      if (error.response?.status === 401) {
        logout();
      }
    }
  };

  // Check if user has specific role
  const hasRole = (role) => {
    return user?.role === role;
  };

  // Check if user is admin
  const isAdmin = () => {
    return hasRole('admin');
  };

  // Context value
  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    updateProfile,
    refreshUser,
    hasRole,
    isAdmin,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
