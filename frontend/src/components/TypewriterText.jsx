import React, { useState, useEffect } from 'react';

const TypewriterText = ({ text, delay = 50, className = '', style = {} }) => {
  const [currentText, setCurrentText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (currentIndex < text.length) {
      const timeout = setTimeout(() => {
        setCurrentText(prevText => prevText + text[currentIndex]);
        setCurrentIndex(prevIndex => prevIndex + 1);
      }, delay);
      
      return () => clearTimeout(timeout);
    }
  }, [currentIndex, delay, text]);

  return (
    <span className={className} style={{ ...style, position: 'relative' }}>
      {currentText}
      {currentIndex < text.length && (
        <span 
          style={{
            borderRight: '2px solid var(--primary)',
            animation: 'blink 1s step-end infinite',
            marginLeft: '2px'
          }}
        />
      )}
      <style>{`
        @keyframes blink {
          50% { border-color: transparent; }
        }
      `}</style>
    </span>
  );
};

export default TypewriterText;
