import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';

const QuizTakePage = () => {
  const { courseworkId } = useParams(); // --- RENAMED ---
  const navigate = useNavigate();
  const [coursework, setCoursework] = useState(null); // --- RENAMED ---
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null); // --- ADDED ---

  useEffect(() => {
    const fetchQuiz = async () => {
      try {
        // --- RENAMED API ---
        const response = await apiClient.get(`/api/coursework/${courseworkId}`);
        setCoursework(response.data);
      } catch (error) {
        console.error("Failed to fetch quiz:", error);
        setError(error.response?.data?.detail || "Failed to load quiz.");
      } finally {
        setLoading(false);
      }
    };
    fetchQuiz();
  }, [courseworkId]);

  const handleOptionSelect = (questionId, optionId) => {
    setAnswers({ ...answers, [questionId]: optionId });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = {
      answers: Object.keys(answers).map(qId => ({
        question_id: parseInt(qId),
        selected_option_id: answers[qId],
      })),
    };
    
    if (payload.answers.length !== coursework.questions.length) {
      alert("Please answer all questions.");
      return;
    }

    try {
      // --- RENAMED API ---
      const response = await apiClient.post(`/api/coursework/${courseworkId}/submit-quiz`, payload);
      alert('Submission successful! Your quiz is being graded.');
      navigate(`/submission/${response.data.id}/result`);
    } catch (error) {
      console.error("Failed to submit quiz:", error);
      alert('Failed to submit: ' + error.response?.data?.detail);
    }
  };
  
  // --- ADDED: Error and loading states ---
  if (loading) return <p>Loading quiz...</p>;
  if (error) return <p style={{color: 'red'}}>Error: {error}</p>;
  if (!coursework) return <p>Quiz not found.</p>;

  return (
    <div>
      <h2>{coursework.name}</h2>
      <form onSubmit={handleSubmit}>
        {coursework.questions.map((q) => (
          <div key={q.id} style={{ margin: '15px' }}>
            <strong>{q.question_text}</strong>
            {q.options.map((opt) => (
              <div key={opt.id}>
                <input type="radio" name={`question_${q.id}`} value={opt.id}
                  onChange={() => handleOptionSelect(q.id, opt.id)} required />
                <label>{opt.option_text}</label>
              </div>
            ))}
          </div>
        ))}
        <button type="submit">Submit Quiz</button>
      </form>
    </div>
  );
};

export default QuizTakePage;