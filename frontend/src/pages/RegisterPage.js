import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import apiClient from '../api/apiClient';

const RegisterPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('student');
  const [enrollmentNumber, setEnrollmentNumber] = useState(''); 
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const payload = {
      email,
      password,
      role,
      enrollment_number: role === 'student' ? enrollmentNumber : null,
    };

    try {
      const response = await apiClient.post('/api/auth/register', payload);
      alert(response.data.message); // Show the success message from backend
      navigate('/login');
    } catch (error) {
      console.error('Registration failed:', error);
      // --- UPDATE ERROR HANDLING ---
      setError(error.response?.data?.detail || 'Registration failed. Please try again.');
    }
  };

  return (
    <div>
      <h2>Register</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <form onSubmit={handleSubmit}>
        <div>
          <label>Email:</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div>
          <label>Password:</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <div>
          <label>Register as:</label>
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="student">Student</option>
            <option value="teacher">Teacher</option>
          </select>
        </div>

        {role === 'student' && (
          <div>
            <label>Enrollment Number:</label>
            <input 
              type="text" 
              value={enrollmentNumber} 
              onChange={(e) => setEnrollmentNumber(e.target.value)} 
              required 
            />
          </div>
        )}
        
        <button type="submit">Register</button>
      </form>
      <p>
        Already have an account? <Link to="/login">Login here</Link>
      </p>
    </div>
  );
};

export default RegisterPage;