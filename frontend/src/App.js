import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import './App.css';

// This is a component to protect our routes
const PrivateRoute = ({ children }) => {
  const { token } = useAuth();
  // If there's no token, redirect to the login page
  return token ? children : <Navigate to="/login" />;
};

function App() {
  return (
    <div className="App">
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Protected Routes */}
        <Route 
          path="/dashboard" 
          element={
            <PrivateRoute>
              <DashboardPage />
            </PrivateRoute>
          } 
        />

        {/* Default route */}
        {/* If user is at "/", redirect to dashboard if logged in, else to login */}
        <Route path="/" element={<Navigate to="/dashboard" />} />
      </Routes>
    </div>
  );
}

export default App;