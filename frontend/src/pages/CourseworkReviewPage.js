import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';

const CourseworkReviewPage = () => {
  const { courseworkId } = useParams();
  const [submissions, setSubmissions] = useState([]);
  const [coursework, setCoursework] = useState(null); // <-- ADD THIS STATE
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch submissions (as before)
        const subResponse = await apiClient.get(`/api/coursework/${courseworkId}/submissions`);
        setSubmissions(subResponse.data);

        // --- FIX: Fetch coursework data to get classroom_id ---
        const cwResponse = await apiClient.get(`/api/coursework/${courseworkId}/details`);
        setCoursework(cwResponse.data);
        
      } catch (error) {
        console.error("Failed to fetch data:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [courseworkId]);

  if (loading) return <p>Loading submissions...</p>;

  return (
    <div>
      <h2>Review Submissions for {coursework?.name}</h2>
      
      {/* --- FIX: Use coursework.classroom_id for navigation --- */}
      <button 
        onClick={() => navigate(`/classroom/${coursework.classroom_id}`)}
        disabled={!coursework}
      >
        Back to Classroom
      </button>
      
      <table>
        {/* ... (rest of your table is correct) ... */}
        <thead>
          <tr>
            <th>Enrollment #</th>
            <th>Student Email</th>
            <th>Status</th>
            <th>AI Score</th>
            <th>Submitted At</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {submissions.length === 0 ? (
            <tr>
              <td colSpan="6">No submissions yet.</td>
            </tr>
          ) : (
            submissions.map(sub => (
              <tr key={sub.id}>
                <td>{sub.student.enrollment_number}</td>
                <td>{sub.student.email}</td>
                <td>{sub.status}</td>
                <td>{sub.final_score !== null ? `${Math.round(sub.final_score * 100)}%` : 'N/A'}</td>
                <td>{new Date(sub.submitted_at).toLocaleString()}</td>
                <td>
                  <button
                    onClick={() => navigate(`/submission/${sub.id}/review`)}
                    disabled={sub.status === 'NOT_SUBMITTED'}
                  >
                    Review
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

export default CourseworkReviewPage;