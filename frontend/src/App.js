import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import CreateClassroomPage from './pages/CreateClassroomPage';
import JoinClassroomPage from './pages/JoinClassroomPage';
import ClassroomDetailPage from './pages/ClassroomDetailPage';
import StudentManagementPage from './pages/StudentManagementPage';
import Navbar from './components/Navbar';
import './App.css';

// --- RENAMED IMPORTS ---
import CreateCourseworkPage from './pages/CreateCourseworkPage';
import QuizTakePage from './pages/QuizTakePage';
import EssaySubmitPage from './pages/EssaySubmitPage';
import SubmissionResultPage from './pages/SubmissionResultPage';

const PrivateRoute = ({ children }) => {
  const { token } = useAuth();
  return token ? children : <Navigate to="/login" />;
};

function App() {
  return (
    <div className="App">
      <Navbar />
      <div className="main-content">
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected Routes */}
          <Route path="/dashboard" element={<PrivateRoute><DashboardPage /></PrivateRoute>} />
          <Route path="/create-classroom" element={<PrivateRoute><CreateClassroomPage /></PrivateRoute>} />
          <Route path="/join-classroom" element={<PrivateRoute><JoinClassroomPage /></PrivateRoute>} />
          <Route path="/classroom/:classroomId" element={<PrivateRoute><ClassroomDetailPage /></PrivateRoute>} />
          <Route path="/classroom/:classroomId/students" element={<PrivateRoute><StudentManagementPage /></PrivateRoute>} />
          
          {/* --- UPDATED COURSEWORK ROUTES --- */}
          <Route 
            path="/classroom/:classroomId/create-coursework" 
            element={<PrivateRoute><CreateCourseworkPage /></PrivateRoute>} 
          />
          <Route 
            path="/quiz/:courseworkId/take" 
            element={<PrivateRoute><QuizTakePage /></PrivateRoute>} 
          />
          <Route 
            path="/assignment/:courseworkId/submit" 
            element={<PrivateRoute><EssaySubmitPage /></PrivateRoute>} 
          />
          <Route 
            path="/submission/:submissionId/result" 
            element={<PrivateRoute><SubmissionResultPage /></PrivateRoute>} 
          />
          
          {/* Default route */}
          <Route path="/" element={<Navigate to="/dashboard" />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;