import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import apiClient from '../api/apiClient';

// --- Quiz Result Component ---
const QuizResultDetail = ({ submission }) => {
  return (
    <div>
      <h3>Your Answers:</h3>
      {submission.answers.map((answer, index) => {
        const selectedIds = new Set(answer.selected_option_ids);
        const correctIds = new Set(
          answer.question.options.filter(opt => opt.is_correct).map(opt => opt.id)
        );

        // Correct if selected matches exactly the correct options
        const isQCorrect =
          selectedIds.size === correctIds.size &&
          [...selectedIds].every(id => correctIds.has(id));

        return (
          <div
            key={answer.id}
            style={{
              border: `2px solid ${isQCorrect ? 'green' : 'red'}`,
              padding: '10px',
              margin: '10px 0',
              borderRadius: '5px',
            }}
          >
            <strong>
              Q{index + 1}: {answer.question.question_text}
            </strong>
            <ul style={{ listStyle: 'none', paddingLeft: 0 }}>
              {answer.question.options.map(opt => {
                const isSelected = selectedIds.has(opt.id);
                const isCorrect = correctIds.has(opt.id);
                let style = {};

                if (isSelected && isCorrect) style = { color: 'green', fontWeight: 'bold' };
                if (isSelected && !isCorrect) style = { color: 'red', fontWeight: 'bold' };
                if (!isSelected && isCorrect) style = { color: 'orange', fontWeight: 'bold' };

                return (
                  <li key={opt.id} style={style}>
                    {isSelected ? '[Your Answer] ' : ''}
                    {isCorrect ? '[Correct] ' : ''}
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

// --- Essay Result Component ---
const EssayResultDetail = ({ submission }) => (
  <div>
    <h3>Your Submission:</h3>
    {submission.submission_file_url && (
      <p>
        <a  // <--- HERE IS THE DOWNLOAD LINK
          href={submission.submission_file_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          Download Your Submitted File
        </a>
      </p>
    )}
    {/*
    <h4>Extracted Text:</h4>
    <pre
      style={{
        backgroundColor: '#f4f4f4',
        padding: '10px',
        whiteSpace: 'pre-wrap',
      }}
    >
      {submission.submission_text || 'No text extracted or text-only submission.'}
    </pre> */}
  </div>
);

// --- AI Feedback Component ---
const AIFeedbackDisplay = ({ feedback }) => (
  <div>
    <h3>AI Feedback Breakdown:</h3>
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

// --- Main Submission Result Page ---
const SubmissionResultPage = () => {
  const { submissionId } = useParams();
  const [submission, setSubmission] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchResult = async () => {
      try {
        const response = await apiClient.get(
          `/api/coursework/submissions/${submissionId}/result`
        );
        setSubmission(response.data);

        // Stop polling if grading is done or errored
        if (!['SUBMITTED', 'GRADING'].includes(response.data.status)) {
          setLoading(false);
          return true; // stop polling
        }
      } catch (error) {
        console.error('Failed to fetch result:', error);
        setLoading(false);
        return true;
      }
      return false; // keep polling
    };

    fetchResult();

    const pollInterval = setInterval(async () => {
      const stopped = await fetchResult();
      if (stopped) clearInterval(pollInterval);
    }, 3000);

    return () => clearInterval(pollInterval);
  }, [submissionId]);

  if (loading) return <p>Loading submission status... (This may take a moment for AI grading)</p>;
  if (!submission) return <p>Could not load submission.</p>;

  const { coursework, status } = submission;
  const isGraded = status === 'GRADED';
  const isPendingReview = status === 'PENDING_REVIEW';

  return (
    <div>
      <h2>Results for: {coursework.name}</h2>

      <p>
        <strong>Status:</strong> {status}
      </p>

      {isGraded && (
        <>
          <h3>
            {/* --- FIX #1: Use final_score --- */}
            Score: {Math.round(submission.final_score * 100)}%
          </h3>

          {/* --- FIX #2: Add Teacher Feedback --- */}
          {submission.teacher_feedback && (
            <div style={{border: '1px solid blue', padding: '10px', margin: '10px 0'}}>
              <strong>Teacher Feedback:</strong>
              <p>{submission.teacher_feedback}</p>
            </div>
          )}
        </>
      )}

      {isPendingReview && (
        <h3>Score: (Graded by AI, awaiting teacher review)</h3>
      )}
      <p>
        <strong>Submitted at:</strong> {new Date(submission.submitted_at).toLocaleString()}
      </p>

      <hr />

      {/* Show student's answers only if graded or pending review */}
      {(isGraded || isPendingReview) &&
        (coursework.coursework_type === 'quiz' && submission.answers ? (
          <QuizResultDetail submission={submission} />
        ) : (
          <EssayResultDetail submission={submission} />
        ))}

      <hr />

      {/* Show AI feedback only if graded */}
      {isGraded && submission.ai_feedback && <AIFeedbackDisplay feedback={submission.ai_feedback} />}

      <Link to={`/classroom/${coursework.classroom_id}`}>Back to Classroom</Link>
    </div>
  );
};

export default SubmissionResultPage;
