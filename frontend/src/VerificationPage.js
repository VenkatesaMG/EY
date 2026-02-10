
import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Check, Edit2, ShieldCheck, AlertCircle, Save, X } from 'lucide-react';
import './DeploymentTracker.css'; // Reusing existing styles for consistency

const API_BASE = 'http://localhost:8000';

const FieldRow = ({ label, fieldKey, value, onUpdate }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [tempValue, setTempValue] = useState(value);
    const [isConfirmed, setIsConfirmed] = useState(false);

    useEffect(() => {
        setTempValue(value);
    }, [value]);

    const handleSave = () => {
        onUpdate(fieldKey, tempValue);
        setIsEditing(false);
        setIsConfirmed(true);
    };

    const handleConfirm = () => {
        setIsConfirmed(!isConfirmed);
    };

    return (
        <div className="provider-card" style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '1rem',
            marginBottom: '0.75rem',
            border: isConfirmed ? '1px solid #10b981' : '1px solid hsl(228, 12%, 18%)',
            backgroundColor: isConfirmed ? 'rgba(16, 185, 129, 0.05)' : 'hsl(228, 12%, 12%)'
        }}>
            <div style={{ flex: 1 }}>
                <p style={{ margin: 0, fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>{label}</p>

                {isEditing ? (
                    <input
                        type="text"
                        value={tempValue || ''}
                        onChange={(e) => setTempValue(e.target.value)}
                        className="search-input"
                        style={{ marginTop: '0.5rem', width: '90%' }}
                        autoFocus
                    />
                ) : (
                    <p style={{ margin: '0.25rem 0 0', fontSize: '1rem', fontWeight: 500 }}>
                        {value || <span style={{ fontStyle: 'italic', opacity: 0.5 }}>Not provided</span>}
                    </p>
                )}
            </div>

            <div style={{ display: 'flex', gap: '0.5rem' }}>
                {isEditing ? (
                    <>
                        <button
                            onClick={handleSave}
                            className="action-button primary"
                            style={{ padding: '0.5rem' }}
                            title="Save Changes"
                        >
                            <Save size={16} />
                        </button>
                        <button
                            onClick={() => { setIsEditing(false); setTempValue(value); }}
                            className="action-button"
                            style={{ padding: '0.5rem' }}
                            title="Cancel"
                        >
                            <X size={16} />
                        </button>
                    </>
                ) : (
                    <>
                        <button
                            onClick={() => setIsEditing(true)}
                            className="action-button"
                            style={{ padding: '0.5rem' }}
                            title="Edit Information"
                        >
                            <Edit2 size={16} />
                        </button>
                        <button
                            onClick={handleConfirm}
                            className={`action-button ${isConfirmed ? 'primary' : ''}`}
                            style={{
                                padding: '0.5rem',
                                backgroundColor: isConfirmed ? '#10b981' : undefined,
                                borderColor: isConfirmed ? '#10b981' : undefined
                            }}
                            title="Confirm Information"
                        >
                            <Check size={16} />
                        </button>
                    </>
                )}
            </div>
        </div>
    );
};

export default function VerificationPage() {
    const [token, setToken] = useState(null);

    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const tokenVal = params.get('token');
        setToken(tokenVal);

        if (!tokenVal) {
            setError("No verification token provided.");
            setLoading(false);
            return;
        }

        fetch(`${API_BASE}/verification/${tokenVal}`)
            .then(res => {
                if (!res.ok) throw new Error("Invalid or expired token");
                return res.json();
            })
            .then(data => {
                setData(data);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, []);

    const handleFieldUpdate = (key, newValue) => {
        setData(prev => ({
            ...prev,
            [key]: newValue
        }));
    };

    const handleSubmit = () => {
        setLoading(true);
        fetch(`${API_BASE}/verification/${token}/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
            .then(res => {
                if (!res.ok) throw new Error("Submission failed");
                return res.json();
            })
            .then(() => {
                setSuccess(true);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    };

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', color: '#94a3b8' }}>
                Loading verification data...
            </div>
        );
    }

    if (success) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '2rem', borderRadius: '1rem', textAlign: 'center' }}>
                    <ShieldCheck size={64} color="#10b981" style={{ marginBottom: '1rem' }} />
                    <h1>Verification Complete</h1>
                    <p style={{ color: '#94a3b8' }}>Thank you for verifying your information. Our records have been updated.</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column' }}>
                <AlertCircle size={64} color="#ef4444" style={{ marginBottom: '1rem' }} />
                <h1>Verification Failed</h1>
                <p style={{ color: '#ef4444' }}>{error}</p>
            </div>
        );
    }

    return (
        <div style={{ maxWidth: '800px', margin: '0 auto', padding: '2rem' }}>
            <header style={{ marginBottom: '2rem', textAlign: 'center' }}>
                <h1>Provider Verification Portal</h1>
                <p style={{ color: '#94a3b8' }}>
                    Please review the information below. Click the <Edit2 size={14} style={{ display: 'inline' }} /> icon to edit,
                    or the <Check size={14} style={{ display: 'inline' }} /> icon to confirm each field.
                </p>
            </header>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                <h3 style={{ margin: '1.5rem 0 1rem', borderBottom: '1px solid #334155', paddingBottom: '0.5rem' }}>Personal Information</h3>
                <FieldRow label="First Name" fieldKey="first_name" value={data.first_name} onUpdate={handleFieldUpdate} />
                <FieldRow label="Last Name" fieldKey="last_name" value={data.last_name} onUpdate={handleFieldUpdate} />
                <FieldRow label="Display Name" fieldKey="display_name" value={data.display_name} onUpdate={handleFieldUpdate} />
                <FieldRow label="Phone" fieldKey="phone" value={data.phone} onUpdate={handleFieldUpdate} />
                <FieldRow label="Email" fieldKey="email" value={data.email} onUpdate={handleFieldUpdate} />

                <h3 style={{ margin: '2rem 0 1rem', borderBottom: '1px solid #334155', paddingBottom: '0.5rem' }}>Professional Details</h3>
                <FieldRow label="Practice Name" fieldKey="practice_name" value={data.practice_name} onUpdate={handleFieldUpdate} />
                <FieldRow label="Website" fieldKey="website" value={data.website} onUpdate={handleFieldUpdate} />
                <FieldRow label="Address" fieldKey="address_line1" value={data.address_line1} onUpdate={handleFieldUpdate} />
                <FieldRow label="City" fieldKey="city" value={data.city} onUpdate={handleFieldUpdate} />
                <FieldRow label="State" fieldKey="state" value={data.state} onUpdate={handleFieldUpdate} />
                <FieldRow label="Postal Code" fieldKey="postal_code" value={data.postal_code} onUpdate={handleFieldUpdate} />

                <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'flex-end' }}>
                    <button
                        className="action-button primary"
                        style={{ padding: '1rem 2rem', fontSize: '1.1rem' }}
                        onClick={handleSubmit}
                    >
                        Submit Verified Information
                    </button>
                </div>
            </motion.div>
        </div>
    );
}
