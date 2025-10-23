import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import apiClient from '../api/apiClient';

// --- NEW: Helper Components ---

// Shows the student's quiz answers (Req #4)
const QuizResultDetail = ({ submission }) => {
  return (
    <div>
      <h3>Your Answers:</h3>
      {submission.answers.map((answer, index) => {
        const selectedId = answer.selected_option.id;
        const correctOption = answer.question.options.find(opt => opt.is_correct);
        const isCorrect = correctOption.id === selectedId;
        
        return (
          <div key={answer.id} style={{border: '1px solid #ddd', padding: '10px', margin: '10px 0'}}>
            <strong>Q{index+1}: {answer.question.question_text}</strong>
            <ul style={{listStyle: 'none'}}>
              {answer.question.options.map(opt => {
                let style = {};
                if (opt.id === selectedId && !isCorrect) {
                  style = {color: 'red', fontWeight: 'bold'}; // Incorrectly chosen
                } else if (opt.is_correct) {
                  style = {color: 'green', fontWeight: 'bold'}; // The correct answer
                }
                
                return (
                  <li key={opt.id} style={style}>
                    {opt.id === selectedId ? `(Your Answer) ` : ''}
                    {opt.is_correct ? `(Correct) ` : ''}
                    {opt.option_text}
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </div>
  );
};

// Shows the student's essay (Req #4)
const EssayResultDetail = ({ submission }) => {
  return (
    <div>
      <h3>Your Submission:</h3>
      <pre style={{backgroundColor: '#f4f4f4', padding: '10px', whiteSpace: 'pre-wrap'}}>
        {submission.submission_text}
      </pre>
    </div>
  );
};

// Shows the AI's rubric-based feedback
const AIFeedbackDisplay = ({ feedback }) => {
  return (
    <div>
      <h3>AI Feedback Breakdown:</h3>
      <table style={{width: '100%', borderCollapse: 'collapse'}}>
        <thead>
          <tr style={{backgroundColor: '#eee'}}>
            <th style={{border: '1px solid #ddd', padding: '8px'}}>Criterion</th>
            <th style={{border: '1px solid #ddd', padding: '8px'}}>Score</th>
            <th style={{border: '1px solid #ddd', padding: '8px'}}>Justification</th>
          </tr>
        </thead>
        <tbody>
          {feedback.map((item, index) => (
            <tr key={index}>
              <td style={{border: '1px solid #ddd', padding: '8px'}}>{item.criterion}</td>
              <td style={{border: '1px solid #ddd', padding: '8px'}}>{item.score}</td>
              <td style={{border: '1px solid #ddd', padding: '8px'}}>{item.justification}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// --- Main Page Component ---
const SubmissionResultPage = () => {
  const { submissionId } = useParams();
  const [submission, setSubmission] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchResult = async () => {
      try {
        const response = await apiClient.get(`/api/coursework/submissions/${submissionId}/result`);
        setSubmission(response.data);
        
        // Stop polling if grading is done or errored
        if (response.data.status !== 'SUBMITTED' && response.data.status !== 'GRADING') {
          setLoading(false);
          return true; // Stop
        }
      } catch (error) {
        console.error("Failed to fetch result:", error);
        setLoading(false);
        return true; // Stop
      }
      return false; // Keep polling
    };

    // Initial fetch
    fetchResult();
    
    // Poll for results
    const pollInterval = setInterval(async () => {
      const stopped = await fetchResult();
      if (stopped) {
        clearInterval(pollInterval);
      }
    }, 3000); // Check every 3 seconds

    return () => clearInterval(pollInterval);
  }, [submissionId]);

  if (loading) return <p>Loading submission status... (This may take a moment for AI grading)</p>;
  if (!submission) return <p>Could not load submission.</p>;

  const { coursework, status, score } = submission;
  const isGraded = status === 'PENDING_REVIEW' || status === 'GRADED';

  return (
    <div>
      <h2>Results for: {coursework.name}</h2>
      
      <p>
        <strong>Status:</strong> {status}
      </p>
      
      {isGraded && (
        <h3>
          Score: {Math.round(score * 100)}%
          {status === 'PENDING_REVIEW' && ' (Pending Teacher Review)'}
        </h3>
      )}
      
      <p>
        <strong>Submitted at:</strong> {new Date(submission.submitted_at).toLocaleString()}
      </p>
      
      <hr />
      
      {/* --- Req #4: Show the student's work --- */}
      {coursework.coursework_type === 'quiz' && submission.answers && (
        <QuizResultDetail submission={submission} />
      )}
      {coursework.coursework_type !== 'quiz' && submission.submission_text && (
        <EssayResultDetail submission={submission} />
      )}
      
      <hr />

      {/* --- Req #4: Show the AI feedback --- */}
      {isGraded && submission.ai_feedback && (
        <AIFeedbackDisplay feedback={submission.ai_feedback} />
      )}
      
      <Link to={`/classroom/${coursework.classroom_id}`}>Back to Classroom</Link>
    </div>
  );
};

export default SubmissionResultPage;