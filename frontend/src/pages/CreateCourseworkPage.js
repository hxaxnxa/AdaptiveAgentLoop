import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';

// --- NEW Rubric Sub-component ---
const RubricBuilder = ({ rubric, setRubric, onUploadSuccess }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [rawText, setRawText] = useState('');

  const handleRubricChange = (rIndex, field, value) => {
    const newRubric = [...rubric];
    newRubric[rIndex][field] = value;
    setRubric(newRubric);
  };
  
  const addRubricCriterion = () => {
    setRubric([...rubric, { criterion: '', max_points: 10 }]);
  };

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await apiClient.post('/api/coursework/upload-rubric', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setRawText(response.data.raw_text);
      onUploadSuccess(response.data.raw_text); // Pass text to AI parser
    } catch (error) {
      alert('File upload failed: ' + error.response?.data?.detail);
    }
    setUploading(false);
  };

  return (
    <div>
      <h3>Grading Rubric</h3>
      
      {/* --- NEW: Rubric Upload Feature --- */}
      <div>
        <label>Upload Rubric (.txt, .pdf):</label>
        <input type="file" accept=".txt,.pdf" onChange={handleFileChange} />
        <button type="button" onClick={handleUpload} disabled={uploading}>
          {uploading ? "Uploading..." : "Upload & Extract Text"}
        </button>
      </div>

      {rawText && (
        <div style={{marginTop: '10px'}}>
          <h4>Extracted Text (Review & Parse):</h4>
          <textarea 
            rows="5" 
            cols="80" 
            value={rawText} 
            onChange={(e) => setRawText(e.target.value)} 
          />
          <button type="button" onClick={onUploadSuccess} disabled={parsing}>
            {parsing ? "Parsing..." : "Parse with AI"}
          </button>
        </div>
      )}

      {/* --- Manual Rubric Builder --- */}
      {rubric.map((r, rIndex) => (
        <div key={rIndex} style={{ border: '1px solid #ccc', margin: '10px', padding: '10px' }}>
          <label>Criterion {rIndex + 1}:</label>
          <input
            type="text"
            placeholder="e.g., Clarity of Argument"
            value={r.criterion}
            onChange={(e) => handleRubricChange(rIndex, 'criterion', e.target.value)}
          />
          <label>Max Points:</label>
          <input
            type="number"
            value={r.max_points}
            onChange={(e) => handleRubricChange(rIndex, 'max_points', e.target.value)}
          />
        </div>
      ))}
      <button type="button" onClick={addRubricCriterion}>Add Criterion Manually</button>
    </div>
  );
};

// --- NEW Quiz Sub-component (for clarity) ---
const QuizBuilder = ({ questions, setQuestions }) => {
  
  const handleQuestionChange = (qIndex, value) => {
    const newQuestions = [...questions];
    newQuestions[qIndex].question_text = value;
    setQuestions(newQuestions);
  };
  const handleOptionChange = (qIndex, oIndex, value) => {
    const newQuestions = [...questions];
    newQuestions[qIndex].options[oIndex].option_text = value;
    setQuestions(newQuestions);
  };
  const handleCorrectChange = (qIndex, oIndex) => {
    const newQuestions = [...questions];
    newQuestions[qIndex].options.forEach((opt, idx) => opt.is_correct = (idx === oIndex));
    setQuestions(newQuestions);
  };
  const addOption = (qIndex) => {
    const newQuestions = [...questions];
    newQuestions[qIndex].options.push({ option_text: '', is_correct: false });
    setQuestions(newQuestions);
  };
  const addQuestion = () => {
    setQuestions([
      ...questions,
      { question_text: '', options: [{ option_text: '', is_correct: false }] }
    ]);
  };

  return (
    <div>
      <h3>Quiz Questions</h3>
      {questions.map((q, qIndex) => (
        <div key={qIndex} style={{ border: '1px solid #ccc', margin: '10px', padding: '10px' }}>
          <label>Question {qIndex + 1}:</label>
          <input type="text" value={q.question_text} onChange={(e) => handleQuestionChange(qIndex, e.target.value)} required />
          {q.options.map((opt, oIndex) => (
            <div key={oIndex} style={{ marginLeft: '20px' }}>
              <input type="text" placeholder={`Option ${oIndex + 1}`} value={opt.option_text} onChange={(e) => handleOptionChange(qIndex, oIndex, e.target.value)} required />
              <input type="radio" name={`correct_q_${qIndex}`} checked={opt.is_correct} onChange={() => handleCorrectChange(qIndex, oIndex)} />
              <label>Correct</label>
            </div>
          ))}
          <button type="button" onClick={() => addOption(qIndex)}>Add Option</button>
        </div>
      ))}
      <button type="button" onClick={addQuestion}>Add Question</button>
    </div>
  );
};


