import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Users, RefreshCw, ChevronRight, AlertCircle, Loader2, Map, ArrowRight, Mail, CheckCircle } from 'lucide-react';
import './App.css';

const Dashboard = ({ onSelectProvider, onNavigateToAnalysis }) => {
    const [providers, setProviders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [refreshing, setRefreshing] = useState(false);
    const [verifyingEmail, setVerifyingEmail] = useState(null);
    const [seedLoading, setSeedLoading] = useState(false);

    const fetchProviders = async (isRefresh = false) => {
        if (isRefresh) setRefreshing(true);
        try {
            // Fetch more providers to show the batch processing visually
            const response = await fetch('http://localhost:8000/providers?limit=200');
            if (!response.ok) throw new Error('Failed to fetch providers');
            const data = await response.json();
            setProviders(data);
            setError(null);
        } catch (err) {
            console.error("Failed to fetch", err);
            setError(err.message);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        fetchProviders();
        const interval = setInterval(() => fetchProviders(), 3000); // Polling faster for visual effect
        return () => clearInterval(interval);
    }, []);

    const handleRefresh = () => {
        fetchProviders(true);
    };

    const handleSeedMockData = async () => {
        setSeedLoading(true);
        try {
            const response = await fetch('http://localhost:8000/providers/seed-mock-data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(errorData.detail || `HTTP ${response.status}: Failed to seed mock data`);
            }
            const data = await response.json();
            alert(`Successfully added ${data.count} mock providers!`);
            setTimeout(() => {
                fetchProviders(true);
            }, 500);
        } catch (err) {
            console.error("Failed to seed mock data", err);
            alert(`Error: ${err.message}`);
        } finally {
            setSeedLoading(false);
        }
    };

    const handleVerifyEmail = async (providerId) => {
        setVerifyingEmail(providerId);
        try {
            const response = await fetch(`http://localhost:8000/providers/${providerId}/verify-email`, {
                method: 'POST'
            });
            if (!response.ok) throw new Error('Failed to trigger email verification');
            const data = await response.json();
            alert(data.message);
        } catch (err) {
            console.error("Failed to verify email", err);
            alert(`Error: ${err.message}`);
        } finally {
            setVerifyingEmail(null);
        }
    };

    // Filter Logic
    const needsReviewProviders = providers.filter(p => {
        const score = p.overall_confidence || 0;
        return p.status === 'needs_review' || score < 60 || p.status === 'pending';
    });

    const verifiedProviders = providers.filter(p => {
        const score = p.overall_confidence || 0;
        // Verified if status is verified/enriched OR score is high (and not explicitly flagged for review)
        return (p.status === 'verified' || p.status === 'enriched' || score >= 60) && p.status !== 'needs_review' && p.status !== 'pending';
    });

    // Loading State
    if (loading && providers.length === 0) {
        return (
            <div className="dashboard">
                <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '4rem 2rem',
                    gap: '1rem'
                }}>
                    <Loader2 size={40} className="spin" style={{ color: 'hsl(217, 91%, 60%)' }} />
                    <p style={{ color: 'hsl(228, 8%, 55%)', fontSize: '0.9375rem' }}>
                        Loading dashboard...
                    </p>
                </div>
            </div>
        );
    }

    // Error State
    if (error && providers.length === 0) {
        return (
            <div className="dashboard">
                <div style={{
                    textAlign: 'center',
                    padding: '4rem 2rem',
                    background: 'hsl(228, 12%, 11%)',
                    borderRadius: '16px',
                    border: '1px solid hsl(228, 12%, 18%)'
                }}>
                    <AlertCircle size={48} style={{ color: 'hsl(0, 72%, 51%)', marginBottom: '1rem' }} />
                    <h3 style={{ marginBottom: '0.5rem' }}>Unable to Load Data</h3>
                    <p style={{ color: 'hsl(228, 8%, 55%)', marginBottom: '1.5rem' }}>
                        {error}. Please check your connection and try again.
                    </p>
                    <button onClick={handleRefresh} className="submit-btn secondary">
                        <RefreshCw size={16} />
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    const renderTable = (data, emptyMessage) => (
        <>
            {data.length === 0 ? (
                <div style={{
                    padding: '2rem',
                    textAlign: 'center',
                    background: 'hsl(var(--card))',
                    borderRadius: '12px',
                    border: '1px dashed hsl(var(--border))',
                    color: 'hsl(var(--muted-foreground))'
                }}>
                    {emptyMessage}
                </div>
            ) : (
                <div className="provider-table-container">
                    <table className="provider-table">
                        <thead>
                            <tr>
                                <th>Status</th>
                                <th>Name</th>
                                <th style={{ width: '80px' }}>Score</th>
                                <th style={{ textAlign: 'right' }}>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            <AnimatePresence>
                                {data.map((p, index) => (
                                    <motion.tr
                                        key={p.provider_id}
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0 }}
                                        transition={{ delay: index * 0.03 }}
                                    >
                                        <td>
                                            <span className={`badge ${p.status}`}>
                                                {p.status === 'needs_review' ? 'Review' : (p.status || 'Pending')}
                                            </span>
                                        </td>
                                        <td>
                                            <div style={{ fontWeight: 500, fontSize: '0.9rem' }}>
                                                {p.display_name || 'Unknown'}
                                            </div>
                                            <div style={{ fontSize: '0.75rem', color: 'hsl(228, 8%, 55%)' }}>
                                                {p.npi}
                                            </div>
                                        </td>
                                        <td>
                                            {p.overall_confidence ? (
                                                <div style={{
                                                    fontWeight: '600',
                                                    color: p.overall_confidence >= 80 ? 'hsl(var(--success))' :
                                                        p.overall_confidence >= 60 ? 'hsl(var(--warning))' : 'hsl(var(--error))'
                                                }}>
                                                    {Math.round(p.overall_confidence)}%
                                                </div>
                                            ) : '-'}
                                        </td>
                                        <td style={{ textAlign: 'right' }}>
                                            <button
                                                onClick={() => onSelectProvider(p.provider_id)}
                                                style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                                            >
                                                <ChevronRight size={14} />
                                            </button>
                                        </td>
                                    </motion.tr>
                                ))}
                            </AnimatePresence>
                        </tbody>
                    </table>
                </div>
            )}
        </>
    );

    return (
        <div className="dashboard">
            {/* Header */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: '2rem'
            }}>
                <div>
                    <h2 style={{ marginBottom: '0.5rem' }}>Pipeline Monitor</h2>
                    <p style={{ color: 'hsl(228, 8%, 55%)', fontSize: '0.9375rem', margin: 0 }}>
                        Real-time verification status of {providers.length} providers
                    </p>
                </div>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
                    <button onClick={handleSeedMockData} className="submit-btn" disabled={seedLoading} style={{ width: 'auto', padding: '0.5rem 1rem', background: 'hsl(160, 84%, 39%)' }}>
                        {seedLoading ? <Loader2 size={16} className="spin" /> : <Users size={16} />}
                        <span style={{ marginLeft: '0.5rem' }}>Seed Data</span>
                    </button>
                    {onNavigateToAnalysis && (
                        <button onClick={onNavigateToAnalysis} className="submit-btn" style={{ width: 'auto', padding: '0.5rem 1rem', background: 'hsl(217, 91%, 60%)' }}>
                            <Map size={16} /><span style={{ marginLeft: '0.5rem' }}>Analysis</span>
                        </button>
                    )}
                    <button onClick={handleRefresh} className="submit-btn secondary" disabled={refreshing}>
                        <RefreshCw size={16} className={refreshing ? 'spin' : ''} />
                    </button>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '2rem' }}>
                {/* Needs Review Section */}
                <div style={{
                    background: 'hsla(43, 96%, 56%, 0.05)',
                    border: '1px solid hsla(43, 96%, 56%, 0.2)',
                    borderRadius: '16px',
                    padding: '1.5rem',
                    display: 'flex',
                    flexDirection: 'column'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                        <div style={{
                            background: 'hsla(43, 96%, 56%, 0.2)',
                            padding: '0.5rem',
                            borderRadius: '8px',
                            color: 'hsl(var(--warning))'
                        }}>
                            <AlertCircle size={20} />
                        </div>
                        <div>
                            <h3 style={{ fontSize: '1.125rem', marginBottom: '0.25rem' }}>Needs Review</h3>
                            <p style={{ fontSize: '0.8125rem', color: 'hsl(var(--muted-foreground))' }}>Low confidence or flagged</p>
                        </div>
                        <div style={{ marginLeft: 'auto', fontWeight: 'bold', color: 'hsl(var(--warning))' }}>
                            {needsReviewProviders.length}
                        </div>
                    </div>
                    {renderTable(needsReviewProviders, "No items pending review.")}
                </div>

                {/* Verified Section */}
                <div style={{
                    background: 'hsla(160, 84%, 39%, 0.05)',
                    border: '1px solid hsla(160, 84%, 39%, 0.2)',
                    borderRadius: '16px',
                    padding: '1.5rem',
                    display: 'flex',
                    flexDirection: 'column'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                        <div style={{
                            background: 'hsla(160, 84%, 39%, 0.2)',
                            padding: '0.5rem',
                            borderRadius: '8px',
                            color: 'hsl(var(--success))'
                        }}>
                            <CheckCircle size={20} />
                        </div>
                        <div>
                            <h3 style={{ fontSize: '1.125rem', marginBottom: '0.25rem' }}>Verified</h3>
                            <p style={{ fontSize: '0.8125rem', color: 'hsl(var(--muted-foreground))' }}>Processed successfully</p>
                        </div>
                        <div style={{ marginLeft: 'auto', fontWeight: 'bold', color: 'hsl(var(--success))' }}>
                            {verifiedProviders.length}
                        </div>
                    </div>
                    {renderTable(verifiedProviders, "No verified providers yet.")}
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
