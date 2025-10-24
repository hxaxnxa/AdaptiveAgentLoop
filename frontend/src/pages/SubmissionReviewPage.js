import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';

// --- Helper Components from SubmissionResultPage ---
const QuizResultDetail = ({ submission, onOptionCorrectChange, editable }) => {
  return (
    <div>
      <h3>Quiz Answers</h3>
      {submission.answers.map((answer, index) => (
        <div
          key={answer.id}
          style={{
            border: '1px solid #ccc',
            padding: '10px',
            marginBottom: '10px',
            borderRadius: '5px',
          }}
        >
          <strong>
            Q{index + 1}: {answer.question.question_text}
          </strong>
          <ul style={{ listStyle: 'none', paddingLeft: 0 }}>
            {answer.question.options.map(opt => (
              <li key={opt.id} style={{ margin: '5px 0' }}>
                {editable ? (
                  <label>
                    <input
                      type="checkbox"
                      checked={opt.is_correct}
                      onChange={e => onOptionCorrectChange(answer.question.id, opt.id, e.target.checked)}
                    />
                    {opt.option_text}
                  </label>
                ) : (
                  <span>{opt.option_text} {opt.is_correct ? '(Correct)' : ''}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
};

const EssayResultDetail = ({ submission }) => (
  <div>
    <h3>Essay Submission</h3>
    {submission.submission_file_url && (
      <p>
        <a href={submission.submission_file_url} target="_blank" rel="noopener noreferrer">
          Download Submitted File
        </a>
      </p>
    )}
    <pre style={{ backgroundColor: '#f4f4f4', padding: '10px', whiteSpace: 'pre-wrap' }}>
      {submission.submission_text || "No text extracted."}
    </pre>
  </div>
);

const AIFeedbackDisplay = ({ feedback }) => (
  <div>
    <h3>AI Feedback</h3>
    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
      <thead>
        <tr style={{ backgroundColor: '#eee' }}>
          <th style={{ border: '1px solid #ddd', padding: '8px' }}>Criterion</th>
          <th style={{ border: '1px solid #ddd', padding: '8px' }}>Score</th>
          <th style={{ border: '1px solid #ddd', padding: '8px' }}>Justification</th>
        </tr>
      </thead>
      <tbody>
        {feedback.map((item, index) => (
          <tr key={index}>
            <td style={{ border: '1px solid #ddd', padding: '8px' }}>{item.criterion}</td>
            <td style={{ border: '1px solid #ddd', padding: '8px' }}>{item.score}</td>
            <td style={{ border: '1px solid #ddd', padding: '8px' }}>{item.justification}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

const SubmissionReviewPage = () => {
  const { submissionId } = useParams();
  const navigate = useNavigate();
  const [submission, setSubmission] = useState(null);
  const [loading, setLoading] = useState(true);

  const [overrideScore, setOverrideScore] = useState('');
  const [teacherFeedback, setTeacherFeedback] = useState('');

  // Fetch submission
  useEffect(() => {
    const fetchSubmission = async () => {
      try {
        const response = await apiClient.get(`/api/coursework/submissions/${submissionId}/result`);
        setSubmission(response.data);
        if (response.data.teacher_override_score !== null) {
          setOverrideScore(Math.round(response.data.teacher_override_score * 100));
        }
        if (response.data.teacher_feedback) {
          setTeacherFeedback(response.data.teacher_feedback);
        }
      } catch (error) {
        console.error("Failed to fetch submission:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchSubmission();
  }, [submissionId]);

  const handleApprove = async () => {
    const payload = {
      teacher_override_score: overrideScore === '' ? null : parseFloat(overrideScore) / 100,
      teacher_feedback: teacherFeedback,
    };
    try {
      await apiClient.patch(`/api/coursework/submissions/${submissionId}/approve`, payload);
      alert('Submission approved and published.');
      navigate(`/coursework/${submission.coursework.id}/review`);
    } catch (error) {
      alert('Approval failed: ' + error.response?.data?.detail);
    }
  };

  const handleCorrectOptionChange = async (questionId, optionId, newIsCorrect) => {
    
    // 1. Get the *current* state before we change it, so we can roll back on failure.
    const originalSubmission = submission;

    // 2. Update the UI *immediately* (optimistically)
    setSubmission(prevSubmission => {
      const newSubmission = { ...prevSubmission };
      newSubmission.answers = prevSubmission.answers.map(answer => {
        if (answer.question.id !== questionId) return answer;
        return {
          ...answer,
          question: {
            ...answer.question,
            options: answer.question.options.map(option => {
              if (option.id !== optionId) return option;
              return { ...option, is_correct: newIsCorrect };
            })
          }
        };
      });
      return newSubmission;
    });

    // 3. Now, try to sync this change with the backend
    try {
      // --- THIS IS THE FIX ---
      // We are sending NO body (the 2nd argument is null)
      // Instead, we pass the data as 'params' in the config object
      // axios will turn this into: ?is_correct=true
      await apiClient.patch(
        `/api/coursework/questions/${questionId}/options/${optionId}`,
        null, // No request body
        {
          params: { is_correct: newIsCorrect } // This creates the query parameter
        }
      );
      // --- END OF FIX ---

      // Success!
      alert('Option updated. Regrading has been triggered for all students.');

    } catch (error) {
      // --- FIX FOR [object Object] ALERT ---
      const errorMsg = error.response?.data?.detail || error.message || 'An unknown error occurred.';
      alert('Failed to update option: ' + errorMsg);
      // --- END OF FIX ---
      
      // 4. ROLLBACK: The API call failed. Revert the UI.
      setSubmission(originalSubmission);
    }
  };

  if (loading) return <p>Loading submission...</p>;
  if (!submission) return <p>Submission not found.</p>;

  return (
    <div>
      <h2>Review Submission</h2>
      <p>Student: {submission.student.email} ({submission.student.enrollment_number})</p>

      {submission.coursework.coursework_type === 'quiz' ? (
        <QuizResultDetail
          submission={submission}
          onOptionCorrectChange={handleCorrectOptionChange}
          editable={true}
        />
      ) : (
        <EssayResultDetail submission={submission} />
      )}

      {submission.ai_feedback && <AIFeedbackDisplay feedback={submission.ai_feedback} />}

      <hr />

      <h3>Teacher Review & Approval</h3>
      <div>
        <label>Override Score (%): </label>
        <input
          type="number"
          min="0"
          max="100"
          value={overrideScore}
          onChange={e => setOverrideScore(e.target.value)}
          placeholder={submission.score !== null ? `AI Score: ${Math.round(submission.score * 100)}%` : ''}
        />
      </div>
      <div>
        <label>Final Feedback/Comments:</label>
        <textarea
          rows="5"
          value={teacherFeedback}
          onChange={e => setTeacherFeedback(e.target.value)}
        />
      </div>

      <button onClick={handleApprove}>Approve & Publish Grade</button>
      <button onClick={() => navigate(`/coursework/${submission.coursework.id}/review`)}>Cancel</button>
    </div>
  );
};

export default SubmissionReviewPage;
