import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';

const JoinClassroomPage = () => {
  const [inviteCode, setInviteCode] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await apiClient.post('/api/classrooms/join', { invite_code: inviteCode });
      alert('Successfully joined classroom!');
      navigate('/dashboard'); // Go back to dashboard
    } catch (error) {
      console.error('Failed to join classroom:', error);
      alert('Failed to join classroom: ' + error.response.data.detail);
    }
  };

  return (
    <div>
      <h2>Join a Classroom</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Invite Code:</label>
          <input 
            type="text" 
            value={inviteCode} 
            onChange={(e) => setInviteCode(e.target.value)} 
            required 
          />
        </div>
        <button type="submit">Join</button>
        <button type="button" onClick={() => navigate('/dashboard')}>Cancel</button>
      </form>
    </div>
  );
};

export default JoinClassroomPage;