// --- Main Page Component ---
const CreateCourseworkPage = () => {
  const { classroomId } = useParams();
  const navigate = useNavigate();
  
  const [courseworkType, setCourseworkType] = useState('quiz');
  const [name, setName] = useState('');
  const [availableFrom, setAvailableFrom] = useState(new Date().toISOString().slice(0, 16));
  const [dueAt, setDueAt] = useState('');
  
  const [questions, setQuestions] = useState([
    { question_text: '', options: [{ option_text: '', is_correct: false }] }
  ]);
  const [rubric, setRubric] = useState([
    { criterion: '', max_points: 10 }
  ]);
  const [isParsing, setIsParsing] = useState(false);

  // --- NEW: AI Rubric Parsing ---
  const handleParseRubric = async (rawText) => {
    if (!rawText) return;
    setIsParsing(true);
    try {
      const response = await apiClient.post('/api/coursework/parse-rubric', { raw_text: rawText });
      setRubric(response.data.rubric); // Overwrite manual rubric with AI parsed one
    } catch (error) {
      alert('AI parsing failed: ' + error.response?.data?.detail);
    }
    setIsParsing(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    let payload = {
      name,
      coursework_type: courseworkType,
      available_from: new Date(availableFrom).toISOString(),
      due_at: dueAt ? new Date(dueAt).toISOString() : null,
    };
    
    if (courseworkType === 'quiz') {
      payload.questions = questions;
    } else {
      payload.rubric = rubric.map(r => ({ ...r, max_points: parseInt(r.max_points) || 0 }));
    }
    
    try {
      await apiClient.post(`/api/coursework/classrooms/${classroomId}`, payload);
      alert('Coursework created successfully!');
      navigate(`/classroom/${classroomId}`);
    } catch (error) {
      console.error("Failed to create coursework:", error);
      alert('Failed to create coursework: ' + error.response?.data?.detail);
    }
  };

  return (
    <div>
      <h2>Create New Coursework</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Coursework Type: </label>
          <select value={courseworkType} onChange={(e) => setCourseworkType(e.target.value)}>
            <option value="quiz">Quiz</option>
            <option value="assignment">Assignment</option>
            <option value="case_study">Case Study</option>
            <option value="essay">Essay</option>
          </select>
        </div>
        
        <div>
          <label>Name:</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        
        {/* --- NEW: Deadline Fields --- */}
        <div>
          <label>Available From:</label>
          <input type="datetime-local" value={availableFrom} onChange={(e) => setAvailableFrom(e.target.value)} required />
        </div>
        <div>
          <label>Due At:</label>
          <input type="datetime-local" value={dueAt} onChange={(e) => setDueAt(e.target.value)} />
        </div>
        
        {courseworkType === 'quiz' ? (
          <QuizBuilder questions={questions} setQuestions={setQuestions} />
        ) : (
          <RubricBuilder 
            rubric={rubric} 
            setRubric={setRubric} 
            onUploadSuccess={handleParseRubric}
            parsing={isParsing}
          />
        )}
        
        <hr />
        <button type="submit">Create Coursework</button>
        <button type="button" onClick={() => navigate(`/classroom/${classroomId}`)}>Cancel</button>
      </form>
    </div>
  );
};

export default CreateCourseworkPage;