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
            const response = await fetch('http://localhost:8000/providers');
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
        const interval = setInterval(() => fetchProviders(), 5000);
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
            // Wait a bit for database to commit, then refresh
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
                    <h2 style={{ marginBottom: '0.5rem' }}>Onboarded Stakeholders</h2>
                    <p style={{ color: 'hsl(228, 8%, 55%)', fontSize: '0.9375rem', margin: 0 }}>
                        {providers.length} provider{providers.length !== 1 ? 's' : ''} in the system
                    </p>
                </div>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
                    <button
                        onClick={handleSeedMockData}
                        className="submit-btn"
                        disabled={seedLoading}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.5rem 1rem',
                            background: 'hsl(160, 84%, 39%)',
                            color: 'white'
                        }}
                    >
                        {seedLoading ? (
                            <>
                                <Loader2 size={16} className="spin" />
                                Seeding...
                            </>
                        ) : (
                            <>
                                <Users size={16} />
                                Load Mock Data
                            </>
                        )}
                    </button>
                    {onNavigateToAnalysis && (
                        <button
                            onClick={onNavigateToAnalysis}
                            className="submit-btn"
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                padding: '0.5rem 1rem',
                                background: 'hsl(217, 91%, 60%)',
                                color: 'white'
                            }}
                        >
                            <Map size={16} />
                            View Analysis
                            <ArrowRight size={14} />
                        </button>
                    )}
                    <button
                        onClick={handleRefresh}
                        className="submit-btn secondary"
                        disabled={refreshing}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.5rem 1rem'
                        }}
                    >
                        <RefreshCw size={16} className={refreshing ? 'spin' : ''} />
                        {refreshing ? 'Refreshing...' : 'Refresh'}
                    </button>
                </div>
            </div>

            {/* Empty State */}
            {providers.length === 0 ? (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="empty-state"
                >
                    <div style={{
                        width: '80px',
                        height: '80px',
                        margin: '0 auto 1.5rem',
                        background: 'hsla(217, 91%, 60%, 0.1)',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                    }}>
                        <Users size={36} color="hsl(217, 91%, 60%)" />
                    </div>
                    <h3>No Providers Yet</h3>
                    <p style={{ maxWidth: '400px', margin: '0.5rem auto 0' }}>
                        Start by onboarding your first healthcare provider. Use the "Onboard New" tab to get started.
                    </p>
                </motion.div>
            ) : (
                /* Provider Table */
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.3 }}
                >
                    <table className="provider-table">
                        <thead>
                            <tr>
                                <th>Status</th>
                                <th>NPI</th>
                                <th>Name</th>
                                <th>Type</th>
                                <th>Confidence</th>
                                <th>Email</th>
                                <th style={{ textAlign: 'right' }}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            <AnimatePresence>
                                {providers.map((p, index) => (
                                    <motion.tr
                                        key={p.provider_id}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, y: -10 }}
                                        transition={{ delay: index * 0.05 }}
                                    >
                                        <td>
                                            <span className={`badge ${p.status}`}>
                                                {p.status?.replace('_', ' ') || 'pending'}
                                            </span>
                                        </td>
                                        <td style={{ fontFamily: "'SF Mono', 'Fira Code', monospace", fontSize: '0.875rem' }}>
                                            {p.npi || '—'}
                                        </td>
                                        <td>
                                            <div style={{ fontWeight: 500 }}>
                                                {p.display_name || 'Unknown'}
                                            </div>
                                            {p.practice_name && (
                                                <div style={{
                                                    fontSize: '0.8125rem',
                                                    color: 'hsl(228, 8%, 55%)',
                                                    marginTop: '0.125rem'
                                                }}>
                                                    {p.practice_name}
                                                </div>
                                            )}
                                        </td>
                                        <td>
                                            <span style={{
                                                fontSize: '0.8125rem',
                                                color: 'hsl(228, 8%, 55%)'
                                            }}>
                                                {p.practice_name ? 'Organization' : 'Individual'}
                                            </span>
                                        </td>
                                        <td>
                                            {p.overall_confidence ? (
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                    <div style={{
                                                        width: '60px',
                                                        height: '6px',
                                                        background: 'hsl(228, 12%, 18%)',
                                                        borderRadius: '3px',
                                                        overflow: 'hidden'
                                                    }}>
                                                        <div style={{
                                                            width: `${p.overall_confidence}%`,
                                                            height: '100%',
                                                            background: p.overall_confidence >= 80
                                                                ? 'hsl(160, 84%, 39%)'
                                                                : p.overall_confidence >= 60
                                                                    ? 'hsl(43, 96%, 56%)'
                                                                    : 'hsl(0, 72%, 51%)',
                                                            borderRadius: '3px',
                                                            transition: 'width 0.5s ease'
                                                        }} />
                                                    </div>
                                                    <span style={{ fontSize: '0.8125rem', color: 'hsl(228, 8%, 55%)' }}>
                                                        {p.overall_confidence}%
                                                    </span>
                                                </div>
                                            ) : (
                                                <span style={{ color: 'hsl(228, 8%, 40%)' }}>—</span>
                                            )}
                                        </td>
                                        <td>
                                            {p.email ? (
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                    <span style={{ fontSize: '0.8125rem', color: 'hsl(228, 8%, 55%)' }}>
                                                        {p.email}
                                                    </span>
                                                    <button
                                                        onClick={() => handleVerifyEmail(p.provider_id)}
                                                        disabled={verifyingEmail === p.provider_id}
                                                        style={{
                                                            display: 'inline-flex',
                                                            alignItems: 'center',
                                                            gap: '0.25rem',
                                                            padding: '0.25rem 0.5rem',
                                                            background: 'hsl(217, 91%, 60%)',
                                                            border: 'none',
                                                            borderRadius: '4px',
                                                            color: 'white',
                                                            fontSize: '0.75rem',
                                                            cursor: verifyingEmail === p.provider_id ? 'not-allowed' : 'pointer',
                                                            opacity: verifyingEmail === p.provider_id ? 0.6 : 1
                                                        }}
                                                        title="Send verification email"
                                                    >
                                                        {verifyingEmail === p.provider_id ? (
                                                            <Loader2 size={12} className="spin" />
                                                        ) : (
                                                            <Mail size={12} />
                                                        )}
                                                        Verify
                                                    </button>
                                                </div>
                                            ) : (
                                                <span style={{ color: 'hsl(228, 8%, 40%)', fontSize: '0.8125rem' }}>No email</span>
                                            )}
                                        </td>
                                        <td style={{ textAlign: 'right' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'flex-end' }}>
                                                <button
                                                    onClick={() => onSelectProvider(p.provider_id)}
                                                    style={{
                                                        display: 'inline-flex',
                                                        alignItems: 'center',
                                                        gap: '0.25rem'
                                                    }}
                                                >
                                                    View Details
                                                    <ChevronRight size={14} />
                                                </button>
                                            </div>
                                        </td>
                                    </motion.tr>
                                ))}
                            </AnimatePresence>
                        </tbody>
                    </table>
                </motion.div>
            )}
        </div>
    );
};

export default Dashboard;
