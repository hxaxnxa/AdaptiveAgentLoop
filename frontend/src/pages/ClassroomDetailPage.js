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

  const handleDeleteCoursework = async (courseworkId, courseworkName) => {
    if (window.confirm(`Are you sure you want to delete "${courseworkName}"? This will delete all associated submissions.`)) {
      try {
        await apiClient.delete(`/api/coursework/${courseworkId}`);
        alert('Coursework deleted.');
        // Refresh the list
        setCourseworks(prev => prev.filter(cw => cw.id !== courseworkId));
      } catch (error) {
        console.error("Failed to delete coursework:", error);
        alert('Failed to delete: ' + error.response?.data?.detail);
      }
    }
  };

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
              
              {user?.role === 'student' ? (
                // STUDENT: Check if submission_id exists
                cw.submission_id ? (
                  <Link to={`/submission/${cw.submission_id}/result`} style={{ marginLeft: '10px' }}>
                    View Results
                  </Link>
                ) : (
                  // No submission, show the "take" link
                  cw.coursework_type === 'quiz' ? (
                    <Link to={`/quiz/${cw.id}/take`} style={{ marginLeft: '10px' }}>Take Quiz</Link>
                  ) : (
                    <Link to={`/assignment/${cw.id}/submit`} style={{ marginLeft: '10px' }}>Submit Assignment</Link>
                  )
                )
              ) : (
                // TEACHER: Show review and delete links
                <>
                  <Link to={`/coursework/${cw.id}/review`} style={{ marginLeft: '10px' }}>Review Submissions</Link>
                  <button
                    onClick={() => handleDeleteCoursework(cw.id, cw.name)}
                    style={{ marginLeft: '5px', color: 'red' }}
                  >
                    Delete
                  </button>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* This teacher-only section for classroom-wide actions is correct */}
      {user?.role === 'teacher' && (
        <div className="teacher-actions" style={{margin: '10px 0', borderTop: '1px solid #ccc', paddingTop: '10px'}}>
          <button onClick={() => navigate(`/classroom/${classroomId}/create-coursework`)}>
            Create Coursework
          </button>
          <button onClick={() => navigate(`/classroom/${classroomId}/students`)} style={{marginLeft: '10px'}}>
            Manage Students
          </button>
          <button onClick={() => navigate(`/classroom/${classroomId}/gradebook`)} style={{marginLeft: '10px'}}>
            View Gradebook
          </button>
          <button onClick={() => navigate(`/classroom/${classroomId}/analytics`)} style={{marginLeft: '10px'}}>
            View Analytics
          </button>
        </div>
      )}
    </div>
  );
};

export default ClassroomDetailPage;