import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';

const StudentManagementPage = () => {
  const { classroomId } = useParams();
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchStudents = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get(`/api/classrooms/${classroomId}/students`);
      setStudents(response.data);
    } catch (error) {
      console.error("Failed to fetch students:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudents();
  }, [classroomId]);

  const handleRemoveStudent = async (studentId) => {
    if (window.confirm("Are you sure you want to remove this student from the class?")) {
      try {
        await apiClient.delete(`/api/classrooms/${classroomId}/students/${studentId}`);
        alert('Student removed.');
        // Refresh the list
        fetchStudents();
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