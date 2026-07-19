import React from 'react';
import { useNavigate } from 'react-router-dom';

const LandingPage = () => {
  const navigate = useNavigate();

  return (
    <div className="page-container">
      <div style={{ textAlign: 'center', zIndex: 10 }}>
        <h1 
          className="animate-text-reveal" 
          style={{ 
            fontSize: '4rem', 
            fontWeight: 700,
            background: 'linear-gradient(to right, #fff, #a78bfa)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: '40px',
            textShadow: '0 0 40px rgba(167, 139, 250, 0.3)'
          }}
        >
          Hi ! I am Alaska<br/>let's be friends
        </h1>
        
        <button 
          onClick={() => navigate('/login')}
          className="btn-primary animate-float animate-fade-in"
          style={{ 
            animationDelay: '1s',
            padding: '16px 40px',
            fontSize: '1.2rem',
            borderRadius: '50px'
          }}
        >
          Get Started
        </button>
      </div>
      
      {/* Decorative background elements */}
      <div style={{
        position: 'absolute',
        top: '20%',
        left: '20%',
        width: '300px',
        height: '300px',
        background: 'rgba(124, 58, 237, 0.15)',
        filter: 'blur(80px)',
        borderRadius: '50%'
      }} />
      <div style={{
        position: 'absolute',
        bottom: '20%',
        right: '20%',
        width: '250px',
        height: '250px',
        background: 'rgba(56, 189, 248, 0.1)',
        filter: 'blur(60px)',
        borderRadius: '50%'
      }} />
    </div>
  );
};

export default LandingPage;
