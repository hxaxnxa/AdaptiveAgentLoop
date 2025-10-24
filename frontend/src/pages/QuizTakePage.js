import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';

const QuizTakePage = () => {
  const { courseworkId } = useParams(); // Quiz/coursework ID from URL
  const navigate = useNavigate();
  const [coursework, setCoursework] = useState(null);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchQuiz = async () => {
      try {
        const response = await apiClient.get(`/api/coursework/${courseworkId}`);
        setCoursework(response.data);
      } catch (error) {
        console.error("Failed to fetch quiz:", error);
        const detail = error.response?.data?.detail;
        if (error.response?.status === 409) {
          // Already submitted
          const subId = error.response.headers['x-submission-id'];
          alert(detail + " Redirecting to your result.");
          navigate(`/submission/${subId}/result`);
        } else {
          setError(detail || "Failed to load quiz.");
        }
      } finally {
        setLoading(false);
      }
    };
    fetchQuiz();
  }, [courseworkId, navigate]);

  const handleOptionSelect = (questionId, optionId, questionType) => {
    setAnswers(prev => {
      const newAnswers = { ...prev };
      const currentSelections = prev[questionId] || [];

      if (questionType === 'multiple_choice') {
        // Single selection for radio buttons
        newAnswers[questionId] = [optionId];
      } else if (questionType === 'multiple_response') {
        // Toggle selection for checkboxes
        if (currentSelections.includes(optionId)) {
          newAnswers[questionId] = currentSelections.filter(id => id !== optionId);
        } else {
          newAnswers[questionId] = [...currentSelections, optionId];
        }
      }

      return newAnswers;
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const payload = {
      answers: Object.keys(answers).map(qId => ({
        question_id: parseInt(qId),
        selected_option_ids: answers[qId],
      })),
    };

    // Ensure all questions answered
    if (payload.answers.length !== coursework.questions.length) {
      alert("Please answer all questions.");
      return;
    }

    try {
      const response = await apiClient.post(`/api/coursework/${courseworkId}/submit-quiz`, payload);
      alert('Submission successful! Your quiz is being graded.');
      navigate(`/submission/${response.data.id}/result`);
    } catch (error) {
      console.error("Failed to submit quiz:", error);
      alert('Failed to submit: ' + error.response?.data?.detail);
    }
  };

  if (loading) return <p>Loading quiz...</p>;
  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>;
  if (!coursework) return <p>Quiz not found.</p>;

  return (
    <div>
      <h2>{coursework.name}</h2>
      <form onSubmit={handleSubmit}>
        {coursework.questions.map((q) => (
          <div key={q.id} style={{ marginBottom: '20px' }}>
            <strong>{q.question_text} ({q.score} pts)</strong>
            <p>{q.question_type === 'multiple_response' ? '(Select all that apply)' : '(Select one)'}</p>
            {q.options.map((opt) => (
              <div key={opt.id}>
                <input
                  type={q.question_type === 'multiple_choice' ? 'radio' : 'checkbox'}
                  name={`question_${q.id}`} // Radio buttons need same name per question
                  checked={(answers[q.id] || []).includes(opt.id)}
                  onChange={() => handleOptionSelect(q.id, opt.id, q.question_type)}
                />
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
