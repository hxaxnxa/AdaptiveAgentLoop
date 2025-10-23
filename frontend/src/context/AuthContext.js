import React, { createContext, useState, useContext, useEffect } from 'react'; // Import useEffect
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';
import { jwtDecode } from 'jwt-decode'; // Import this

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null); // --- ADD THIS STATE ---
  const navigate = useNavigate();

  // --- ADD THIS EFFECT ---
  // This effect runs when the app loads to decode an existing token
  useEffect(() => {
    if (token) {
      try {
        const decodedToken = jwtDecode(token);
        // 'sub' is email, 'role' is role from our backend
        setUser({ email: decodedToken.sub, role: decodedToken.role });
      } catch (error) {
        console.error("Invalid token:", error);
        logout(); // Log out if token is bad
      }
    }
  }, [token]); // Reruns if the token changes

  const login = async (loginId, password, role) => {
    try {
      const response = await apiClient.post('/api/auth/login', {
        login_id: loginId,
        password,
        role,
      });
      
      const { access_token } = response.data;
      setToken(access_token);
      localStorage.setItem('token', access_token);
      // Decode the token immediately on login
      const decodedToken = jwtDecode(access_token);
      setUser({ email: decodedToken.sub, role: decodedToken.role });
      
      navigate('/dashboard');
    } catch (error) {
      console.error('Login failed:', error);
      throw new Error(error.response?.data?.detail || 'Login failed');
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null); // --- ADD THIS ---
    localStorage.removeItem('token');
    navigate('/login');
  };

  // --- UPDATE THE VALUE ---
  const value = {
    token,
    user, // Share the user object
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  return useContext(AuthContext);
};