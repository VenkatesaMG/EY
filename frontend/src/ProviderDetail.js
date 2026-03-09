import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    ArrowLeft,
    User,
    Building2,
    Mail,
    Phone,
    Globe,
    MapPin,
    FileCheck,
    Stethoscope,
    Shield,
    Loader2,
    CheckCircle,
    XCircle,
    AlertCircle,
    ExternalLink,
    Clock,
    History,
    ArrowRight,
    Database,
    Search,
    Bot,
    UserCheck,
    Edit3,
    Save
} from 'lucide-react';
import './App.css';

const ProviderDetail = ({ providerId, onBack }) => {
    const [provider, setProvider] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview'); // 'overview' or 'history'
    const [auditLog, setAuditLog] = useState([]);
    const [auditLoading, setAuditLoading] = useState(false);
    const [enriching, setEnriching] = useState(false);
    const [callSession, setCallSession] = useState(null); // { active: boolean, logs: array }

    // Manual Review State
    const [reviewData, setReviewData] = useState(null);
    const [reviewLoading, setReviewLoading] = useState(false);
    const [selectedValues, setSelectedValues] = useState({});
    const [customValues, setCustomValues] = useState({});
    const [submittingReview, setSubmittingReview] = useState(false);

    useEffect(() => {
        if (activeTab === 'review' && providerId) {
            const fetchReviewData = async () => {
                setReviewLoading(true);
                try {
                    const res = await fetch(`http://localhost:8000/providers/${providerId}/manual-review`);
                    const data = await res.json();
                    setReviewData(data);
                } catch (err) {
                    console.error('Failed to fetch review data:', err);
                } finally {
                    setReviewLoading(false);
                }
            };
            fetchReviewData();
        }
    }, [activeTab, providerId]);

    const handleSelectValue = (field, source, value) => {
        setSelectedValues(prev => ({
            ...prev,
            [field]: { source, value }
        }));
    };

    const handleCustomValueChange = (field, value) => {
        setCustomValues(prev => ({
            ...prev,
            [field]: value
        }));
        // Select custom automatically
        handleSelectValue(field, 'custom', value);
    };

    const submitManualReview = async () => {
        const updates = {};
        Object.keys(selectedValues).forEach(field => {
            updates[field] = selectedValues[field].value;
        });

        if (Object.keys(updates).length === 0) {
            alert("No changes selected.");
            return;
        }

        setSubmittingReview(true);
        try {
            const res = await fetch(`http://localhost:8000/providers/${providerId}/manual-review`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ updates })
            });
            const data = await res.json();
            if (data.success) {
                alert("Golden Record created successfully!");
                // Refresh data
                const refreshRes = await fetch(`http://localhost:8000/providers/${providerId}`);
                const refreshedData = await refreshRes.json();
                setProvider(refreshedData);
                setActiveTab('overview');
            } else {
                alert("Failed: " + data.message);
            }
        } catch (err) {
            alert("Error: " + err.message);
        } finally {
            setSubmittingReview(false);
        }
    };


    useEffect(() => {
        const fetchDetail = async () => {
            try {
                const res = await fetch(`http://localhost:8000/providers/${providerId}`);
                const data = await res.json();
                setProvider(data);
            } catch (err) {
                console.error('Failed to fetch provider details:', err);
            } finally {
                setLoading(false);
            }
        };
        fetchDetail();
    }, [providerId]);

    // Fetch audit log when History tab is selected
    useEffect(() => {
        if (activeTab === 'history' && providerId) {
            const fetchAuditLog = async () => {
                setAuditLoading(true);
                try {
                    const res = await fetch(`http://localhost:8000/providers/${providerId}/audit-log`);
                    const data = await res.json();
                    setAuditLog(data);
                } catch (err) {
                    console.error('Failed to fetch audit log:', err);
                } finally {
                    setAuditLoading(false);
                }
            };
            fetchAuditLog();
        }
    }, [activeTab, providerId]);

    const renderManualReviewTab = () => {
        if (reviewLoading) {
            return (
                <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem 2rem' }}>
                    <Loader2 size={32} className="spin" style={{ color: 'hsl(217, 91%, 60%)' }} />
                </div>
            );
        }

        if (!reviewData || Object.keys(reviewData).length === 0) {
            return (
                <div className="detail-card" style={{ textAlign: 'center', padding: '3rem 2rem' }}>
                    <p style={{ color: 'hsl(228, 8%, 55%)' }}>No review data available for this provider yet.</p>
                </div>
            );
        }

        return (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="detail-card" style={{ overflowX: 'auto' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h3 style={{ margin: 0, border: 'none', padding: 0 }}>Create Golden Record</h3>
                    <button
                        onClick={submitManualReview}
                        disabled={submittingReview}
                        className="submit-btn"
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.6rem 1.25rem',
                            borderRadius: '12px',
                            background: 'linear-gradient(135deg, hsl(217, 91%, 60%), #8b5cf6)',
                            color: 'white',
                            fontWeight: 600,
                            fontSize: '0.875rem',
                            border: 'none',
                            boxShadow: '0 4px 12px hsla(217, 91%, 60%, 0.3)',
                            cursor: submittingReview ? 'not-allowed' : 'pointer',
                            opacity: submittingReview ? 0.7 : 1,
                            transition: 'all 0.2s',
                            width: 'auto'
                        }}
                    >
                        {submittingReview ? <Loader2 size={16} className="spin" /> : <Save size={16} />}
                        Save Golden Record
                    </button>
                </div>


                <table className="review-table">
                    <thead>
                        <tr>
                            <th>Attribute</th>
                            <th>NPI Source</th>
                            <th>Web Enrichment</th>
                            <th>Email Result</th>
                            <th>Call Result</th>
                            <th>Custom Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        {Object.entries(reviewData).filter(([field]) => !['status', 'overall_confidence', 'confidence_score'].includes(field)).map(([field, sourcesData]) => (
                            <tr key={field} style={{ borderBottom: '1px solid hsla(228, 12%, 18%, 0.5)' }}>
                                <td>{formatFieldName(field)}</td>

                                {/* NPI Source */}
                                <td>
                                    {sourcesData['npi_lookup'] && (
                                        <div
                                            onClick={() => handleSelectValue(field, 'npi_lookup', sourcesData['npi_lookup'])}
                                            className="review-selection-card"
                                            style={{
                                                borderColor: selectedValues[field]?.source === 'npi_lookup' ? 'hsl(217, 91%, 60%)' : 'hsla(217, 91%, 60%, 0.3)',
                                                background: selectedValues[field]?.source === 'npi_lookup' ? 'hsla(217, 91%, 60%, 0.15)' : 'transparent',
                                                color: selectedValues[field]?.source === 'npi_lookup' ? 'hsl(217, 91%, 60%)' : 'hsl(228, 8%, 70%)',
                                                boxShadow: selectedValues[field]?.source === 'npi_lookup' ? 'inset 4px 0 0 0 hsl(217, 91%, 60%)' : 'none'
                                            }}
                                        >
                                            {sourcesData['npi_lookup']}
                                        </div>
                                    )}
                                </td>

                                {/* Web Enrichment */}
                                <td>
                                    {sourcesData['enrichment'] && (
                                        <div
                                            onClick={() => handleSelectValue(field, 'enrichment', sourcesData['enrichment'])}
                                            className="review-selection-card"
                                            style={{
                                                borderColor: selectedValues[field]?.source === 'enrichment' ? 'hsl(280, 70%, 60%)' : 'hsla(280, 70%, 60%, 0.3)',
                                                background: selectedValues[field]?.source === 'enrichment' ? 'hsla(280, 70%, 60%, 0.15)' : 'transparent',
                                                color: selectedValues[field]?.source === 'enrichment' ? 'hsl(280, 70%, 60%)' : 'hsl(228, 8%, 70%)',
                                                boxShadow: selectedValues[field]?.source === 'enrichment' ? 'inset 4px 0 0 0 hsl(280, 70%, 60%)' : 'none'
                                            }}
                                        >
                                            {sourcesData['enrichment']}
                                        </div>
                                    )}
                                </td>

                                {/* Email Result (Hunter/Verification) */}
                                <td>
                                    {(sourcesData['hunter_io'] || sourcesData['verification']) && (
                                        <div
                                            onClick={() => handleSelectValue(field, 'hunter', sourcesData['hunter_io'] || sourcesData['verification'])}
                                            className="review-selection-card"
                                            style={{
                                                borderColor: selectedValues[field]?.source === 'hunter' ? 'hsl(43, 96%, 56%)' : 'hsla(43, 96%, 56%, 0.3)',
                                                background: selectedValues[field]?.source === 'hunter' ? 'hsla(43, 96%, 56%, 0.15)' : 'transparent',
                                                color: selectedValues[field]?.source === 'hunter' ? 'hsl(43, 96%, 56%)' : 'hsl(228, 8%, 70%)',
                                                boxShadow: selectedValues[field]?.source === 'hunter' ? 'inset 4px 0 0 0 hsl(43, 96%, 56%)' : 'none'
                                            }}
                                        >
                                            {sourcesData['verification'] || sourcesData['hunter_io']}
                                        </div>
                                    )}
                                </td>

                                {/* Call Result */}
                                <td>
                                    {sourcesData['phone_verification'] && (
                                        <div
                                            onClick={() => handleSelectValue(field, 'phone_verification', sourcesData['phone_verification'])}
                                            className="review-selection-card"
                                            style={{
                                                borderColor: selectedValues[field]?.source === 'phone_verification' ? 'hsl(160, 84%, 39%)' : 'hsla(160, 84%, 39%, 0.3)',
                                                background: selectedValues[field]?.source === 'phone_verification' ? 'hsla(160, 84%, 39%, 0.15)' : 'transparent',
                                                color: selectedValues[field]?.source === 'phone_verification' ? 'hsl(160, 84%, 39%)' : 'hsl(228, 8%, 70%)',
                                                boxShadow: selectedValues[field]?.source === 'phone_verification' ? 'inset 4px 0 0 0 hsl(160, 84%, 39%)' : 'none'
                                            }}
                                        >
                                            {sourcesData['phone_verification']}
                                        </div>
                                    )}
                                </td>

                                {/* Custom Value */}
                                <td>
                                    <div
                                        className="review-custom-input-container"
                                        style={{
                                            borderColor: selectedValues[field]?.source === 'custom' ? 'hsl(0, 0%, 60%)' : 'hsla(0, 0%, 60%, 0.3)',
                                            background: selectedValues[field]?.source === 'custom' ? 'hsla(0, 0%, 60%, 0.15)' : 'transparent',
                                            boxShadow: selectedValues[field]?.source === 'custom' ? 'inset 4px 0 0 0 hsl(0, 0%, 60%)' : 'none',
                                            border: '1px solid',
                                            padding: '0.625rem 0.75rem',
                                            borderRadius: 'var(--radius-md)',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.75rem',
                                            transition: 'all 0.2s'
                                        }}
                                    >
                                        <input
                                            type="radio"
                                            checked={selectedValues[field]?.source === 'custom'}
                                            onChange={() => handleSelectValue(field, 'custom', customValues[field] || provider[field] || '')}
                                            style={{ accentColor: 'hsl(var(--foreground))', cursor: 'pointer', margin: 0 }}
                                        />
                                        <input
                                            type="text"
                                            placeholder="Enter text..."
                                            value={customValues[field] || ''}
                                            onChange={(e) => handleCustomValueChange(field, e.target.value)}
                                            onFocus={() => handleSelectValue(field, 'custom', customValues[field] || '')}
                                            style={{
                                                background: 'transparent',
                                                border: 'none',
                                                color: 'hsl(var(--foreground))',
                                                fontSize: '0.875rem',
                                                width: '100%',
                                                outline: 'none'
                                            }}
                                        />
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

            </motion.div>
        );
    };

    if (loading) {
        return (
            <div className="provider-detail">
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
                        Loading provider details...
                    </p>
                </div>
            </div>
        );
    }

    if (!provider) {
        return (
            <div className="provider-detail">
                <button onClick={onBack}>
                    <ArrowLeft size={16} />
                    Back to Dashboard
                </button>
                <div style={{
                    textAlign: 'center',
                    padding: '4rem 2rem',
                    background: 'hsl(228, 12%, 11%)',
                    borderRadius: '16px',
                    border: '1px solid hsl(228, 12%, 18%)',
                    marginTop: '2rem'
                }}>
                    <AlertCircle size={48} style={{ color: 'hsl(0, 72%, 51%)', marginBottom: '1rem' }} />
                    <h3 style={{ marginBottom: '0.5rem' }}>Provider Not Found</h3>
                    <p style={{ color: 'hsl(228, 8%, 55%)' }}>
                        The requested provider could not be found.
                    </p>
                </div>
            </div>
        );
    }

    const getStatusIcon = (status) => {
        switch (status?.toLowerCase()) {
            case 'valid':
            case 'verified':
                return <CheckCircle size={14} color="hsl(160, 84%, 39%)" />;
            case 'invalid':
            case 'failed':
                return <XCircle size={14} color="hsl(0, 72%, 51%)" />;
            default:
                return <AlertCircle size={14} color="hsl(43, 96%, 56%)" />;
        }
    };

    const getStatusClass = (status) => {
        switch (status?.toLowerCase()) {
            case 'valid':
            case 'verified':
                return 'valid';
            case 'invalid':
            case 'failed':
                return 'invalid';
            default:
                return 'pending';
        }
    };

    // --- Audit Log Helpers ---
    const getSourceIcon = (source) => {
        switch (source) {
            case 'npi_lookup': return <Database size={16} />;
            case 'enrichment': return <Search size={16} />;
            case 'hunter_io': return <Mail size={16} />;
            case 'verification': return <UserCheck size={16} />;
            case 'validation': return <Shield size={16} />;
            case 'submission': return <FileCheck size={16} />;
            default: return <Bot size={16} />;
        }
    };

    const getSourceColor = (source) => {
        switch (source) {
            case 'npi_lookup': return 'hsl(217, 91%, 60%)';
            case 'enrichment': return 'hsl(160, 84%, 39%)';
            case 'hunter_io': return 'hsl(43, 96%, 56%)';
            case 'verification': return 'hsl(280, 70%, 60%)';
            case 'validation': return 'hsl(199, 89%, 48%)';
            case 'submission': return 'hsl(340, 75%, 55%)';
            default: return 'hsl(228, 8%, 55%)';
        }
    };

    const getSourceLabel = (source) => {
        switch (source) {
            case 'npi_lookup': return 'NPI Registry';
            case 'enrichment': return 'Web Enrichment';
            case 'hunter_io': return 'Hunter.io';
            case 'verification': return 'Provider Verification';
            case 'validation': return 'AI Validation';
            case 'submission': return 'Form Submission';
            case 'csv_import': return 'CSV Import';
            default: return source;
        }
    };

    const formatFieldName = (name) => {
        return name
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase());
    };

    const formatTimestamp = (iso) => {
        if (!iso) return '';
        const d = new Date(iso);
        const now = new Date();
        const diffMs = now - d;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        let relative;
        if (diffMins < 1) relative = 'Just now';
        else if (diffMins < 60) relative = `${diffMins}m ago`;
        else if (diffHours < 24) relative = `${diffHours}h ago`;
        else if (diffDays < 7) relative = `${diffDays}d ago`;
        else relative = d.toLocaleDateString();

        return {
            relative,
            full: d.toLocaleString()
        };
    };

    // Group audit entries by date
    const groupByDate = (entries) => {
        const groups = {};
        entries.forEach(entry => {
            const date = new Date(entry.changed_at).toLocaleDateString('en-US', {
                year: 'numeric', month: 'long', day: 'numeric'
            });
            if (!groups[date]) groups[date] = [];
            groups[date].push(entry);
        });
        return groups;
    };

    const ValidationField = ({ icon: Icon, label, value, status, confidence, sourceUrl }) => (
        <div className="detail-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', minWidth: '160px' }}>
                <div style={{
                    width: '32px',
                    height: '32px',
                    background: 'hsl(228, 15%, 9%)',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                }}>
                    <Icon size={16} color="hsl(228, 8%, 55%)" />
                </div>
                <span className="field-label" style={{ width: 'auto' }}>{label}</span>
            </div>
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '1rem', overflow: 'hidden' }}>
                <span className="field-value">{value || 'N/A'}</span>
                {status && (
                    <div className={`status-tag ${getStatusClass(status)}`} style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.375rem',
                        flexShrink: 0
                    }}>
                        {getStatusIcon(status)}
                        {status}
                        {confidence && <span style={{ opacity: 0.8 }}>({Math.round(confidence)}%)</span>}
                    </div>
                )}
                {typeof sourceUrl === 'string' && value && value !== 'N/A' && (
                    <a
                        href={sourceUrl.startsWith('http') ? sourceUrl : `https://${sourceUrl}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                            color: 'hsl(160, 84%, 39%)',
                            background: 'hsla(160, 84%, 39%, 0.1)',
                            padding: '4px 8px',
                            borderRadius: '6px',
                            textDecoration: 'none',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.3rem',
                            fontSize: '0.7rem',
                            marginLeft: 'auto',
                            flexShrink: 0
                        }}
                        title="Source of this information"
                    >
                        <Globe size={10} />
                        Source
                    </a>
                )}
            </div>
        </div>
    );

    const InfoField = ({ icon: Icon, label, value, isLink = false, sourceUrl = null }) => (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '0.75rem 0',
            borderBottom: '1px solid hsla(228, 12%, 18%, 0.5)'
        }}>
            <div style={{
                width: '36px',
                height: '36px',
                background: 'hsla(217, 91%, 60%, 0.1)',
                borderRadius: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
            }}>
                <Icon size={18} color="hsl(217, 91%, 60%)" />
            </div>
            <div style={{ flex: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <div style={{ fontSize: '0.75rem', color: 'hsl(228, 8%, 55%)', marginBottom: '0.125rem' }}>
                        {label}
                    </div>
                    {isLink && value ? (
                        <a
                            href={value.startsWith('http') ? value : `https://${value}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                                color: 'hsl(217, 91%, 60%)',
                                textDecoration: 'none',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.25rem',
                                fontSize: '0.9375rem'
                            }}
                        >
                            {value}
                            <ExternalLink size={12} />
                        </a>
                    ) : (
                        <div style={{ fontSize: '0.9375rem', color: 'hsl(0, 0%, 98%)' }}>
                            {value || 'Not provided'}
                        </div>
                    )}
                </div>
                {typeof sourceUrl === 'string' && value && value !== 'Not provided' && (
                    <a
                        href={sourceUrl.startsWith('http') ? sourceUrl : `https://${sourceUrl}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                            color: 'hsl(160, 84%, 39%)',
                            background: 'hsla(160, 84%, 39%, 0.1)',
                            padding: '4px 8px',
                            borderRadius: '6px',
                            textDecoration: 'none',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.3rem',
                            fontSize: '0.7rem'
                        }}
                        title="Source of this information"
                    >
                        <Globe size={10} />
                        Source
                    </a>
                )}
            </div>
        </div>
    );

    // --- Timeline Entry Component ---
    const TimelineEntry = ({ entry, isLast }) => {
        const time = formatTimestamp(entry.changed_at);
        const color = getSourceColor(entry.change_source);

        return (
            <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3 }}
                className="timeline-entry"
            >
                {/* Timeline connector line */}
                <div className="timeline-connector">
                    <div className="timeline-dot" style={{
                        background: color,
                        boxShadow: `0 0 12px ${color}40`
                    }}>
                        {getSourceIcon(entry.change_source)}
                    </div>
                    {!isLast && <div className="timeline-line" />}
                </div>

                {/* Content */}
                <div className="timeline-content">
                    <div className="timeline-header">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                            <span className="timeline-field-name">
                                {formatFieldName(entry.field_name)}
                            </span>
                            <span className="timeline-source-badge" style={{
                                background: `${color}18`,
                                color: color,
                                border: `1px solid ${color}30`
                            }}>
                                {getSourceLabel(entry.change_source)}
                            </span>
                            {entry.table_name && (
                                <span className="timeline-table-badge">
                                    {entry.table_name}
                                </span>
                            )}
                        </div>
                        <div className="timeline-time" title={time.full}>
                            <Clock size={12} />
                            {time.relative}
                        </div>
                    </div>

                    {/* Value change visualization */}
                    <div className="timeline-values">
                        {entry.old_value ? (
                            <div className="timeline-value-change">
                                <div className="timeline-old-value">
                                    <span className="value-label">From</span>
                                    <span className="value-text old">{entry.old_value === 'None' ? 'Empty' : entry.old_value}</span>
                                </div>
                                <ArrowRight size={14} style={{ color: 'hsl(228, 8%, 40%)', flexShrink: 0 }} />
                                <div className="timeline-new-value">
                                    <span className="value-label">To</span>
                                    <span className="value-text new">{entry.new_value === 'None' ? 'Empty' : entry.new_value}</span>
                                </div>
                            </div>
                        ) : (
                            <div className="timeline-value-set">
                                <span className="value-label">Set to</span>
                                <span className="value-text new">{entry.new_value === 'None' ? 'Empty' : entry.new_value}</span>
                            </div>
                        )}
                    </div>

                    {/* Actor badge */}
                    {entry.actor && (
                        <div className="timeline-actor">
                            {entry.actor === 'provider' ? <UserCheck size={12} /> : <Bot size={12} />}
                            <span>{entry.actor === 'provider' ? 'Provider' : 'System'}</span>
                        </div>
                    )}
                </div>
            </motion.div>
        );
    };

    // --- Render History Tab ---
    const renderHistoryTab = () => {
        if (auditLoading) {
            return (
                <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '4rem 2rem',
                    gap: '1rem'
                }}>
                    <Loader2 size={32} className="spin" style={{ color: 'hsl(217, 91%, 60%)' }} />
                    <p style={{ color: 'hsl(228, 8%, 55%)', fontSize: '0.875rem' }}>
                        Loading change history...
                    </p>
                </div>
            );
        }

        if (auditLog.length === 0) {
            return (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="detail-card"
                    style={{ textAlign: 'center', padding: '3rem 2rem' }}
                >
                    <History size={48} style={{ color: 'hsl(228, 8%, 30%)', marginBottom: '1rem' }} />
                    <h3 style={{ borderBottom: 'none', marginBottom: '0.5rem', paddingBottom: 0 }}>No History Yet</h3>
                    <p style={{ color: 'hsl(228, 8%, 55%)', fontSize: '0.9375rem' }}>
                        Changes to this provider's data will appear here.
                        Try running validation or enrichment to generate audit entries.
                    </p>
                </motion.div>
            );
        }

        const grouped = groupByDate(auditLog);

        return (
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
            >
                {/* Summary Stats */}
                <div className="audit-stats">
                    <div className="audit-stat-card">
                        <div className="audit-stat-number">{auditLog.length}</div>
                        <div className="audit-stat-label">Total Changes</div>
                    </div>
                    <div className="audit-stat-card">
                        <div className="audit-stat-number">
                            {new Set(auditLog.map(e => e.change_source)).size}
                        </div>
                        <div className="audit-stat-label">Data Sources</div>
                    </div>
                    <div className="audit-stat-card">
                        <div className="audit-stat-number">
                            {new Set(auditLog.map(e => e.field_name)).size}
                        </div>
                        <div className="audit-stat-label">Fields Updated</div>
                    </div>
                    <div className="audit-stat-card">
                        <div className="audit-stat-number">
                            {Object.keys(grouped).length}
                        </div>
                        <div className="audit-stat-label">Active Days</div>
                    </div>
                </div>

                {/* Timeline */}
                <div className="audit-timeline">
                    {Object.entries(grouped).map(([date, entries]) => (
                        <div key={date} className="timeline-date-group">
                            <div className="timeline-date-header">
                                <Clock size={14} />
                                {date}
                            </div>
                            {entries.map((entry, idx) => (
                                <TimelineEntry
                                    key={entry.id}
                                    entry={entry}
                                    isLast={idx === entries.length - 1}
                                />
                            ))}
                        </div>
                    ))}
                </div>
            </motion.div>
        );
    };

    return (
        <motion.div
            className="provider-detail"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
        >
            {/* Back Button */}
            <button onClick={onBack} style={{ marginBottom: '1.5rem' }}>
                <ArrowLeft size={16} />
                Back to Dashboard
            </button>

            {/* Header */}
            <div style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '1.5rem',
                marginBottom: '2rem',
                padding: '1.5rem',
                background: 'hsl(228, 12%, 11%)',
                borderRadius: '16px',
                border: '1px solid hsl(228, 12%, 18%)'
            }}>
                <div style={{
                    width: '72px',
                    height: '72px',
                    background: 'linear-gradient(135deg, hsl(217, 91%, 60%), hsl(199, 89%, 48%))',
                    borderRadius: '16px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                }}>
                    {provider.practice_name ? (
                        <Building2 size={32} color="white" />
                    ) : (
                        <User size={32} color="white" />
                    )}
                </div>
                <div style={{ flex: 1 }}>
                    <h2 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700 }}>
                        {provider.display_name || 'Unknown Provider'}
                    </h2>
                    {provider.practice_name && (
                        <p style={{
                            margin: '0.25rem 0 0 0',
                            color: 'hsl(228, 8%, 55%)',
                            fontSize: '0.9375rem'
                        }}>
                            {provider.practice_name}
                        </p>
                    )}
                    <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
                        <span className={`badge ${provider.status}`}>
                            {provider.status?.replace('_', ' ') || 'pending'}
                        </span>
                        {provider.overall_confidence && (
                            <span style={{
                                fontSize: '0.8125rem',
                                color: 'hsl(228, 8%, 55%)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.375rem'
                            }}>
                                <Shield size={14} />
                                {Math.round(provider.overall_confidence)}% confidence
                            </span>
                        )}
                        <button
                            onClick={async () => {
                                try {
                                    const res = await fetch(`http://localhost:8000/providers/${provider.npi}/verify-email`, { method: 'POST' });
                                    const data = await res.json();
                                    if (data.success) {
                                        alert(`Verification email sent!\nLink (Debug): ${data.debug_link}`);
                                    } else {
                                        alert("Failed to send verification email.");
                                    }
                                } catch (err) {
                                    alert("Error: " + err.message);
                                }
                            }}
                            className="action-button"
                            style={{
                                padding: '0.4rem 0.8rem',
                                borderRadius: '6px',
                                border: '1px solid hsl(43, 96%, 56%)',
                                background: 'hsla(43, 96%, 56%, 0.1)',
                                color: 'hsl(43, 96%, 56%)',
                                fontSize: '0.75rem',
                                fontWeight: 600,
                                marginLeft: '0.5rem',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.375rem',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                boxShadow: '0 2px 4px hsla(43, 96%, 56%, 0.1)'
                            }}
                        >
                            <Mail size={14} color="hsl(43, 96%, 56%)" />
                            Verify via Email
                        </button>
                        <button
                            onClick={async () => {
                                try {
                                    setCallSession({ active: true, logs: [{ time: new Date().toLocaleTimeString(), text: "Initiating call...", type: 'system' }] });
                                    const res = await fetch(`http://localhost:8000/providers/${provider.npi}/call`, { method: 'POST' });
                                    const data = await res.json();

                                    if (data.success) {
                                        setCallSession(prev => ({ ...prev, logs: [...prev.logs, { time: new Date().toLocaleTimeString(), text: "Ringing provider...", type: 'system' }] }));

                                        // Connect to SSE stream
                                        const eventSource = new EventSource(`http://localhost:8000/providers/${provider.npi}/call-stream`);

                                        eventSource.onmessage = (event) => {
                                            const eventData = JSON.parse(event.data);

                                            setCallSession(prev => {
                                                const newLogs = [...(prev?.logs || [])];

                                                if (eventData.step === 'start') {
                                                    newLogs.push({ time: new Date().toLocaleTimeString(), text: "Call connected. Asking for NPI verification...", type: 'system' });
                                                } else if (eventData.step === 'verify_npi') {
                                                    if (eventData.digits) {
                                                        newLogs.push({ time: new Date().toLocaleTimeString(), text: `Provider entered NPI: ${eventData.digits}`, type: 'provider' });
                                                    }
                                                } else if (eventData.step === 'process_update') {
                                                    if (eventData.speech) {
                                                        newLogs.push({ time: new Date().toLocaleTimeString(), text: `Provider said: "${eventData.speech}"`, type: 'provider' });
                                                    }
                                                } else if (eventData.step === 'completed') {
                                                    newLogs.push({ time: new Date().toLocaleTimeString(), text: `Updates parsed by AI: ${JSON.stringify(eventData.updates)}`, type: 'ai' });
                                                    newLogs.push({ time: new Date().toLocaleTimeString(), text: "Call ended successfully. Refreshing data...", type: 'system' });

                                                    // Stop listening and close after a few seconds
                                                    eventSource.close();
                                                    setTimeout(() => {
                                                        setCallSession(null);
                                                        // force a re-fetch of the provider
                                                        fetch(`http://localhost:8000/providers/${provider.npi}`)
                                                            .then(r => r.json())
                                                            .then(d => setProvider(d));
                                                    }, 5000);
                                                }

                                                return { ...prev, logs: newLogs };
                                            });
                                        };

                                        eventSource.onerror = () => {
                                            eventSource.close();
                                        };

                                    } else {
                                        setCallSession(null);
                                        alert("Failed to initiate call.");
                                    }
                                } catch (err) {
                                    setCallSession(null);
                                    alert("Error: " + err.message);
                                }
                            }}
                            className="action-button"
                            style={{
                                padding: '0.4rem 0.8rem',
                                borderRadius: '6px',
                                border: '1px solid hsl(160, 84%, 39%)',
                                background: 'hsla(160, 84%, 39%, 0.1)',
                                color: 'hsl(160, 84%, 39%)',
                                fontSize: '0.75rem',
                                fontWeight: 600,
                                marginLeft: '0.5rem',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.375rem',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                boxShadow: '0 2px 4px hsla(160, 84%, 39%, 0.1)'
                            }}
                        >
                            <Phone size={14} color="hsl(160, 84%, 39%)" />
                            Verify via Phone
                        </button>
                        <button
                            onClick={async () => {
                                if (enriching) return;
                                setEnriching(true);
                                try {
                                    await fetch(`http://localhost:8000/providers/${provider.npi}/enrich`, { method: 'POST' });
                                    // Poll until status changes to enriched
                                    const poll = async () => {
                                        for (let i = 0; i < 60; i++) {
                                            await new Promise(r => setTimeout(r, 2000));
                                            try {
                                                const res = await fetch(`http://localhost:8000/providers/${provider.npi}`);
                                                const data = await res.json();
                                                if (data.status === 'enriched' || data.status === 'verified') {
                                                    setProvider(data);
                                                    setEnriching(false);
                                                    return;
                                                }
                                            } catch (e) { /* continue polling */ }
                                        }
                                        setEnriching(false);
                                    };
                                    poll();
                                } catch (err) {
                                    alert("Error: " + err.message);
                                    setEnriching(false);
                                }
                            }}
                            disabled={enriching}
                            className="action-button"
                            style={{
                                padding: '0.4rem 0.8rem',
                                borderRadius: '6px',
                                border: '1px solid hsl(217, 91%, 60%)',
                                background: enriching ? 'hsla(217, 91%, 60%, 0.3)' : 'hsla(217, 91%, 60%, 0.1)',
                                color: 'hsl(217, 91%, 60%)',
                                fontSize: '0.75rem',
                                fontWeight: 600,
                                marginLeft: '0.5rem',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.375rem',
                                cursor: enriching ? 'not-allowed' : 'pointer',
                                opacity: enriching ? 0.8 : 1,
                                transition: 'all 0.2s',
                                boxShadow: '0 2px 4px hsla(217, 91%, 60%, 0.1)'
                            }}
                        >
                            {enriching ? <Loader2 size={14} className="spin" color="hsl(217, 91%, 60%)" /> : <Globe size={14} color="hsl(217, 91%, 60%)" />}
                            {enriching ? 'Enriching...' : 'Enrich Now'}
                        </button>
                    </div>
                </div>
            </div>

            {/* Tab Switcher */}
            <div className="detail-tabs">
                <button
                    className={`detail-tab ${activeTab === 'overview' ? 'active' : ''}`}
                    onClick={() => setActiveTab('overview')}
                >
                    <FileCheck size={16} />
                    Overview
                </button>
                <button
                    className={`detail-tab ${activeTab === 'history' ? 'active' : ''}`}
                    onClick={() => setActiveTab('history')}
                >
                    <History size={16} />
                    History
                    {auditLog.length > 0 && (
                        <span className="tab-badge">{auditLog.length}</span>
                    )}
                </button>
                <button
                    className={`detail-tab ${activeTab === 'review' ? 'active' : ''}`}
                    onClick={() => setActiveTab('review')}
                >
                    <Edit3 size={16} />
                    Manual Review
                </button>
            </div>

            {/* Tab Content */}
            <AnimatePresence mode="wait">
                {activeTab === 'overview' ? (
                    <motion.div
                        key="overview"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.2 }}
                    >
                        {/* Two Column Layout */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                            {/* Left Column - Validation Data */}
                            <div>
                                <div className="detail-card">
                                    <h3>
                                        <FileCheck size={18} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
                                        Core Validation
                                    </h3>
                                    <ValidationField
                                        icon={Shield}
                                        label="NPI"
                                        value={provider.npi}
                                        status={provider.npi_status}
                                        confidence={provider.npi_confidence}
                                        sourceUrl={provider.field_metadata?.npi}
                                    />
                                    <ValidationField
                                        icon={User}
                                        label="Name"
                                        value={provider.display_name}
                                        status={provider.name_status}
                                        confidence={provider.name_confidence}
                                        sourceUrl={provider.field_metadata?.display_name || provider.field_metadata?.first_name}
                                    />
                                    <ValidationField
                                        icon={Building2}
                                        label="Practice"
                                        value={provider.practice_name}
                                        status={provider.practice_status}
                                        confidence={provider.practice_confidence}
                                        sourceUrl={provider.field_metadata?.practice_name}
                                    />
                                    <ValidationField
                                        icon={MapPin}
                                        label="Address"
                                        value={[provider.address_line1, provider.city, provider.state].filter(Boolean).join(', ') || null}
                                        status={provider.address_status}
                                        confidence={provider.address_confidence}
                                        sourceUrl={provider.field_metadata?.address_line1 || provider.field_metadata?.city}
                                    />
                                    <ValidationField
                                        icon={Stethoscope}
                                        label="Taxonomy"
                                        value={provider.taxonomy_code}
                                        status={provider.taxonomy_status}
                                        confidence={provider.taxonomy_confidence}
                                        sourceUrl={provider.field_metadata?.taxonomy_code}
                                    />
                                    <ValidationField
                                        icon={Stethoscope}
                                        label="Specialties"
                                        value={Array.isArray(provider.specialties) ? provider.specialties.join(', ') : provider.specialties}
                                        sourceUrl={provider.field_metadata?.specialties}
                                    />
                                    <ValidationField
                                        icon={FileCheck}
                                        label="License"
                                        value={provider.license_number}
                                        status={provider.license_status}
                                        confidence={provider.license_confidence}
                                        sourceUrl={provider.field_metadata?.license_number}
                                    />
                                </div>
                            </div>

                            {/* Right Column - Contact & Enrichment */}
                            <div>
                                <div className="detail-card">
                                    <h3>
                                        <Globe size={18} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
                                        Contact & Enrichment
                                    </h3>
                                    <InfoField icon={Phone} label="Phone Number" value={provider.phone} sourceUrl={provider.field_metadata?.phone} />
                                    <InfoField icon={Mail} label="Email Address" value={provider.email} sourceUrl={provider.field_metadata?.email} />
                                    <InfoField icon={Globe} label="Website" value={provider.website} isLink sourceUrl={provider.field_metadata?.website} />
                                    <InfoField
                                        icon={MapPin}
                                        label="Full Address"
                                        value={[
                                            provider.address_line1,
                                            provider.address_line2,
                                            [provider.city, provider.state, provider.postal_code].filter(Boolean).join(', ')
                                        ].filter(Boolean).join(', ') || null}
                                        sourceUrl={provider.field_metadata?.address_line1 || provider.field_metadata?.city}
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Raw Data Section */}
                        {provider.raw_data_json && (
                            <motion.div
                                className="detail-card"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.2 }}
                                style={{ marginTop: '1.5rem' }}
                            >
                                <h3 style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between'
                                }}>
                                    <span>Raw API Response</span>
                                    <span style={{
                                        fontSize: '0.75rem',
                                        fontWeight: 400,
                                        color: 'hsl(228, 8%, 55%)',
                                        background: 'hsl(228, 15%, 9%)',
                                        padding: '0.25rem 0.5rem',
                                        borderRadius: '4px'
                                    }}>
                                        JSON
                                    </span>
                                </h3>
                                <pre style={{
                                    maxHeight: '300px',
                                    overflow: 'auto',
                                    fontSize: '0.8125rem'
                                }}>
                                    {JSON.stringify(provider.raw_data_json, null, 2)}
                                </pre>
                            </motion.div>
                        )}
                    </motion.div>
                ) : activeTab === 'review' ? (
                    <motion.div
                        key="review"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.2 }}
                    >
                        {renderManualReviewTab()}
                    </motion.div>
                ) : (
                    <motion.div
                        key="history"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.2 }}
                    >
                        {renderHistoryTab()}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Live Call Popup */}
            <AnimatePresence>
                {callSession?.active && (
                    <motion.div
                        initial={{ opacity: 0, y: 50, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 50, scale: 0.95 }}
                        style={{
                            position: 'fixed',
                            bottom: '2rem',
                            right: '2rem',
                            width: '350px',
                            background: 'hsl(228, 12%, 11%)',
                            border: '1px solid hsl(228, 12%, 25%)',
                            borderRadius: '12px',
                            boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
                            display: 'flex',
                            flexDirection: 'column',
                            overflow: 'hidden',
                            zIndex: 1000
                        }}
                    >
                        {/* Header */}
                        <div style={{
                            padding: '1rem',
                            borderBottom: '1px solid hsl(228, 12%, 18%)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            background: 'hsl(228, 15%, 13%)'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <div style={{
                                    width: '10px',
                                    height: '10px',
                                    borderRadius: '50%',
                                    background: 'hsl(160, 84%, 39%)',
                                    boxShadow: '0 0 8px hsl(160, 84%, 39%)'
                                }} />
                                <span style={{ fontWeight: 600, fontSize: '0.9375rem' }}>Live Verification Call</span>
                            </div>
                            <button
                                onClick={() => setCallSession(null)}
                                style={{ background: 'transparent', border: 'none', color: 'hsl(228, 8%, 55%)', cursor: 'pointer' }}
                            >
                                <XCircle size={16} />
                            </button>
                        </div>

                        {/* Transcript Area */}
                        <div style={{
                            padding: '1rem',
                            maxHeight: '300px',
                            overflowY: 'auto',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '0.75rem'
                        }}>
                            {callSession.logs.map((log, i) => (
                                <div key={i} style={{
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: log.type === 'provider' ? 'flex-end' : 'flex-start',
                                }}>
                                    <span style={{ fontSize: '0.65rem', color: 'hsl(228, 8%, 40%)', marginBottom: '2px' }}>
                                        {log.time} {log.type === 'system' ? '- System' : log.type === 'ai' ? '- AI Parser' : '- Provider'}
                                    </span>
                                    <div style={{
                                        background: log.type === 'provider' ? 'hsl(217, 91%, 60%)' :
                                            log.type === 'ai' ? 'hsl(280, 70%, 60%)' :
                                                'hsl(228, 12%, 18%)',
                                        color: 'white',
                                        padding: '0.5rem 0.75rem',
                                        borderRadius: '8px',
                                        fontSize: '0.8125rem',
                                        maxWidth: '90%',
                                        lineHeight: 1.4
                                    }}>
                                        {log.text}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
};

export default ProviderDetail;
