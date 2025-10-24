import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';

const CourseworkReviewPage = () => {
  const { courseworkId } = useParams();
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchSubmissions = async () => {
      try {
        const response = await apiClient.get(`/api/coursework/${courseworkId}/submissions`);
        setSubmissions(response.data);
      } catch (error) {
        console.error("Failed to fetch submissions:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchSubmissions();
  }, [courseworkId]);

  if (loading) return <p>Loading submissions...</p>;

  return (
    <div>
      <h2>Review Submissions</h2>
      <button onClick={() => navigate(`/classroom/${courseworkId}`)}>Back to Classroom</button>
      <table>
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
