import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';

const CreateClassroomPage = () => {
  const [name, setName] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await apiClient.post('/api/classrooms/', { name });
      alert(`Classroom created! Invite Code: ${response.data.invite_code}`);
      navigate('/dashboard'); // Go back to dashboard
    } catch (error) {
      console.error('Failed to create classroom:', error);
      alert('Failed to create classroom: ' + error.response.data.detail);
    }
  };

  return (
    <div>
      <h2>Create New Classroom</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Classroom Name:</label>
          <input 
            type="text" 
            value={name} 
            onChange={(e) => setName(e.target.value)} 
            required 
          />
        </div>
        <button type="submit">Create</button>
        <button type="button" onClick={() => navigate('/dashboard')}>Cancel</button>
      </form>
    </div>
  );
};

export default CreateClassroomPage;