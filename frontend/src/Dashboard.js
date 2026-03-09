import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Users, RefreshCw, ChevronRight, AlertCircle, Loader2, Map, ArrowRight, Mail, CheckCircle, Globe, Phone } from 'lucide-react';
import './App.css';

const StatCard = ({ title, value, color }) => (
    <motion.div
        whileHover={{ y: -2 }}
        style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            padding: '0.4rem 0.75rem',
            border: `1px solid ${color + '40'}`,
            background: `linear-gradient(135deg, ${color + '10'}, transparent)`,
            borderRadius: '12px',
            minWidth: '130px'
        }}
    >
        <p style={{ color: 'hsl(var(--muted-foreground))', fontSize: '0.7rem', marginBottom: '0.125rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{title}</p>
        <motion.h3
            key={value}
            initial={{ scale: 0.9, opacity: 0.8 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: 'spring', stiffness: 400, damping: 25 }}
            style={{ fontSize: '1.25rem', fontWeight: 800, color: 'hsl(var(--foreground))', margin: 0 }}
        >
            {value}
        </motion.h3>
    </motion.div>
);

const Dashboard = ({ onSelectProvider, onNavigateToAnalysis }) => {
    const [providers, setProviders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [refreshing, setRefreshing] = useState(false);
    const [verifyingEmail, setVerifyingEmail] = useState(null);
    const [scheduleInterval, setScheduleInterval] = useState(0);
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const dropdownRef = React.useRef(null);

    React.useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsDropdownOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

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
        const fetchConfig = async () => {
            try {
                const res = await fetch('http://localhost:8000/scheduler/config');
                if (res.ok) {
                    const data = await res.json();
                    setScheduleInterval(data.interval_minutes);
                }
            } catch (err) {
                console.error("Failed to fetch schedule config", err);
            }
        };
        fetchConfig();
        const interval = setInterval(() => fetchProviders(), 3000); // Polling faster for visual effect
        return () => clearInterval(interval);
    }, []);

    const handleScheduleChange = async (e) => {
        const value = parseFloat(e.target.value);
        setScheduleInterval(value);

        try {
            await fetch('http://localhost:8000/scheduler/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ interval_minutes: value })
            });
        } catch (err) {
            console.error("Failed to update schedule config", err);
            alert("Failed to update auto re-enrich schedule");
        }
    };

    const handleRefresh = () => {
        fetchProviders(true);
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

    const handleBatchEnrich = async () => {
        const providersList = needsReviewProviders;
        if (!window.confirm(`Start batch enrichment for ${providersList.length} providers?`)) return;

        try {
            const npiList = providersList.map(p => p.npi);
            const response = await fetch('http://localhost:8000/providers/batch-enrich', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ npi_list: npiList })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to start batch enrichment');
            }
            const data = await response.json();
            alert(data.message);
        } catch (err) {
            console.error("Batch enrichment failed", err);
            alert(`Error: ${err.message}`);
        }
    };

    const handleSingleEnrich = async (npi) => {
        try {
            const response = await fetch('http://localhost:8000/providers/batch-enrich', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ npi_list: [npi] })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to start enrichment');
            }
            alert("Enrichment process started for provider.");
        } catch (err) {
            console.error("Enrichment failed", err);
            alert(`Error: ${err.message}`);
        }
    };

    // Filter Logic
    const selfVerifiedProviders = providers.filter(p => p.status === 'verified_by_provider');

    // Only move to 'Enriched' if enrichment is explicitly done
    const verifiedProviders = providers.filter(p => {
        return p.status === 'verified' || p.status === 'enriched';
    });

    // Stay in 'NPI Checked' until explicitly enriched or self-verified
    // Sort by confidence: Low to High as requested
    const needsReviewProviders = providers
        .filter(p => {
            return p.status !== 'verified_by_provider' && p.status !== 'verified' && p.status !== 'enriched';
        })
        .sort((a, b) => (a.overall_confidence || 0) - (b.overall_confidence || 0));

    const handleBatchCall = async () => {
        const providersList = selfVerifiedProviders;
        if (!window.confirm(`Start batch calls for ${providersList.length} self-verified providers?`)) return;

        try {
            const npiList = providersList.map(p => p.npi);
            const response = await fetch('http://localhost:8000/providers/batch-call', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ npi_list: npiList })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to start batch calls');
            }
            const data = await response.json();
            alert(data.message);
        } catch (err) {
            console.error("Batch call failed", err);
            alert(`Error: ${err.message}`);
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
                    padding: '8rem 2rem',
                    gap: '1.5rem'
                }}>
                    <Loader2 size={48} className="spin" style={{ color: 'hsl(var(--primary))' }} />
                    <p style={{ color: 'hsl(var(--muted-foreground))', fontSize: '1.125rem', fontWeight: 500, letterSpacing: '0.02em' }}>
                        Initializing Pipeline Monitor...
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

    const renderTable = (data, emptyMessage, isVerified = false) => (
        <>
            {data.length === 0 ? (
                <div style={{
                    padding: '3rem 2rem',
                    textAlign: 'center',
                    background: 'hsla(0, 0%, 100%, 0.01)',
                    borderRadius: '16px',
                    border: '1px dashed hsl(var(--border))',
                    color: 'hsl(var(--muted-foreground))',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '1rem'
                }}>
                    <div style={{
                        background: 'hsl(var(--background-elevated))',
                        padding: '1rem',
                        borderRadius: '50%',
                        color: 'hsl(var(--subtle-foreground))'
                    }}>
                        {isVerified ? <CheckCircle size={24} /> : <AlertCircle size={24} />}
                    </div>
                    {emptyMessage}
                </div>
            ) : (
                <div className="provider-table-container" style={{ overflowX: 'auto', paddingBottom: '0.5rem', width: '100%' }}>
                    <table className="provider-table modern-table" style={{ width: '100%', minWidth: '400px', tableLayout: 'fixed' }}>
                        <thead>
                            <tr>
                                <th style={{ width: '120px' }}>Status</th>
                                <th>Name</th>
                                <th style={{ width: '80px', textAlign: 'right' }}>Score</th>
                            </tr>
                        </thead>
                        <tbody>
                            <AnimatePresence>
                                {data.map((p, index) => (
                                    <motion.tr
                                        key={p.provider_id}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, scale: 0.95 }}
                                        transition={{ delay: index * 0.05, duration: 0.2 }}
                                        className="table-row-hover"
                                        onClick={() => onSelectProvider(p.provider_id)}
                                        style={{ cursor: 'pointer' }}
                                    >
                                        <td>
                                            <span className={`badge ${p.status === 'verified_by_provider' ? 'self_verified' : p.status === 'verified' ? 'enriched' : p.status}`}>
                                                {p.status === 'needs_review' ? 'Checked' :
                                                    p.status === 'verified_by_provider' ? 'Self-Verified' :
                                                        (p.status === 'verified' ? 'Enriched' : (p.status || 'Pending'))}
                                            </span>
                                        </td>
                                        <td>
                                            <div style={{ fontWeight: 600, fontSize: '0.95rem', color: 'hsl(var(--foreground))' }}>
                                                {p.display_name || 'Unknown'}
                                            </div>
                                            <div style={{ fontSize: '0.8rem', color: 'hsl(var(--muted-foreground))', marginTop: '0.125rem' }}>
                                                {p.npi}
                                            </div>
                                        </td>
                                        <td style={{ textAlign: 'right' }}>
                                            {p.status === 'verified_by_provider' ? (
                                                <div style={{ fontWeight: '700', color: 'hsl(var(--success))', textShadow: '0 0 10px hsla(160, 84%, 39%, 0.3)' }}>100%</div>
                                            ) : (
                                                p.overall_confidence ? (
                                                    <div style={{
                                                        fontWeight: '700',
                                                        color: p.overall_confidence >= 80 ? 'hsl(var(--success))' :
                                                            p.overall_confidence >= 60 ? 'hsl(var(--warning))' : 'hsl(var(--error))',
                                                        textShadow: p.overall_confidence >= 80 ? '0 0 10px hsla(160, 84%, 39%, 0.3)' :
                                                            p.overall_confidence >= 60 ? '0 0 10px hsla(43, 96%, 56%, 0.3)' : '0 0 10px hsla(0, 72%, 51%, 0.3)'
                                                    }}>
                                                        {Math.round(p.overall_confidence)}%
                                                    </div>
                                                ) : <span style={{ color: 'hsl(var(--muted-foreground))' }}>—</span>
                                            )}
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

    const avgConfidence = providers.length > 0
        ? Math.round(providers.reduce((acc, p) => acc + (p.overall_confidence || 0), 0) / providers.length)
        : 0;



    return (
        <div className="dashboard">
            {/* Unified Top Header & Stats Section */}
            {/* Unified Top Header & Stats Section - Single Row */}
            <div className="glass-panel" style={{
                borderRadius: '24px',
                padding: '1rem 2rem',
                border: '1px solid hsla(217, 91%, 60%, 0.2)',
                marginBottom: '2.5rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '2.5rem',
                background: 'linear-gradient(90deg, hsla(217, 91%, 60%, 0.05) 0%, transparent 100%)',
                overflowX: 'auto'
            }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', minWidth: '220px' }}>
                    <h2 style={{
                        margin: 0,
                        fontSize: '1.75rem',
                        fontWeight: 800,
                        background: 'linear-gradient(90deg, #fff 0%, hsl(217, 91%, 75%) 100%)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        letterSpacing: '-0.02em'
                    }}>
                        Pipeline Monitor
                    </h2>
                    <p style={{ color: 'hsl(var(--muted-foreground))', fontSize: '0.8125rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', background: 'hsl(217, 91%, 60%)', boxShadow: '0 0 6px hsl(217, 91%, 60%)' }}></span>
                        AI-Powered Verification Engine
                    </p>
                </div>

                {/* Summary Stats - Squeezed Horizontal */}
                <div style={{
                    display: 'flex',
                    gap: '1rem',
                    flex: 1,
                    justifyContent: 'center',
                    padding: '0 1rem'
                }}>
                    <StatCard
                        title="Total"
                        value={providers.length}
                        color="#ffffff"
                    />
                    <StatCard
                        title="NPI Checked"
                        value={needsReviewProviders.length}
                        color="#eab308"
                    />
                    <StatCard
                        title="Enriched"
                        value={verifiedProviders.length}
                        color="#3b82f6"
                    />
                    <StatCard
                        title="Self Verified"
                        value={selfVerifiedProviders.length}
                        color="#a855f7"
                    />
                    <StatCard
                        title="Confidence"
                        value={`${avgConfidence}%`}
                        color="#22d3ee"
                    />
                </div>

                {/* Controls - Squeezed */}
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'hsla(var(--background-elevated), 0.8)', padding: '0.4rem 0.75rem', borderRadius: '20px', border: '1px solid hsl(var(--border))' }}>
                        <RefreshCw size={12} style={{ color: 'hsl(217, 91%, 60%)' }} />
                        <span style={{ fontSize: '0.75rem', color: 'hsl(var(--muted-foreground))', fontWeight: 600 }}>AUTO</span>
                        <div style={{ position: 'relative' }} ref={dropdownRef}>
                            <div
                                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                                style={{
                                    background: 'transparent',
                                    border: 'none',
                                    color: 'hsl(var(--foreground))',
                                    fontSize: '0.75rem',
                                    fontWeight: 700,
                                    outline: 'none',
                                    cursor: 'pointer',
                                    padding: 0,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '4px'
                                }}
                            >
                                {scheduleInterval === 0 ? "OFF" : scheduleInterval === 5 ? "5m" : scheduleInterval === 15 ? "15m" : scheduleInterval === 60 ? "1h" : "24h"}
                                <motion.div animate={{ rotate: isDropdownOpen ? 180 : 0 }}>
                                    <svg width="10" height="10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                    </svg>
                                </motion.div>
                            </div>

                            <AnimatePresence>
                                {isDropdownOpen && (
                                    <motion.div
                                        initial={{ opacity: 0, y: -5 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, y: -5 }}
                                        transition={{ duration: 0.15 }}
                                        style={{
                                            position: 'absolute',
                                            top: '100%',
                                            right: 0,
                                            marginTop: '6px',
                                            background: 'hsl(228, 12%, 18%)',
                                            border: '1px solid hsl(228, 12%, 25%)',
                                            borderRadius: '6px',
                                            zIndex: 100,
                                            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                                            minWidth: '70px'
                                        }}
                                    >
                                        {[
                                            { value: 0, label: "OFF" },
                                            { value: 5, label: "5m" },
                                            { value: 15, label: "15m" },
                                            { value: 60, label: "1h" },
                                            { value: 1440, label: "24h" }
                                        ].map(option => (
                                            <div
                                                key={option.value}
                                                onClick={() => { handleScheduleChange({ target: { value: option.value } }); setIsDropdownOpen(false); }}
                                                style={{
                                                    padding: '0.4rem 0.75rem',
                                                    cursor: 'pointer',
                                                    fontSize: '0.75rem',
                                                    fontWeight: 600,
                                                    color: scheduleInterval === option.value ? 'white' : 'hsl(228, 8%, 70%)',
                                                    background: scheduleInterval === option.value ? 'hsl(217, 91%, 60%)' : 'transparent',
                                                }}
                                                onMouseEnter={(e) => { if (scheduleInterval !== option.value) e.target.style.background = 'hsla(228, 12%, 25%, 1)'; }}
                                                onMouseLeave={(e) => { if (scheduleInterval !== option.value) e.target.style.background = 'transparent'; }}
                                            >
                                                {option.label}
                                            </div>
                                        ))}
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </div>

                    <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={handleRefresh}
                        className="submit-btn secondary"
                        disabled={refreshing}
                        style={{ padding: '0.4rem 0.8rem', borderRadius: '20px', fontSize: '0.75rem', width: 'auto' }}
                    >
                        <RefreshCw size={14} className={refreshing ? 'spin' : ''} />
                    </motion.button>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '1.5rem', overflowX: 'auto' }}>
                {/* NPI Checked Section */}
                <div className="panel-glow-warning" style={{
                    background: 'hsla(43, 96%, 56%, 0.05)',
                    border: '1px solid hsla(43, 96%, 56%, 0.2)',
                    borderRadius: '24px',
                    padding: '2rem',
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    position: 'relative',
                    overflow: 'hidden'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '2rem', justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                            <div style={{
                                background: 'linear-gradient(135deg, hsla(43, 96%, 56%, 0.2), hsla(43, 96%, 56%, 0.05))',
                                padding: '0.75rem',
                                borderRadius: '12px',
                                color: '#eab308',
                                boxShadow: 'inset 0 0 10px hsla(43, 96%, 56%, 0.2)'
                            }}>
                                <AlertCircle size={24} />
                            </div>
                            <div>
                                <h3 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: 'hsl(var(--foreground))' }}>NPI Checked</h3>
                                <p style={{ fontSize: '0.85rem', color: 'hsl(var(--muted-foreground))', margin: '0.25rem 0 0 0' }}>Pending enrichment</p>
                            </div>
                        </div>

                        {/* Batch Action */}
                        <div style={{ display: 'flex', gap: '0.75rem' }}>
                            <motion.button
                                whileHover={{ scale: 1.05, backgroundColor: 'hsl(var(--card-hover))' }}
                                whileTap={{ scale: 0.95 }}
                                className="submit-btn secondary"
                                style={{ padding: '0.5rem 1rem', fontSize: '0.85rem', width: 'auto', borderRadius: '10px' }}
                                onClick={handleBatchEnrich}
                                disabled={needsReviewProviders.length === 0}
                            >
                                <Globe size={16} style={{ marginRight: '0.5rem', color: 'hsl(var(--info))' }} />
                                Batch Enrich
                            </motion.button>
                        </div>
                    </div>
                    {renderTable(needsReviewProviders, "No items pending review.")}
                </div>

                {/* Enriched Section */}
                <div className="panel-glow-success" style={{
                    background: 'hsla(217, 91%, 60%, 0.05)',
                    border: '1px solid hsla(217, 91%, 60%, 0.2)',
                    borderRadius: '24px',
                    padding: '2rem',
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    position: 'relative',
                    overflow: 'hidden'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '2rem', justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                            <div style={{
                                background: 'linear-gradient(135deg, hsla(217, 91%, 60%, 0.2), hsla(217, 91%, 60%, 0.05))',
                                padding: '0.75rem',
                                borderRadius: '12px',
                                color: '#3b82f6',
                                boxShadow: 'inset 0 0 10px hsla(217, 91%, 60%, 0.2)'
                            }}>
                                <CheckCircle size={24} />
                            </div>
                            <div>
                                <h3 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: 'hsl(var(--foreground))' }}>Enriched</h3>
                                <p style={{ fontSize: '0.85rem', color: 'hsl(var(--muted-foreground))', margin: '0.25rem 0 0 0' }}>Ready for verification</p>
                            </div>
                        </div>

                        {/* Moved Batch Verify here */}
                        <motion.button
                            whileHover={{ scale: 1.05, backgroundColor: 'hsl(var(--card-hover))' }}
                            whileTap={{ scale: 0.95 }}
                            className="submit-btn secondary"
                            style={{ padding: '0.5rem 1rem', fontSize: '0.85rem', width: 'auto', borderRadius: '10px' }}
                            onClick={() => {
                                alert("Batch verification email process started for enriched providers.");
                                verifiedProviders.forEach(p => handleVerifyEmail(p.npi));
                            }}
                            disabled={verifiedProviders.length === 0}
                        >
                            <Mail size={16} style={{ marginRight: '0.5rem', color: 'hsl(var(--primary))' }} />
                            Batch Verify
                        </motion.button>
                    </div>
                    {renderTable(verifiedProviders, "No enriched providers yet.", true)}
                </div>

                {/* Self Verified Section */}
                <div className="panel-glow-purple" style={{
                    background: 'hsla(270, 80%, 60%, 0.05)',
                    border: '1px solid hsla(270, 80%, 60%, 0.2)',
                    borderRadius: '24px',
                    padding: '2rem',
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    position: 'relative',
                    overflow: 'hidden'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '2rem', justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                            <div style={{
                                background: 'linear-gradient(135deg, hsla(270, 80%, 60%, 0.2), hsla(270, 80%, 60%, 0.05))',
                                padding: '0.75rem',
                                borderRadius: '12px',
                                color: 'hsl(270, 80%, 70%)',
                                boxShadow: 'inset 0 0 10px hsla(270, 80%, 60%, 0.2)'
                            }}>
                                <Users size={24} />
                            </div>
                            <div>
                                <h3 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: 'hsl(var(--foreground))' }}>Self Verified</h3>
                                <p style={{ fontSize: '0.85rem', color: 'hsl(var(--muted-foreground))', margin: '0.25rem 0 0 0' }}>Verified by the provider directly</p>
                            </div>
                        </div>

                        <motion.button
                            whileHover={{ scale: 1.05, backgroundColor: 'hsl(var(--card-hover))' }}
                            whileTap={{ scale: 0.95 }}
                            className="submit-btn secondary"
                            style={{ padding: '0.5rem 1rem', fontSize: '0.85rem', width: 'auto', borderRadius: '10px' }}
                            onClick={handleBatchCall}
                            disabled={selfVerifiedProviders.length === 0}
                        >
                            <Phone size={16} style={{ marginRight: '0.5rem', color: '#a855f7' }} />
                            Batch Call
                        </motion.button>
                    </div>
                    {renderTable(selfVerifiedProviders, "No self-verified providers yet.", true)}
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
