import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';

const StudentManagementPage = () => {
  const { classroomId } = useParams();
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  // This function is now wrapped in useCallback
  const fetchStudents = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get(`/api/classrooms/${classroomId}/students`);
      setStudents(response.data);
    } catch (error) {
      console.error("Failed to fetch students:", error);
    } finally {
      setLoading(false);
    }
  }, [classroomId]); // It correctly depends on classroomId

  useEffect(() => {
    fetchStudents();
  }, [fetchStudents]); // <-- THIS IS THE FIX: Changed [classroomId] to [fetchStudents]

  const handleRemoveStudent = async (studentId) => {
    if (window.confirm("Are you sure you want to remove this student from the class?")) {
      try {
        await apiClient.delete(`/api/classrooms/${classroomId}/students/${studentId}`);
        alert('Student removed.');
        fetchStudents(); // Re-fetch students after removal
      } catch (error) {
        console.error("Failed to remove student:", error);
        alert('Could not remove student: ' + error.response?.data?.detail);
      }
    }
  };

  if (loading) return <p>Loading students...</p>;

  return (
    <div>
      <button onClick={() => navigate(`/classroom/${classroomId}`)}>Back to Classroom</button>
      <h2>Manage Students</h2>
      <table>
        <thead>
          <tr>
            <th>Enrollment Number</th>
            <th>Email</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {students.length === 0 ? (
            <tr>
              <td colSpan="3">No students enrolled.</td>
            </tr>
          ) : (
            students.map(student => (
              <tr key={student.id}>
                <td>{student.enrollment_number}</td>
                <td>{student.email}</td>
                <td>
                  <button 
                    onClick={() => navigate(`/student/${student.id}/profile`)} 
                    style={{ marginRight: '5px' }}
                  >
                    View Profile
                  </button>
                  <button onClick={() => handleRemoveStudent(student.id)} style={{color: 'red'}}>
                    Remove
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

export default StudentManagementPage;