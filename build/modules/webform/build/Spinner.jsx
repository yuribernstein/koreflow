import React from 'react';
import '../styles/Spinner.css';

const Spinner = ({ visible = false, overlay = true }) => {
  if (!visible) return null;

  return (
    <div className={`spinner-overlay ${overlay ? 'show-overlay' : ''}`}>
      <div className="spinner-container">
        <div className="spinner" />
      </div>
    </div>
  );
};

export default Spinner;
