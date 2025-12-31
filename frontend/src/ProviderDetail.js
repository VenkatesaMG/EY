import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
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
    ExternalLink
} from 'lucide-react';
import './App.css';

const ProviderDetail = ({ providerId, onBack }) => {
    const [provider, setProvider] = useState(null);
    const [loading, setLoading] = useState(true);

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

    const ValidationField = ({ icon: Icon, label, value, status, confidence }) => (
        <div className="detail-row">
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
            <span className="field-value">{value || 'N/A'}</span>
            {status && (
                <div className={`status-tag ${getStatusClass(status)}`} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.375rem'
                }}>
                    {getStatusIcon(status)}
                    {status}
                    {confidence && <span style={{ opacity: 0.8 }}>({confidence}%)</span>}
                </div>
            )}
        </div>
    );

    const InfoField = ({ icon: Icon, label, value, isLink = false }) => (
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
            <div style={{ flex: 1 }}>
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
        </div>
    );

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
                                {provider.overall_confidence}% confidence
                            </span>
                        )}
                    </div>
                </div>
            </div>

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
                        />
                        <ValidationField
                            icon={User}
                            label="Name"
                            value={provider.display_name}
                            status={provider.name_status}
                            confidence={provider.name_confidence}
                        />
                        <ValidationField
                            icon={Building2}
                            label="Practice"
                            value={provider.practice_name}
                            status={provider.practice_status}
                            confidence={provider.practice_confidence}
                        />
                        <ValidationField
                            icon={MapPin}
                            label="Address"
                            value={[provider.address_line1, provider.city, provider.state].filter(Boolean).join(', ') || null}
                            status={provider.address_status}
                            confidence={provider.address_confidence}
                        />
                        <ValidationField
                            icon={Stethoscope}
                            label="Taxonomy"
                            value={provider.taxonomy_code}
                            status={provider.taxonomy_status}
                            confidence={provider.taxonomy_confidence}
                        />
                        <ValidationField
                            icon={FileCheck}
                            label="License"
                            value={provider.license_number}
                            status={provider.license_status}
                            confidence={provider.license_confidence}
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
                        <InfoField icon={Phone} label="Phone Number" value={provider.phone} />
                        <InfoField icon={Mail} label="Email Address" value={provider.email} />
                        <InfoField icon={Globe} label="Website" value={provider.website} isLink />
                        <InfoField
                            icon={MapPin}
                            label="Full Address"
                            value={[
                                provider.address_line1,
                                provider.address_line2,
                                [provider.city, provider.state, provider.postal_code].filter(Boolean).join(', ')
                            ].filter(Boolean).join(', ') || null}
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
    );
};

export default ProviderDetail;
