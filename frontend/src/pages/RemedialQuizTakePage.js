import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';

const RemedialQuizTakePage = () => {
  const { quizId } = useParams();
  const navigate = useNavigate();
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Note: The M6 guide's API fetches a *list*. We'll assume the first one.
    // A better API would be GET /api/student/remedial/{quizId}
    const fetchQuiz = async () => {
      try {
        const response = await apiClient.get('/api/student/me/remedial');
        const currentQuiz = response.data.find(q => q.id === parseInt(quizId));
        if (currentQuiz) {
          setQuiz(currentQuiz);
        } else {
          throw new Error("Quiz not found or already completed.");
        }
      } catch (error) {
        alert(error.message);
        navigate('/dashboard');
      } finally {
        setLoading(false);
      }
    };
    fetchQuiz();
  }, [quizId, navigate]);

  const handleOptionSelect = (questionId, optionId) => {
    setAnswers(prev => ({ ...prev, [questionId]: optionId }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = {
      answers: Object.keys(answers).map(qId => ({
        question_id: parseInt(qId),
        selected_option_id: answers[qId],
      })),
    };

    try {
      const response = await apiClient.post(`/api/student/remedial/${quizId}/submit`, payload);
      alert(`Practice Complete! You got ${response.data.correct}/${response.data.total}.`);
      navigate('/dashboard');
    } catch (error) {
      alert('Failed to submit: ' + error.response?.data?.detail);
    }
  };

  if (loading) return <p>Loading practice quiz...</p>;
  if (!quiz) return <p>Quiz not found.</p>;

  return (
    <div>
      <h2>Practice for: {quiz.concept}</h2>
      <form onSubmit={handleSubmit}>
        {quiz.questions.map((q) => (
          <div key={q.id} style={{ marginBottom: '20px' }}>
            <strong>{q.question_text}</strong>
            {q.options.map((opt) => (
              <div key={opt.id}>
                <input
                  type="radio"
                  name={`question_${q.id}`}
                  checked={answers[q.id] === opt.id}
                  onChange={() => handleOptionSelect(q.id, opt.id)}
                />
                <label>{opt.option_text}</label>
              </div>
            ))}
          </div>
        ))}
        <button type="submit">Submit Practice</button>
      </form>
    </div>
  );
};

export default RemedialQuizTakePage;