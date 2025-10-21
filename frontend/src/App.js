import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  // 1. Create a state variable to hold the message from the backend
  const [message, setMessage] = useState('');

  // 2. useEffect hook runs after the component mounts
  useEffect(() => {
    // 3. Define the function to fetch data from the backend
    const fetchData = async () => {
      try {
        // 4. Use the fetch API to make a GET request to your backend's root URL
        const response = await fetch('http://localhost:8000/');
        
        // 5. Check if the response was successful
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }

        // 6. Parse the JSON data from the response
        const data = await response.json();
        
        // 7. Update the state with the message from the backend
        setMessage(data.message);
      } catch (error) {
        // 8. If there's an error (e.g., backend is down), set an error message
        console.error('Error fetching data:', error);
        setMessage('Could not connect to the backend.');
      }
    };

    // 9. Call the fetchData function
    fetchData();
  }, []); // The empty dependency array [] means this effect runs only once

  return (
    <div className="App">
      <header className="App-header">
        <h1>Welcome to the Agentic LMS</h1>
        <p>
          {/* 10. Display the message from the backend, or a loading text */}
          <strong>Message from Backend:</strong> {message || "Loading..."}
        </p>
      </header>
    </div>
  );
}

export default App;