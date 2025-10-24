import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';
import { Bar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';

// Register Chart.js components (required, just like in your other chart pages)
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

/**
 * A sub-component to display the analytics for a single piece of coursework.
 * This keeps the main component clean.
 */
const AnalyticsCard = ({ data }) => {
  // Format the grade distribution data for the bar chart
  const chartData = {
    labels: ['A (90+)', 'B (80-89)', 'C (70-79)', 'D (60-69)', 'F (<60)'],
    datasets: [
      {
        label: '# of Students',
        data: [
          data.grade_distribution.A,
          data.grade_distribution.B,
          data.grade_distribution.C,
          data.grade_distribution.D,
          data.grade_distribution.F,
        ],
        backgroundColor: [
          'rgba(75, 192, 192, 0.6)',
          'rgba(54, 162, 235, 0.6)',
          'rgba(255, 206, 86, 0.6)',
          'rgba(255, 159, 64, 0.6)',
          'rgba(255, 99, 132, 0.6)',
        ],
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { display: false }, // Hide legend, labels are clear enough
      title: { display: true, text: 'Grade Distribution' },
    },
    scales: { 
      y: { 
        beginAtZero: true, 
        ticks: { 
          stepSize: 1 // Ensure Y-axis shows whole numbers for student counts
        } 
      } 
    }
  };

  return (
    <div style={{ border: '1px solid #ccc', borderRadius: '8px', padding: '16px', marginBottom: '20px' }}>
      <h3>{data.coursework_name}</h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        
        {/* Left Column: Statistics */}
        <div>
          <h4>Statistics</h4>
          <ul style={{ listStyle: 'none', paddingLeft: 0 }}>
            <li><strong>Submission Rate:</strong> {data.submission_rate}</li>
            <li>
              <strong>Class Average:</strong> 
              {data.class_average !== null ? ` ${(data.class_average * 100).toFixed(1)}%` : ' N/A'}
            </li>
            <li>
              <strong>Highest Score:</strong> 
              {data.highest_score !== null ? ` ${(data.highest_score * 100).toFixed(0)}%` : ' N/A'}
            </li>
            <li>
              <strong>Lowest Score:</strong> 
              {data.lowest_score !== null ? ` ${(data.lowest_score * 100).toFixed(0)}%` : ' N/A'}
            </li>
          </ul>
        </div>

        {/* Right Column: Chart */}
        <div style={{ height: '250px' }}>
          <Bar data={chartData} options={chartOptions} />
        </div>
      </div>
    </div>
  );
};

/**
 * The main page component that fetches and displays all analytics.
 */
const ClassAnalyticsPage = () => {
  const { classroomId } = useParams();
  const [analyticsData, setAnalyticsData] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const response = await apiClient.get(`/api/classrooms/${classroomId}/analytics`);
        setAnalyticsData(response.data);
      } catch (error) {
        console.error("Failed to fetch class analytics:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, [classroomId]);

  if (loading) return <p>Loading class analytics...</p>;

  return (
    <div>
      <button onClick={() => navigate(`/classroom/${classroomId}`)}>Back to Classroom</button>
      <h2>Classroom Analytics</h2>
      {analyticsData.length === 0 ? (
        <p>No analytics data available for this classroom yet.</p>
      ) : (
        analyticsData.map(data => (
          <AnalyticsCard key={data.coursework_id} data={data} />
        ))
      )}
    </div>
  );
};

export default ClassAnalyticsPage;