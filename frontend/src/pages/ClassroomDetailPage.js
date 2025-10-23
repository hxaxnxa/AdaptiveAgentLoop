import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import apiClient from '../api/apiClient';

const ClassroomDetailPage = () => {
  const { classroomId } = useParams();
  const [courseworks, setCourseworks] = useState([]); // --- RENAMED ---
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchCourseworks = async () => {
      try {
        // --- UPDATED API PATH ---
        const response = await apiClient.get(`/api/coursework/classrooms/${classroomId}`);
        setCourseworks(response.data);
      } catch (error) {
        console.error("Failed to fetch coursework:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchCourseworks();
  }, [classroomId]);

  if (loading) return <p>Loading coursework...</p>;

  return (
    <div>
      <button onClick={() => navigate('/dashboard')}>Back to Dashboard</button>
      <h2>Classroom Details</h2>
      
      {user?.role === 'teacher' && (
        <div className="teacher-actions" style={{margin: '10px 0'}}>
          {/* --- UPDATED LINK --- */}
          <button onClick={() => navigate(`/classroom/${classroomId}/create-coursework`)}>
            Create New Coursework
          </button>
          <button onClick={() => navigate(`/classroom/${classroomId}/students`)} style={{marginLeft: '10px'}}>
            Manage Students
          </button>
        </div>
      )}
      
      <h3>Coursework</h3>
      {courseworks.length === 0 ? (
        <p>No coursework created yet.</p>
      ) : (
        <ul>
          {courseworks.map(cw => (
            <li key={cw.id}>
              <strong>{cw.name}</strong> ({cw.coursework_type})
              
              {/* --- UPDATED LINK LOGIC --- */}
              {user?.role === 'student' && (
                cw.coursework_type === 'quiz' ? (
                  <Link to={`/quiz/${cw.id}/take`}>Take Quiz</Link>
                ) : (
                  <Link to={`/assignment/${cw.id}/submit`}>Submit Assignment</Link>
                )
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default ClassroomDetailPage;