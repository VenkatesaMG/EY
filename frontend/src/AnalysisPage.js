import React from 'react';
import { motion } from 'framer-motion';
import USMapAnalysis from './USMapAnalysis';
import './App.css';

const AnalysisPage = () => {
    return (
        <div className="analysis-page">
            <div style={{ marginBottom: '2rem' }}>
                <h2 style={{
                    fontSize: '1.75rem',
                    fontWeight: '700',
                    marginBottom: '0.5rem',
                    letterSpacing: '-0.02em'
                }}>
                    Geographic Analysis
                </h2>
                <p style={{ color: 'hsl(228, 8%, 55%)', fontSize: '1rem' }}>
                    Explore provider distribution and insights across US states with AI-powered analysis.
                </p>
            </div>
            <USMapAnalysis />
        </div>
    );
};

export default AnalysisPage;

