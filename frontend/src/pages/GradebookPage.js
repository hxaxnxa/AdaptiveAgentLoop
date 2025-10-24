import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';

const GradebookPage = () => {
  const { classroomId } = useParams();
  const [gradebook, setGradebook] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchGradebook = async () => {
      try {
        const response = await apiClient.get(`/api/classrooms/${classroomId}/gradebook`);
        setGradebook(response.data);
      } catch (error) {
        console.error("Failed to fetch gradebook:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchGradebook();
  }, [classroomId]);

  const exportToCSV = () => {
    if (!gradebook) return;

    let csvContent = "data:text/csv;charset=utf-8,";
    
    // Header Row
    const headers = ["Enrollment #", "Student Email", ...gradebook.courseworks.map(cw => cw.name)];
    csvContent += headers.join(",") + "\r\n";

    // Student Rows
    gradebook.students.forEach(row => {
      const studentData = [
        row.student.enrollment_number,
        row.student.email,
        ...gradebook.courseworks.map(cw => {
          const score = row.scores[cw.id]?.final_score;
          return score !== null && score !== undefined ? Math.round(score * 100) : "";
        })
      ];
      csvContent += studentData.join(",") + "\r\n";
    });

    // Create and click download link
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `gradebook_classroom_${classroomId}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) return <p>Loading gradebook...</p>;
  if (!gradebook) return <p>No gradebook data found.</p>;

  return (
    <div>
      <h2>Gradebook</h2>
      <button onClick={() => navigate(`/classroom/${classroomId}`)}>Back to Classroom</button>
      <button onClick={exportToCSV} style={{ marginLeft: '10px' }}>Export to CSV</button>
      
      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '20px' }}>
        <thead>
          <tr>
            <th style={{ border: '1px solid #ddd', padding: '8px' }}>Student</th>
            {gradebook.courseworks.map(cw => (
              <th key={cw.id} style={{ border: '1px solid #ddd', padding: '8px' }}>
                {cw.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {gradebook.students.map(row => (
            <tr key={row.student.id}>
              <td style={{ border: '1px solid #ddd', padding: '8px' }}>
                {row.student.enrollment_number} - {row.student.email}
              </td>
              {gradebook.courseworks.map(cw => {
                const score = row.scores[cw.id]?.final_score;
                return (
                  <td key={cw.id} style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'center' }}>
                    {score !== null && score !== undefined ? `${Math.round(score * 100)}%` : 'N/A'}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default GradebookPage;