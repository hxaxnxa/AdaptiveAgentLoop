import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import apiClient from '../api/apiClient';
import { Bar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js'; 

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const StudentProfilePage = () => {
  const { studentId } = useParams();
  // --- FIX 1: Rename state to hold the full profile object ---
  const [profileData, setProfileData] = useState(null); 
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDSKG = async () => {
      try {
        const response = await apiClient.get(`/api/student/${studentId}/dskg`);
        
        // --- FIX 2: Store the entire response object ---
        setProfileData(response.data); 
        
      } catch (error) {
        console.error("Failed to fetch DSKG data:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchDSKG();
  }, [studentId]);

  if (loading) return <p>Loading student knowledge graph...</p>;
  
  // --- FIX 3: Check the profileData object itself ---
  if (!profileData) return <p>No knowledge data found for this student.</p>;

  // --- FIX 4: Process the data *after* the loading checks ---
  const { student, dskg } = profileData;
  const chartData = {
    labels: dskg.map(n => n.concept), // Get concepts from the 'dskg' key
    datasets: [{
      label: 'Concept Mastery (%)',
      data: dskg.map(n => n.score * 100), // Get scores from the 'dskg' key
      backgroundColor: 'rgba(54, 162, 235, 0.6)',
    }]
  };

  return (
    <div>
      {/* --- FIX 5: Display the student's info from the 'student' key --- */}
      <h2>Student Knowledge Profile</h2>
      <p>
        <strong>Student:</strong> {student.email} <br />
        <strong>Enrollment #:</strong> {student.enrollment_number}
      </p>
      
      <div style={{ height: '400px' }}>
        {dskg.length > 0 ? (
          <Bar data={chartData} options={{ maintainAspectRatio: false, scales: { y: { beginAtZero: true, max: 100 } } }} />
        ) : (
          <p>No concepts have been graded for this student yet.</p>
        )}
      </div>
    </div>
  );
};

export default StudentProfilePage;