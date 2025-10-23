import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import apiClient from '../api/apiClient';

const DashboardPage = () => {
  const { user, logout } = useAuth(); // Get user and logout
  const [classrooms, setClassrooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  // Fetch classrooms when the component mounts
  useEffect(() => {
    const fetchClassrooms = async () => {
      if (!user) return; // Don't fetch if user isn't loaded yet
      
      setLoading(true);
      try {
        const response = await apiClient.get('/api/classrooms/');
        setClassrooms(response.data);
      } catch (error) {
        console.error("Failed to fetch classrooms:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchClassrooms();
  }, [user]); // Rerun if the user object changes

  if (!user) {
    return <div>Loading...</div>;
  }

  const renderClassroomList = () => {
    if (loading) return <p>Loading classrooms...</p>;
    if (classrooms.length === 0) {
      return <p>You are not in any classrooms yet.</p>;
    }

    return (
      <ul>
        {classrooms.map((room) => (
          <li key={room.id}>
            <Link to={`/classroom/${room.id}`}>
              <strong>{room.name}</strong>
            </Link>
            {user.role === 'student' && <span> (Teacher: {room.owner.email})</span>}
            {user.role === 'teacher' && <span> (Invite Code: {room.invite_code})</span>}
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div>
      <h2>Dashboard</h2>
      <p>Welcome, <b>{user.email}</b> (logged in as {user.role})</p>
      <button onClick={logout}>Logout</button>
      
      <hr />
      
      <h3>Your Classrooms</h3>
      
      {/* Show the correct button based on user role */}
      {user.role === 'teacher' && (
        <button onClick={() => navigate('/create-classroom')}>Create New Classroom</button>
      )}
      {user.role === 'student' && (
        <button onClick={() => navigate('/join-classroom')}>Join a Classroom</button>
      )}
      
      {renderClassroomList()}
    </div>
  );
};

export default DashboardPage;