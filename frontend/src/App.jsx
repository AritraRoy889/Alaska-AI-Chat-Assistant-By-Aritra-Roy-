import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { SessionProvider } from './context/SessionContext';
import LandingPage from './pages/LandingPage';
import Login from './pages/Login';
import CreateAccount from './pages/CreateAccount';
import ChatInterface from './pages/ChatInterface';

function App() {
  return (
    <SessionProvider>
      <Router>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/create-account" element={<CreateAccount />} />
          <Route path="/chat" element={<ChatInterface />} />
        </Routes>
      </Router>
    </SessionProvider>
  );
}

export default App;
