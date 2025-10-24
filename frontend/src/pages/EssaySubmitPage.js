import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';

const EssaySubmitPage = () => {
  const { courseworkId } = useParams();
  const navigate = useNavigate();
  const [coursework, setCoursework] = useState(null);
  const [file, setFile] = useState(null); // For file upload
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCoursework = async () => {
      try {
        const response = await apiClient.get(`/api/coursework/${courseworkId}`);
        setCoursework(response.data);
      } catch (error) {
        const detail = error.response?.data?.detail;
        if (error.response?.status === 409) {
          const subId = error.response.headers['x-submission-id'];
          alert(detail + " Redirecting to your result.");
          navigate(`/submission/${subId}/result`);
        } else {
          setError(detail || "Failed to load coursework.");
        }
      } finally {
        setLoading(false);
      }
    };
    fetchCoursework();
  }, [courseworkId, navigate]);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      alert("Please select a file to upload.");
      return;
    }
    setLoading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await apiClient.post(
        `/api/coursework/${courseworkId}/submit-file`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );

      alert('Submission successful! Your assignment is being graded.');
      navigate(`/submission/${response.data.id}/result`);
    } catch (error) {
      console.error("Failed to submit essay:", error);
      alert('Submission failed: ' + error.response?.data?.detail);
      setLoading(false);
    }
  };

  if (loading) return <p>Loading...</p>;
  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>;
  if (!coursework) return <p>Coursework not found.</p>;

  return (
    <div>
      <h2>{coursework.name}</h2>

      <h3>Grading Rubric</h3>
      {coursework.rubric_file_url ? (
        <a href={coursework.rubric_file_url} target="_blank" rel="noopener noreferrer">
          View Rubric Document
        </a>
      ) : (
        <ul>
          {coursework.rubric?.map((r, i) => (
            <li key={i}>{r.criterion} ({r.max_points} pts)</li>
          ))}
        </ul>
      )}

      <hr />

      <form onSubmit={handleSubmit}>
        <div>
          <label>Upload your submission (.pdf, .docx, .txt):</label>
          <input
            type="file"
            accept=".pdf,.docx,.doc,.txt"
            onChange={handleFileChange}
            required
          />
        </div>
        <button type="submit" disabled={loading || !file}>
          {loading ? "Submitting..." : "Submit for Grading"}
        </button>
      </form>
    </div>
  );
};

export default EssaySubmitPage;
