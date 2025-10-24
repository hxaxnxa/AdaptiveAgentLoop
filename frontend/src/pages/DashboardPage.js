import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import apiClient from '../api/apiClient';
import { Bar } from 'react-chartjs-2'; 
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js'; 

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const DashboardPage = () => {
  const { user, logout } = useAuth();
  const [classrooms, setClassrooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [remedialQuizzes, setRemedialQuizzes] = useState([]);
  const navigate = useNavigate();
  const [dskgData, setDskgData] = useState(null);
  const [error, setError] = useState(null); // <-- 1. ADD ERROR STATE

  useEffect(() => {
    if (!user) return; 
    
    setError(null); // Clear errors on reload
    
    const fetchClassrooms = async () => {
      setLoading(true);
      try {
        const response = await apiClient.get('/api/classrooms/');
        setClassrooms(response.data);
      } catch (error) {
        console.error("Failed to fetch classrooms:", error);
        setError("Failed to load your classrooms."); 
      } finally {
        setLoading(false);
      }
    };

    fetchClassrooms();

    if (user.role === 'student') {
      const fetchRemedial = async () => {
        try {
          const response = await apiClient.get('/api/student/me/remedial');
          setRemedialQuizzes(response.data);
        } catch (error) {
          console.error("Failed to fetch remedial quizzes:", error);
          setError("Failed to load your recommended practice.");
        }
      };
      
      const fetchMyDSKG = async () => {
        try {
          const response = await apiClient.get('/api/student/me/dskg');
          const labels = response.data.map(n => n.concept);
          const scores = response.data.map(n => n.score * 100);
          
          setDskgData({
            labels,
            datasets: [{
              label: 'My Concept Mastery (%)',
              data: scores,
              backgroundColor: 'rgba(75, 192, 192, 0.6)',
            }]
          });
        } catch (error) {
          // --- 2. THIS IS THE FIX ---
          console.error("Failed to fetch DSKG data:", error);
          const errorMsg = error.response?.data?.detail || "Failed to load your knowledge profile.";
          setError(errorMsg); 
          // --- END OF FIX ---
        }
      };

      fetchRemedial();
      fetchMyDSKG();
    }
    
  }, [user]);

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

      {/* --- 3. DISPLAY THE ERROR --- */}
      {error && (
        <p style={{ color: 'red', border: '1px solid red', padding: '10px' }}>
          <strong>Error:</strong> {error}
        </p>
      )}
      
      <hr />
      
      {/* (Rest of the file is correct) */}
      {user.role === 'student' && remedialQuizzes.length > 0 && (
        <div className="remedial-section" style={{ border: '2px solid blue', padding: '10px', margin: '20px 0', borderRadius: '5px' }}>
          <h3>Recommended Practice</h3>
          {remedialQuizzes.map(quiz => (
            <div key={quiz.id}>
              <p>Practice quiz for: <strong>{quiz.concept}</strong></p>
              <Link to={`/remedial/${quiz.id}/take`}>
                <button>Start Practice</button> 
              </Link>
            </div>
          ))}
        </div>
      )}

      {user.role === 'student' && dskgData && (
        <div className="dskg-section" style={{ padding: '10px', margin: '20px 0' }}>
          <h3>My Knowledge Profile</h3>
          <div style={{ height: '300px' }}>
            <Bar data={dskgData} options={{ maintainAspectRatio: false, scales: { y: { beginAtZero: true, max: 100 } } }} />
          </div>
        </div>
      )}
      
      <h3>Your Classrooms</h3>
      
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