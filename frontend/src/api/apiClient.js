import axios from 'axios';

// Create an axios instance with a predefined base URL
const apiClient = axios.create({
  baseURL: 'http://localhost:8000', // Your FastAPI backend URL
  headers: {
    'Content-Type': 'application/json',
  },
});

export default apiClient;