import React from 'react';
import { useAuth } from '../context/AuthContext';

const DashboardPage = () => {
  const { logout } = useAuth(); // Get logout function

  return (
    <div>
      <h2>Dashboard</h2>
      <p>Welcome to your A-LMS Dashboard!</p>
      {/* This button will log the user out and redirect them to login */}
      <button onClick={logout}>Logout</button>
    </div>
  );
};

export default DashboardPage;