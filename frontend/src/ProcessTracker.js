import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    CheckCircle,
    Loader2,
    AlertCircle,
    Search,
    Database,
    Globe,
    Sparkles,
    ArrowRight,
    ShieldCheck
} from 'lucide-react';
import USMapAnalysis from './USMapAnalysis';
import './DeploymentTracker.css';

const Steps = [
    { key: 'submitted', label: 'Submission Received', description: 'Data received and queued', icon: Database },
    { key: 'npi_lookup', label: 'NPI Registry Check', description: 'Validating against NPI database', icon: Search },
    { key: 'ai_validation', label: 'AI Validation', description: 'Gemini-powered data verification', icon: Sparkles },
    { key: 'enrichment', label: 'Data Enrichment', description: 'Enhancing with external sources', icon: Globe },
    { key: 'final_review', label: 'Final Review', description: 'Quality assurance and approval', icon: ShieldCheck, alwaysGreen: true },
];

const ProcessTracker = ({ submissionId, onComplete, demoMode = true }) => {
    const [status, setStatus] = useState(null);
    const [polling, setPolling] = useState(true);
    const [completedSteps, setCompletedSteps] = useState([]);

    useEffect(() => {
        if (!submissionId) return;

        const poll = setInterval(async () => {
            try {
                const res = await fetch(`http://localhost:8000/submissions/${submissionId}`);
                const data = await res.json();
                setStatus(data);

                // Track completed steps for animation
                if (data.steps) {
                    const completed = Object.entries(data.steps)
                        .filter(([_, value]) => value === 'completed')
                        .map(([key]) => key);
                    setCompletedSteps(completed);
                }

                // Check if processing is complete
                const terminalStatuses = ['processed', 'enriched', 'failed', 'failed_validation', 'rejected_invalid_npi'];
                if (terminalStatuses.includes(data.processing_status)) {
                    setPolling(false);
                    clearInterval(poll);
                    if (onComplete && (data.processing_status === 'processed' || data.processing_status === 'enriched')) {
                        setTimeout(() => onComplete(data), 1500);
                    }
                }
            } catch (e) {
                console.error("Polling failed", e);
            }
        }, 2000);

        return () => clearInterval(poll);
    }, [submissionId, onComplete]);

    if (!status) {
        return (
            <div className="process-tracker-container">
                <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '3rem',
                    gap: '1rem'
                }}>
                    <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    >
                        <Loader2 size={32} color="hsl(217, 91%, 60%)" />
                    </motion.div>
                    <p style={{ color: 'hsl(228, 8%, 55%)', fontSize: '0.9375rem' }}>
                        Initializing pipeline tracker...
                    </p>
                </div>
            </div>
        );
    }

    const getStepIndex = (stepKey) => Steps.findIndex(s => s.key === stepKey);
    const currentStepIndex = Steps.findIndex(s => status.steps?.[s.key] === 'in_progress');
    const lastCompletedIndex = [...Steps].reverse().findIndex(s => status.steps?.[s.key] === 'completed');
    const progressIndex = currentStepIndex >= 0 ? currentStepIndex : (lastCompletedIndex >= 0 ? Steps.length - 1 - lastCompletedIndex : -1);

    return (
        <motion.div
            className="process-tracker-container"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
        >
            <h3>Onboarding Pipeline</h3>

            {/* Pipeline Steps */}
            <div className="pipeline-steps">
                {Steps.map((step, index) => {
                    // Demo mode: force all steps to completed (green)
                    // New placeholder step is always green regardless of mode
                    const actualStepStatus = status.steps?.[step.key] || 'pending';
                    const stepStatus = (demoMode || step.alwaysGreen) ? 'completed' : actualStepStatus;
                    const Icon = step.icon;
                    const isCompleted = stepStatus === 'completed';
                    const isInProgress = stepStatus === 'in_progress';
                    const isFailed = stepStatus === 'failed';

                    return (
                        <motion.div
                            key={step.key}
                            className={`pipeline-step ${stepStatus}`}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.1 }}
                        >
                            <motion.div
                                className="icon-container"
                                animate={isInProgress ? {
                                    scale: [1, 1.05, 1],
                                } : {}}
                                transition={{
                                    duration: 2,
                                    repeat: isInProgress ? Infinity : 0,
                                    ease: 'easeInOut'
                                }}
                            >
                                <AnimatePresence mode="wait">
                                    {isCompleted ? (
                                        <motion.div
                                            key="completed"
                                            initial={{ scale: 0, rotate: -180 }}
                                            animate={{ scale: 1, rotate: 0 }}
                                            transition={{ type: 'spring', stiffness: 200, damping: 15 }}
                                        >
                                            <CheckCircle size={24} color="#10b981" />
                                        </motion.div>
                                    ) : isInProgress ? (
                                        <motion.div
                                            key="progress"
                                            animate={{ rotate: 360 }}
                                            transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
                                        >
                                            <Loader2 size={24} color="#3b82f6" />
                                        </motion.div>
                                    ) : isFailed ? (
                                        <motion.div
                                            key="failed"
                                            initial={{ scale: 0 }}
                                            animate={{ scale: 1 }}
                                        >
                                            <AlertCircle size={24} color="#ef4444" />
                                        </motion.div>
                                    ) : (
                                        <Icon size={24} color="#6b7280" />
                                    )}
                                </AnimatePresence>
                            </motion.div>

                            <div className="step-content">
                                <h4>{step.label}</h4>
                                <p className="step-status-text">
                                    {isInProgress ? 'Processing...' : stepStatus.replace('_', ' ')}
                                </p>
                            </div>

                            {/* Connector Line */}
                            {index < Steps.length - 1 && (
                                <div className="connector-line" style={{
                                    background: isCompleted
                                        ? 'linear-gradient(90deg, #10b981, #10b981)'
                                        : isInProgress
                                            ? 'linear-gradient(90deg, #10b981, #3b82f6, #374151)'
                                            : '#374151'
                                }} />
                            )}
                        </motion.div>
                    );
                })}
            </div>

            {/* Progress Summary */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
                style={{
                    marginTop: '2.5rem',
                    padding: '1rem 1.5rem',
                    background: 'hsl(228, 15%, 9%)',
                    borderRadius: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    border: '1px solid hsl(228, 12%, 18%)'
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        background: polling ? '#3b82f6' : status.processing_status === 'failed' ? '#ef4444' : '#10b981',
                        animation: polling ? 'pulse 2s ease-in-out infinite' : 'none'
                    }} />
                    <span style={{ fontSize: '0.875rem', color: 'hsl(228, 8%, 55%)' }}>
                        {polling ? 'Processing in progress...' :
                            status.processing_status === 'failed' ? 'Processing failed' :
                                'Processing complete'}
                    </span>
                </div>
                <div style={{ fontSize: '0.8125rem', color: 'hsl(228, 8%, 40%)' }}>
                    {demoMode ? Steps.length : completedSteps.length} of {Steps.length} steps completed
                </div>
            </motion.div>

            {/* Error Banner */}
            <AnimatePresence>
                {status.error_message && (
                    <motion.div
                        className="error-banner"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                    >
                        <AlertCircle size={20} />
                        <span>{status.error_message}</span>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Live Provider Preview */}
            <AnimatePresence>
                {status.provider && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        transition={{ delay: 0.3 }}
                        className="live-provider-preview"
                    >
                        <h4>
                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                Live Record Status
                                <ArrowRight size={14} color="hsl(228, 8%, 55%)" />
                            </span>
                            <span className={`badge ${status.provider.status}`}>
                                {status.provider.status?.replace('_', ' ')}
                            </span>
                        </h4>

                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(2, 1fr)',
                            gap: '1rem',
                            marginTop: '1rem'
                        }}>
                            <div style={{
                                padding: '0.75rem 1rem',
                                background: 'hsl(228, 12%, 11%)',
                                borderRadius: '8px',
                                border: '1px solid hsl(228, 12%, 18%)'
                            }}>
                                <div style={{ fontSize: '0.75rem', color: 'hsl(228, 8%, 55%)', marginBottom: '0.25rem' }}>
                                    Confidence Score
                                </div>
                                <div style={{
                                    fontSize: '1.25rem',
                                    fontWeight: 600,
                                    color: status.provider.overall_confidence >= 80 ? '#10b981' :
                                        status.provider.overall_confidence >= 60 ? '#fbbf24' : '#ef4444'
                                }}>
                                    {status.provider.overall_confidence ?? '—'}%
                                </div>
                            </div>
                            <div style={{
                                padding: '0.75rem 1rem',
                                background: 'hsl(228, 12%, 11%)',
                                borderRadius: '8px',
                                border: '1px solid hsl(228, 12%, 18%)'
                            }}>
                                <div style={{ fontSize: '0.75rem', color: 'hsl(228, 8%, 55%)', marginBottom: '0.25rem' }}>
                                    NPI Validation
                                </div>
                                <div style={{
                                    fontSize: '1rem',
                                    fontWeight: 500,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem'
                                }}>
                                    {status.provider.npi_status === 'VALID' ? (
                                        <>
                                            <CheckCircle size={16} color="#10b981" />
                                            <span style={{ color: '#10b981' }}>Valid</span>
                                        </>
                                    ) : status.provider.npi_status === 'INVALID' ? (
                                        <>
                                            <AlertCircle size={16} color="#ef4444" />
                                            <span style={{ color: '#ef4444' }}>Invalid</span>
                                        </>
                                    ) : (
                                        <span style={{ color: 'hsl(228, 8%, 55%)' }}>Pending</span>
                                    )}
                                </div>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* US Map Analysis Section */}
            <USMapAnalysis />
        </motion.div>
    );
};

export default ProcessTracker;
