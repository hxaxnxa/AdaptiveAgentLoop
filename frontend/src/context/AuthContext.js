import React, { createContext, useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';

// 1. Create the context
const AuthContext = createContext(null);

// 2. Create the provider component
export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const navigate = useNavigate();

  // 3. Login function
  const login = async (email, password, role) => {
    try {
      const response = await apiClient.post('/api/auth/login', {
        email,
        password,
        role,
      });
      
      const { access_token } = response.data;
      setToken(access_token);
      localStorage.setItem('token', access_token); // Persist token in browser
      navigate('/dashboard'); // Redirect to dashboard on success
    } catch (error) {
      console.error('Login failed:', error);
      alert('Login failed: ' + error.response.data.detail);
    }
  };

  // 4. Logout function
  const logout = () => {
    setToken(null);
    localStorage.removeItem('token');
    navigate('/login');
  };

  // 5. Value to be passed to consuming components
  const value = {
    token,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// 6. Custom hook to easily use the context
export const useAuth = () => {
  return useContext(AuthContext);
};