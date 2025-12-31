import React, { useState, useRef } from 'react';
import { Upload, FileText, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import './App.css';

const OnboardingForm = () => {
    const [mode, setMode] = useState('single');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState({ text: '', type: '' });
    const [submissionId, setSubmissionId] = useState(null);
    const [dragActive, setDragActive] = useState(false);
    const fileInputRef = useRef(null);
    const csvInputRef = useRef(null);

    const [formData, setFormData] = useState({
        npi: '',
        first_name: '',
        last_name: '',
        organization_name: '',
        primary_email: '',
        phone: '',
        website: '',
        type: 'Doctor'
    });

    const [csvFile, setCsvFile] = useState(null);

    const handleInputChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleReset = () => {
        setSubmissionId(null);
        setFormData({
            npi: '',
            first_name: '',
            last_name: '',
            organization_name: '',
            primary_email: '',
            phone: '',
            website: '',
            type: 'Doctor'
        });
        setMessage({ text: '', type: '' });
    };

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleDocumentUpload({ target: { files: e.dataTransfer.files } });
        }
    };

    const handleDocumentUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setLoading(true);
        setMessage({ text: 'Analyzing document with AI-powered OCR...', type: 'info' });

        const uploadData = new FormData();
        uploadData.append('file', file);

        try {
            const response = await fetch('http://localhost:8000/onboard/extract', {
                method: 'POST',
                body: uploadData,
            });

            if (!response.ok) throw new Error('Extraction failed');

            const extracted = await response.json();

            setFormData(prev => ({
                ...prev,
                npi: extracted.npi || prev.npi,
                first_name: extracted.first_name || prev.first_name,
                last_name: extracted.last_name || prev.last_name,
                organization_name: extracted.organization_name || prev.organization_name,
                primary_email: extracted.primary_email || prev.primary_email,
                type: extracted.provider_type === "Organization" ? "Hospital" : "Doctor"
            }));

            setMessage({ text: 'Document analyzed successfully! Please review the fields below.', type: 'success' });
        } catch (err) {
            setMessage({ text: `Error: ${err.message}`, type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleSubmitSingle = async (e) => {
        e.preventDefault();
        setLoading(true);
        setMessage({ text: '', type: '' });

        try {
            const response = await fetch('http://localhost:8000/onboard/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData),
            });
            if (!response.ok) throw new Error('Submission failed');

            const resData = await response.json();
            setSubmissionId(resData.submission_id);
            setMessage({ text: 'Submission queued. Starting validation pipeline...', type: 'success' });

        } catch (err) {
            setMessage({ text: `Error: ${err.message}`, type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleBatchUpload = async (e) => {
        e.preventDefault();
        if (!csvFile) return;
        setLoading(true);
        const uploadData = new FormData();
        uploadData.append('file', csvFile);

        try {
            const response = await fetch('http://localhost:8000/onboard/csv', {
                method: 'POST',
                body: uploadData,
            });
            if (!response.ok) throw new Error('Batch upload failed');
            const resData = await response.json();
            setMessage({ text: resData.message, type: 'success' });
            setCsvFile(null);
        } catch (err) {
            setMessage({ text: `Error: ${err.message}`, type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const ProcessTracker = require('./ProcessTracker').default;

    if (submissionId) {
        return (
            <div className="onboarding-container">
                <ProcessTracker
                    submissionId={submissionId}
                    onComplete={(finalData) => {
                        setMessage({
                            text: `Process Complete! Provider status: ${finalData.provider?.status || 'processed'}`,
                            type: 'success'
                        });
                    }}
                />
                <div style={{ textAlign: 'center', marginTop: '2rem' }}>
                    <button onClick={handleReset} className="submit-btn secondary">
                        ← Onboard Another Provider
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="onboarding-container">
            {/* Page Header */}
            <div style={{ marginBottom: '2rem' }}>
                <h2 style={{
                    fontSize: '1.75rem',
                    fontWeight: '700',
                    marginBottom: '0.5rem',
                    letterSpacing: '-0.02em'
                }}>
                    Provider Onboarding
                </h2>
                <p style={{ color: 'hsl(228, 8%, 55%)', fontSize: '1rem' }}>
                    Add healthcare providers through document upload, manual entry, or CSV batch processing.
                </p>
            </div>

            {/* Tabs */}
            <div className="tabs">
                <button
                    className={mode === 'single' ? 'active' : ''}
                    onClick={() => setMode('single')}
                >
                    Single Onboarding
                </button>
                <button
                    className={mode === 'batch' ? 'active' : ''}
                    onClick={() => setMode('batch')}
                >
                    Batch Upload (CSV)
                </button>
            </div>

            {/* Message Banner */}
            {message.text && (
                <div className={`processed-message ${message.type}`} style={{
                    background: message.type === 'success'
                        ? 'hsla(160, 50%, 20%, 1)'
                        : message.type === 'error'
                            ? 'hsla(0, 50%, 20%, 1)'
                            : 'hsla(199, 50%, 20%, 1)',
                    color: message.type === 'success'
                        ? 'hsl(160, 84%, 39%)'
                        : message.type === 'error'
                            ? 'hsl(0, 72%, 51%)'
                            : 'hsl(199, 89%, 48%)',
                    borderColor: message.type === 'success'
                        ? 'hsla(160, 84%, 39%, 0.3)'
                        : message.type === 'error'
                            ? 'hsla(0, 72%, 51%, 0.3)'
                            : 'hsla(199, 89%, 48%, 0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem'
                }}>
                    {message.type === 'success' && <CheckCircle size={18} />}
                    {message.type === 'error' && <AlertCircle size={18} />}
                    {message.type === 'info' && <Loader2 size={18} className="spin" />}
                    {message.text}
                </div>
            )}

            {mode === 'single' && (
                <div className="single-mode">
                    {/* Document Upload Section - Minimized */}
                    <div
                        className={`upload-section ${dragActive ? 'drag-active' : ''}`}
                        onDragEnter={handleDrag}
                        onDragLeave={handleDrag}
                        onDragOver={handleDrag}
                        onDrop={handleDrop}
                        style={{
                            borderColor: dragActive ? 'hsl(217, 91%, 60%)' : undefined,
                            background: dragActive ? 'hsla(217, 91%, 60%, 0.05)' : undefined,
                            padding: '1rem',
                            marginBottom: '1.5rem'
                        }}
                    >
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '1rem',
                            justifyContent: 'space-between'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1 }}>
                                <div style={{
                                    width: '40px',
                                    height: '40px',
                                    background: 'hsla(217, 91%, 60%, 0.1)',
                                    borderRadius: '8px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    flexShrink: 0
                                }}>
                                    <Upload size={20} color="hsl(217, 91%, 60%)" />
                                </div>
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{ fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem' }}>
                                        Auto-fill from Document
                                    </div>
                                    <div style={{ fontSize: '0.75rem', color: 'hsl(228, 8%, 55%)' }}>
                                        PDF, PNG, JPG (Max 5MB)
                                    </div>
                                </div>
                            </div>
                            <input
                                ref={fileInputRef}
                                type="file"
                                onChange={handleDocumentUpload}
                                accept=".pdf,.png,.jpg,.jpeg"
                                disabled={loading}
                                id="document-upload"
                                style={{ display: 'none' }}
                            />
                            <label
                                htmlFor="document-upload"
                                className="file-label"
                                style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    padding: '0.5rem 1rem',
                                    background: 'hsl(228, 12%, 11%)',
                                    border: '1px solid hsl(228, 12%, 18%)',
                                    borderRadius: '8px',
                                    color: 'hsl(0, 0%, 98%)',
                                    fontSize: '0.8125rem',
                                    fontWeight: '500',
                                    cursor: loading ? 'not-allowed' : 'pointer',
                                    transition: 'all 150ms ease',
                                    opacity: loading ? 0.5 : 1,
                                    whiteSpace: 'nowrap'
                                }}
                            >
                                <FileText size={14} />
                                {loading && !submissionId ? 'Processing...' : 'Upload'}
                            </label>
                        </div>
                    </div>

                    {/* Manual Form */}
                    <form onSubmit={handleSubmitSingle} className="manual-form">
                        <h3>Review & Submit Details</h3>

                        <div className="form-group">
                            <label>Stakeholder Type</label>
                            <select name="type" value={formData.type} onChange={handleInputChange}>
                                <option value="Doctor">Doctor / Individual</option>
                                <option value="Hospital">Hospital / Organization</option>
                                <option value="Insurance">Insurance Company</option>
                            </select>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                            <div className="form-group" style={{ marginBottom: 0 }}>
                                <label>NPI Number</label>
                                <input
                                    name="npi"
                                    value={formData.npi}
                                    onChange={handleInputChange}
                                    placeholder="10-digit NPI"
                                    required
                                />
                            </div>
                            <div className="form-group" style={{ marginBottom: 0 }}>
                                <label>Email</label>
                                <input
                                    name="primary_email"
                                    type="email"
                                    value={formData.primary_email}
                                    onChange={handleInputChange}
                                    placeholder="provider@example.com"
                                />
                            </div>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '1.5rem' }}>
                            <div className="form-group" style={{ marginBottom: 0 }}>
                                <label>First Name</label>
                                <input
                                    name="first_name"
                                    value={formData.first_name}
                                    onChange={handleInputChange}
                                    placeholder="John"
                                />
                            </div>
                            <div className="form-group" style={{ marginBottom: 0 }}>
                                <label>Last Name</label>
                                <input
                                    name="last_name"
                                    value={formData.last_name}
                                    onChange={handleInputChange}
                                    placeholder="Doe"
                                />
                            </div>
                        </div>

                        <div className="form-group" style={{ marginTop: '1.5rem' }}>
                            <label>Organization Name</label>
                            <input
                                name="organization_name"
                                value={formData.organization_name}
                                onChange={handleInputChange}
                                placeholder="e.g. Saint Mary's Hospital"
                            />
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                            <div className="form-group" style={{ marginBottom: 0 }}>
                                <label>Phone</label>
                                <input
                                    name="phone"
                                    value={formData.phone}
                                    onChange={handleInputChange}
                                    placeholder="(555) 555-5555"
                                />
                            </div>
                            <div className="form-group" style={{ marginBottom: 0 }}>
                                <label>Website</label>
                                <input
                                    name="website"
                                    value={formData.website}
                                    onChange={handleInputChange}
                                    placeholder="https://..."
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="submit-btn"
                            style={{ marginTop: '2rem' }}
                        >
                            {loading ? (
                                <>
                                    <Loader2 size={18} className="spin" />
                                    Processing...
                                </>
                            ) : (
                                'Start Onboarding Pipeline →'
                            )}
                        </button>
                    </form>
                </div>
            )}

            {mode === 'batch' && (
                <div className="batch-mode">
                    <div style={{
                        width: '64px',
                        height: '64px',
                        margin: '0 auto 1rem',
                        background: 'hsla(160, 84%, 39%, 0.1)',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                    }}>
                        <FileText size={28} color="hsl(160, 84%, 39%)" />
                    </div>
                    <h3 style={{ textAlign: 'center' }}>Upload CSV File</h3>
                    <p style={{ textAlign: 'center' }}>
                        Process multiple providers at once. Required columns: npi, first_name, last_name, organization_name
                    </p>
                    <form onSubmit={handleBatchUpload}>
                        <div style={{
                            border: '2px dashed hsl(228, 12%, 18%)',
                            borderRadius: '12px',
                            padding: '2rem',
                            textAlign: 'center',
                            marginBottom: '1.5rem',
                            background: csvFile ? 'hsla(160, 50%, 20%, 0.2)' : 'transparent',
                            borderColor: csvFile ? 'hsl(160, 84%, 39%)' : 'hsl(228, 12%, 18%)'
                        }}>
                            <input
                                ref={csvInputRef}
                                type="file"
                                accept=".csv"
                                onChange={(e) => setCsvFile(e.target.files[0])}
                                id="csv-upload"
                                style={{ display: 'none' }}
                            />
                            <label
                                htmlFor="csv-upload"
                                style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    padding: '0.75rem 1.5rem',
                                    background: 'hsl(228, 15%, 9%)',
                                    border: '1px solid hsl(228, 12%, 18%)',
                                    borderRadius: '10px',
                                    color: 'hsl(0, 0%, 98%)',
                                    fontSize: '0.875rem',
                                    fontWeight: '500',
                                    cursor: 'pointer',
                                    transition: 'all 150ms ease'
                                }}
                            >
                                <Upload size={16} />
                                {csvFile ? csvFile.name : 'Choose CSV File'}
                            </label>
                            {csvFile && (
                                <p style={{
                                    marginTop: '1rem',
                                    color: 'hsl(160, 84%, 39%)',
                                    fontSize: '0.875rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '0.5rem'
                                }}>
                                    <CheckCircle size={16} />
                                    {csvFile.name} ready to upload
                                </p>
                            )}
                        </div>
                        <button
                            type="submit"
                            disabled={loading || !csvFile}
                            className="submit-btn"
                        >
                            {loading ? (
                                <>
                                    <Loader2 size={18} className="spin" />
                                    Processing Batch...
                                </>
                            ) : (
                                'Process Batch Upload →'
                            )}
                        </button>
                    </form>
                </div>
            )}
        </div>
    );
};

export default OnboardingForm;
