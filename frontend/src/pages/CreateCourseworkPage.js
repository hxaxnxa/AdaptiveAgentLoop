import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';

// --- Rubric Component ---
const RubricBuilder = ({ rubric, setRubric, onRubricUrlChange }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [fileName, setFileName] = useState('');

  const handleRubricChange = (rIndex, field, value) => {
    const newRubric = [...rubric];
    newRubric[rIndex][field] = value;
    setRubric(newRubric);
  };

  const addRubricCriterion = () => setRubric([...rubric, { criterion: '', max_points: 10 }]);
  const removeRubricCriterion = (rIndex) => setRubric(rubric.filter((_, i) => i !== rIndex));

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setFileName(e.target.files[0].name);
    onRubricUrlChange(null);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await apiClient.post('/api/coursework/upload-file', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      onRubricUrlChange(response.data.file_key);
      alert('Rubric file uploaded successfully.');
    } catch (error) {
      alert('File upload failed: ' + error.response?.data?.detail);
    }
    setUploading(false);
  };

  const handleRemoveFile = () => {
    setFile(null);
    setFileName('');
    onRubricUrlChange(null);
  };

  return (
    <div>
      <h3>Grading Rubric (Upload File)</h3>
      <input type="file" accept=".txt,.pdf,.docx" onChange={handleFileChange} />
      <button type="button" onClick={handleUpload} disabled={uploading || !file}>
        {uploading ? "Uploading..." : "Upload File"}
      </button>
      {fileName && (
        <span>{fileName} <button type="button" onClick={handleRemoveFile}>X</button></span>
      )}

      <h3>Grading Rubric (Manual)</h3>
      {rubric.map((r, rIndex) => (
        <div key={rIndex}>
          <input type="text" placeholder="Criterion" value={r.criterion} onChange={e => handleRubricChange(rIndex, 'criterion', e.target.value)} />
          <input type="number" placeholder="Points" value={r.max_points} onChange={e => handleRubricChange(rIndex, 'max_points', e.target.value)} />
          <button type="button" onClick={() => removeRubricCriterion(rIndex)}>Remove Criterion</button>
        </div>
      ))}
      <button type="button" onClick={addRubricCriterion}>Add Criterion</button>
    </div>
  );
};

// --- Quiz Component ---
const QuizBuilder = ({ questions, setQuestions, materialUrls }) => {
  const [aiTopic, setAiTopic] = useState('');
  const [aiNum, setAiNum] = useState(5);
  const [aiDifficulty, setAiDifficulty] = useState('Medium');
  const [isGenerating, setIsGenerating] = useState(false);

  const handleQuestionChange = (qIndex, field, value) => {
    const newQ = [...questions];
    newQ[qIndex][field] = value;
    setQuestions(newQ);
  };

  const handleOptionChange = (qIndex, oIndex, field, value) => {
    const newQ = [...questions];
    newQ[qIndex].options[oIndex][field] = value;
    setQuestions(newQ);
  };

  const addOption = (qIndex) => {
    const newQ = [...questions];
    newQ[qIndex].options.push({ option_text: '', is_correct: false });
    setQuestions(newQ);
  };

  const removeOption = (qIndex, oIndex) => {
    const newQ = [...questions];
    newQ[qIndex].options = newQ[qIndex].options.filter((_, i) => i !== oIndex);
    setQuestions(newQ);
  };

  const addQuestion = () => {
    setQuestions([...questions, { question_text: '', question_type: 'multiple_choice', score: 1, options: [{ option_text: '', is_correct: false }] }]);
  };

  const removeQuestion = (qIndex) => setQuestions(questions.filter((_, i) => i !== qIndex));

  const handleAIGenerate = async () => {
    if (!materialUrls || materialUrls.length === 0) {
      alert("Please upload material files first.");
      return;
    }
    setIsGenerating(true);
    try {
      const response = await apiClient.post('/api/coursework/generate-quiz-from-files', {
        material_file_urls: materialUrls,
        topic: aiTopic,
        num_questions: parseInt(aiNum),
        difficulty: aiDifficulty
      });
      setQuestions([...questions, ...response.data.questions]);
    } catch (error) {
      alert('AI generation failed: ' + error.response?.data?.detail);
    }
    setIsGenerating(false);
  };

  return (
    <div>
      <h3>AI Quiz Generator</h3>
      <input type="text" placeholder="Topic (optional)" value={aiTopic} onChange={e => setAiTopic(e.target.value)} />
      <input type="number" value={aiNum} onChange={e => setAiNum(e.target.value)} />
      <select value={aiDifficulty} onChange={e => setAiDifficulty(e.target.value)}>
        <option value="Easy">Easy</option>
        <option value="Medium">Medium</option>
        <option value="Hard">Hard</option>
      </select>
      <button type="button" onClick={handleAIGenerate} disabled={isGenerating}>
        {isGenerating ? "Generating..." : "Generate & Add Questions"}
      </button>

      <h3>Quiz Questions (Manual)</h3>
      {questions.map((q, qIndex) => (
        <div key={qIndex} style={{ border: '1px solid #ccc', margin: '10px', padding: '10px' }}>
          <input type="text" value={q.question_text} onChange={e => handleQuestionChange(qIndex, 'question_text', e.target.value)} />
          <input type="number" value={q.score} onChange={e => handleQuestionChange(qIndex, 'score', e.target.value)} />
          <select value={q.question_type} onChange={e => handleQuestionChange(qIndex, 'question_type', e.target.value)}>
            <option value="multiple_choice">Multiple Choice</option>
            <option value="multiple_response">Multiple Response</option>
          </select>
          <button type="button" onClick={() => removeQuestion(qIndex)}>Remove Question</button>

          {q.options.map((opt, oIndex) => (
            <div key={oIndex} style={{ marginLeft: '20px' }}>
              <input type="text" placeholder={`Option ${oIndex + 1}`} value={opt.option_text} onChange={e => handleOptionChange(qIndex, oIndex, 'option_text', e.target.value)} />
              <input type="checkbox" checked={opt.is_correct} onChange={e => handleOptionChange(qIndex, oIndex, 'is_correct', e.target.checked)} />
              <label>Correct</label>
              <button type="button" onClick={() => removeOption(qIndex, oIndex)}>X</button>
            </div>
          ))}
          <button type="button" onClick={() => addOption(qIndex)}>Add Option</button>
        </div>
      ))}
      <button type="button" onClick={addQuestion}>Add Manual Question</button>
    </div>
  );
};

