import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';

const EssaySubmitPage = () => {
  const { courseworkId } = useParams(); // --- RENAMED ---
  const navigate = useNavigate();
  const [coursework, setCoursework] = useState(null); // --- ADDED ---
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null); // --- ADDED ---

  // --- ADDED: Fetch coursework to show rubric ---
  useEffect(() => {
    const fetchCoursework = async () => {
      try {
        const response = await apiClient.get(`/api/coursework/${courseworkId}`);
        setCoursework(response.data);
      } catch (error) {
        console.error("Failed to fetch coursework:", error);
        setError(error.response?.data?.detail || "Failed to load coursework.");
      } finally {
        setLoading(false);
      }
    };
    fetchCoursework();
  }, [courseworkId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = { submission_text: content }; // --- RENAMED ---
      // --- RENAMED API ---
      const response = await apiClient.post(`/api/coursework/${courseworkId}/submit-essay`, payload);
      alert('Submission successful! Your assignment is now being graded by the AI.');
      navigate(`/submission/${response.data.id}/result`);
    } catch (error) {
      console.error("Failed to submit essay:", error);
      alert('Submission failed: ' + error.response?.data?.detail);
      setLoading(false);
    }
  };
  
  if (loading) return <p>Loading...</p>;
  if (error) return <p style={{color: 'red'}}>Error: {error}</p>;
  if (!coursework) return <p>Coursework not found.</p>;

  return (
    <div>
      <h2>{coursework.name}</h2>
      
      {/* --- ADDED: Display Rubric --- */}
      <h3>Grading Rubric</h3>
      <ul>
        {coursework.rubric.map((r, i) => (
          <li key={i}>{r.criterion} ({r.max_points} points)</li>
        ))}
      </ul>
      
      <hr />
      
      <form onSubmit={handleSubmit}>
        <div>
          <label>Your Submission:</label>
          <textarea
            rows="20" cols="80"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            required
            placeholder="Type or paste your submission here..."
          />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? "Submitting..." : "Submit for Grading"}
        </button>
      </form>
    </div>
  );
};

export default EssaySubmitPage;