// --- Main Page ---
const CreateCourseworkPage = () => {
  const { classroomId } = useParams();
  const navigate = useNavigate();

  const [courseworkType, setCourseworkType] = useState('quiz');
  const [name, setName] = useState('');
  const [availableFrom, setAvailableFrom] = useState(new Date().toISOString().slice(0, 16));
  const [dueAt, setDueAt] = useState('');
  const [materialFiles, setMaterialFiles] = useState([]);
  const [materialUrls, setMaterialUrls] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [rubric, setRubric] = useState([]);
  const [rubricFileUrl, setRubricFileUrl] = useState(null);
  const [uploadingMaterials, setUploadingMaterials] = useState(false);

  const handleMaterialFilesChange = (e) => setMaterialFiles([...e.target.files]);

  const handleUploadMaterials = async () => {
    if (!materialFiles || materialFiles.length === 0) return;
    setUploadingMaterials(true);
    const urls = [];
    try {
      for (let f of materialFiles) {
        const formData = new FormData();
        formData.append('file', f);
        const response = await apiClient.post('/api/coursework/upload-file', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        urls.push(response.data.file_key);
      }
      setMaterialUrls(urls);
      alert('Material files uploaded successfully.');
    } catch (error) {
      alert('Material file upload failed: ' + error.response?.data?.detail);
    }
    setUploadingMaterials(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    let payload = {
      name,
      coursework_type: courseworkType,
      available_from: new Date(availableFrom).toISOString(),
      due_at: dueAt ? new Date(dueAt).toISOString() : null,
      material_file_urls: materialUrls,
    };

    if (courseworkType === 'quiz') {
      payload.questions = questions;
    } else {
      payload.rubric = rubric.length > 0 ? rubric.map(r => ({ ...r, max_points: parseInt(r.max_points) || 0 })) : null;
      payload.rubric_file_url = rubricFileUrl;
      if (!payload.rubric && !payload.rubric_file_url) {
        alert("Please create or upload a rubric for this assignment type.");
        return;
      }
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
        <select value={courseworkType} onChange={(e) => setCourseworkType(e.target.value)}>
          <option value="quiz">Quiz</option>
          <option value="assignment">Assignment (File Upload)</option>
          <option value="case_study">Case Study (File Upload)</option>
          <option value="essay">Essay (File Upload)</option>
        </select>
        <input type="text" placeholder="Coursework Name" value={name} onChange={(e) => setName(e.target.value)} required />
        <label>Available From:</label>
        <input type="datetime-local" value={availableFrom} onChange={(e) => setAvailableFrom(e.target.value)} required />
        <label>Due At:</label>
        <input type="datetime-local" value={dueAt} onChange={(e) => setDueAt(e.target.value)} />

        {courseworkType === 'quiz' ? (
          <div>
            <h3>Material Files (Optional for AI Quiz Generation)</h3>
            <input type="file" multiple onChange={handleMaterialFilesChange} />
            <button type="button" onClick={handleUploadMaterials} disabled={uploadingMaterials}>
              {uploadingMaterials ? "Uploading..." : "Upload Materials"}
            </button>
            <QuizBuilder questions={questions} setQuestions={setQuestions} materialUrls={materialUrls} />
          </div>
        ) : (
          <RubricBuilder rubric={rubric} setRubric={setRubric} onRubricUrlChange={setRubricFileUrl} />
        )}

        <hr />
        <button type="submit">Create Coursework</button>
      </form>
    </div>
  );
};

export default CreateCourseworkPage;
