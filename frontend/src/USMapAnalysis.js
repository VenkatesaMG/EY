import React, { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Sparkles, MapPin, Maximize, Minimize, Send, MessageSquare, RotateCcw, Bot, User, X } from 'lucide-react';
import {
    ComposableMap,
    Geographies,
    Geography,
    Annotation
} from 'react-simple-maps';
import { scaleQuantize } from 'd3-scale';
import './USMapAnalysis.css';

const geoUrl = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json";

// State abbreviation to FIPS code mapping
const stateAbbrToFIPS = {
    'AL': '01', 'AK': '02', 'AZ': '04', 'AR': '05', 'CA': '06',
    'CO': '08', 'CT': '09', 'DE': '10', 'FL': '12', 'GA': '13',
    'HI': '15', 'ID': '16', 'IL': '17', 'IN': '18', 'IA': '19',
    'KS': '20', 'KY': '21', 'LA': '22', 'ME': '23', 'MD': '24',
    'MA': '25', 'MI': '26', 'MN': '27', 'MS': '28', 'MO': '29',
    'MT': '30', 'NE': '31', 'NV': '32', 'NH': '33', 'NJ': '34',
    'NM': '35', 'NY': '36', 'NC': '37', 'ND': '38', 'OH': '39',
    'OK': '40', 'OR': '41', 'PA': '42', 'RI': '44', 'SC': '45',
    'SD': '46', 'TN': '47', 'TX': '48', 'UT': '49', 'VT': '50',
    'VA': '51', 'WA': '53', 'WV': '54', 'WI': '55', 'WY': '56',
    'DC': '11'
};

// FIPS to state abbreviation mapping
const fipsToAbbr = Object.fromEntries(
    Object.entries(stateAbbrToFIPS).map(([abbr, fips]) => [fips, abbr])
);

// Map Abbreviation to Full Name (for Tooltips)
const stateNames = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
    'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
    'DC': 'District of Columbia'
};

// Simple markdown renderer
const renderMarkdown = (text) => {
    if (!text) return '';

    return text
        // Headers
        .replace(/^### (.*$)/gim, '<h5 class="md-h5">$1</h5>')
        .replace(/^## (.*$)/gim, '<h4 class="md-h4">$1</h4>')
        .replace(/^# (.*$)/gim, '<h3 class="md-h3">$1</h3>')
        // Bold
        .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.*?)\*/gim, '<em>$1</em>')
        // Unordered lists
        .replace(/^\- (.*$)/gim, '<li>$1</li>')
        .replace(/^\* (.*$)/gim, '<li>$1</li>')
        // Ordered lists
        .replace(/^\d+\. (.*$)/gim, '<li>$1</li>')
        // Line breaks
        .replace(/\n\n/gim, '</p><p>')
        .replace(/\n/gim, '<br/>');
};

const SUGGESTED_PROMPTS = [
    "What are the key trends in provider distribution?",
    "Which states need more coverage?",
    "How is the data quality across providers?",
    "Compare top vs bottom performing states",
    "What specialties are underrepresented?"
];

const USMapAnalysis = () => {
    const [hoveredFIPS, setHoveredFIPS] = useState(null);
    const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
    const [mapRef, setMapRef] = useState(null);
    const [containerRef, setContainerRef] = useState(null);

    // Filter State
    const [specialties, setSpecialties] = useState([]);
    const [selectedSpecialty, setSelectedSpecialty] = useState("");

    // UI State
    const [showChatPanel, setShowChatPanel] = useState(false);
    const [isFullscreen, setIsFullscreen] = useState(false);

    // Real Data State
    const [stateStats, setStateStats] = useState({});

    // Dropdown State
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const dropdownRef = useRef(null);

    // Chat State
    const [chatMessages, setChatMessages] = useState([]);
    const [chatInput, setChatInput] = useState("");
    const [isSending, setIsSending] = useState(false);
    const [contextData, setContextData] = useState(null);
    const [isLoadingContext, setIsLoadingContext] = useState(false);

    const chatEndRef = useRef(null);
    const inputRef = useRef(null);

    // Auto-scroll to bottom of chat
    useEffect(() => {
        if (chatEndRef.current) {
            chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [chatMessages]);

    // Close Dropdown on outside click
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsDropdownOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    // Fetch Specialties
    useEffect(() => {
        fetch('http://localhost:8000/analytics/specialties')
            .then(res => res.json())
            .then(data => setSpecialties(data))
            .catch(err => console.error("Failed to load specialties", err));
    }, []);

    // Fetch Real Data
    useEffect(() => {
        const fetchData = async () => {
            try {
                const url = selectedSpecialty
                    ? `http://localhost:8000/analytics/geo-distribution?specialty=${encodeURIComponent(selectedSpecialty)}`
                    : 'http://localhost:8000/analytics/geo-distribution';

                const res = await fetch(url);
                const counts = await res.json();

                const mergedData = {};
                Object.keys(stateAbbrToFIPS).forEach(abbr => {
                    const count = counts[abbr] || 0;
                    mergedData[abbr] = {
                        name: stateNames[abbr],
                        count: count,
                        providers: count * 1
                    };
                });
                setStateStats(mergedData);
            } catch (e) {
                console.error("Failed to fetch geo stats", e);
            }
        };
        fetchData();

        const interval = setInterval(fetchData, 5000);
        return () => clearInterval(interval);
    }, [selectedSpecialty]);

    // Fetch context data when specialty changes (while chat is open)
    const fetchContextData = useCallback(async () => {
        setIsLoadingContext(true);
        try {
            const url = selectedSpecialty
                ? `http://localhost:8000/analyze/context-data?specialty=${encodeURIComponent(selectedSpecialty)}`
                : 'http://localhost:8000/analyze/context-data';
            const res = await fetch(url);
            const data = await res.json();
            setContextData(data);
            return data;
        } catch (e) {
            console.error("Failed to fetch context data", e);
            return null;
        } finally {
            setIsLoadingContext(false);
        }
    }, [selectedSpecialty]);

    // When specialty changes and chat is open, refresh context and notify
    useEffect(() => {
        if (showChatPanel && chatMessages.length > 0) {
            fetchContextData().then(newContext => {
                if (newContext) {
                    setChatMessages(prev => [
                        ...prev,
                        {
                            role: 'system_notice',
                            content: `Context updated: Now showing data for "${newContext.filter}" — ${newContext.total_providers} providers across ${newContext.states_with_providers} states.`
                        }
                    ]);
                }
            });
        }
    }, [selectedSpecialty]); // eslint-disable-line react-hooks/exhaustive-deps

    // Handle Fullscreen changes
    useEffect(() => {
        const handleFullscreenChange = () => {
            setIsFullscreen(!!document.fullscreenElement);
        };
        document.addEventListener('fullscreenchange', handleFullscreenChange);
        return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
    }, []);

    // Get data by FIPS
    const getStateData = useCallback((fips) => {
        const abbr = fipsToAbbr[fips];
        if (!abbr) return null;
        return stateStats[abbr];
    }, [stateStats]);

    // Calculate color scale using d3-scale
    const colorScale = useMemo(() => {
        const counts = Object.values(stateStats).map(d => d.count);
        if (counts.length === 0) return () => "#e5e7eb";

        const minCount = Math.min(...counts);
        const maxCount = Math.max(...counts);

        if (maxCount === 0) return () => "#f3f4f6";

        return scaleQuantize()
            .domain([minCount, maxCount || 1])
            .range([
                "#dbeafe",
                "#bfdbfe",
                "#93c5fd",
                "#60a5fa",
                "#3b82f6",
                "#1d4ed8"
            ]);
    }, [stateStats]);

    // Handle mouse move for tooltip positioning with edge detection
    const handleMouseMove = useCallback((event) => {
        if (mapRef) {
            const rect = mapRef.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
            const isNearRight = x > (rect.width * 0.6);

            setTooltipPosition({
                x: x,
                y: y,
                align: isNearRight ? 'left' : 'right'
            });
        }
    }, [mapRef]);

    // Open chat panel without automatic first analysis
    const handleOpenChat = async () => {
        const willShow = !showChatPanel;
        setShowChatPanel(willShow);

        if (willShow && chatMessages.length === 0) {
            // Just fetch context data for chat panel initial state
            await fetchContextData();
        }
    };

    // Send a message to the chat endpoint
    const sendMessage = async (messages, ctx = null) => {
        setIsSending(true);
        try {
            const currentContext = ctx || contextData;
            const res = await fetch('http://localhost:8000/analyze/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    messages: messages.filter(m => m.role === 'user' || m.role === 'assistant'),
                    specialty: selectedSpecialty || null,
                    context_data: currentContext || {}
                })
            });

            const result = await res.json();
            if (result.success) {
                setChatMessages(prev => [
                    ...prev,
                    { role: 'assistant', content: result.response }
                ]);
            } else {
                setChatMessages(prev => [
                    ...prev,
                    { role: 'assistant', content: 'Sorry, I was unable to generate a response. Please try again.' }
                ]);
            }
        } catch (e) {
            console.error("Chat error", e);
            setChatMessages(prev => [
                ...prev,
                { role: 'assistant', content: 'Connection error. Please check that the server is running.' }
            ]);
        } finally {
            setIsSending(false);
        }
    };

    // Handle user sending a message
    const handleSendMessage = async (customMessage = null) => {
        const message = customMessage || chatInput.trim();
        if (!message || isSending) return;

        const userMsg = { role: 'user', content: message };
        const newMessages = [...chatMessages, userMsg];
        setChatMessages(newMessages);
        setChatInput("");

        // Focus back on input
        if (inputRef.current) inputRef.current.focus();

        await sendMessage(newMessages);
    };

    // Handle key press in input
    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    // Reset chat
    const handleResetChat = () => {
        setChatMessages([]);
        setContextData(null);
    };

    const toggleFullScreen = () => {
        if (!containerRef) return;

        if (!document.fullscreenElement) {
            containerRef.requestFullscreen().catch((err) => {
                console.error(`Error attempting to enable fullscreen: ${err.message}`);
            });
        } else {
            document.exitFullscreen();
        }
    };

    const hoveredStateData = hoveredFIPS ? getStateData(hoveredFIPS) : null;

    return (
        <motion.div
            className={`us-map-analysis-container ${isFullscreen ? 'fullscreen-mode' : ''}`}
            ref={setContainerRef}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            style={isFullscreen ? {
                marginTop: 0,
                padding: '1rem',
                height: '100vh',
                width: '100vw',
                borderRadius: 0,
                border: 'none',
                background: 'hsl(var(--background))',
                zIndex: 9999,
                position: 'fixed',
                top: 0,
                left: 0
            } : {}}
        >
            <div className="analysis-header" style={isFullscreen ? { display: 'none' } : {}}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '1rem' }}>
                    <div>
                        <h3>Geographic Analysis</h3>
                        <p style={{ color: 'hsl(228, 8%, 55%)', fontSize: '0.875rem', marginTop: '0.5rem' }}>
                            Provider submissions and distribution across US states
                        </p>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', position: 'relative' }} ref={dropdownRef}>
                        <label style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 500 }}>Filter by Department/Specialty</label>
                        <div
                            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                            style={{
                                background: 'hsl(228, 12%, 18%)',
                                border: isDropdownOpen ? '1px solid hsl(217, 91%, 60%)' : '1px solid hsl(228, 12%, 25%)',
                                color: 'white',
                                padding: '0.5rem 0.75rem',
                                borderRadius: '6px',
                                fontSize: '0.875rem',
                                minWidth: '220px',
                                cursor: 'pointer',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                transition: 'all 0.2s ease',
                                boxShadow: isDropdownOpen ? '0 0 0 2px hsla(217, 91%, 60%, 0.2)' : 'none'
                            }}
                        >
                            <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '180px' }}>
                                {selectedSpecialty || "All Specialties"}
                            </span>
                            <motion.div animate={{ rotate: isDropdownOpen ? 180 : 0 }}>
                                <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
                                        top: 'calc(100% + 4px)',
                                        left: 0,
                                        width: '100%',
                                        background: 'hsl(228, 12%, 18%)',
                                        border: '1px solid hsl(228, 12%, 25%)',
                                        borderRadius: '6px',
                                        zIndex: 100,
                                        maxHeight: '300px',
                                        overflowY: 'auto',
                                        boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                                    }}
                                >
                                    <div
                                        className="dropdown-item"
                                        onClick={() => { setSelectedSpecialty(""); setIsDropdownOpen(false); }}
                                        style={{
                                            padding: '0.5rem 0.75rem',
                                            cursor: 'pointer',
                                            fontSize: '0.875rem',
                                            color: selectedSpecialty === "" ? 'white' : 'hsl(228, 8%, 70%)',
                                            background: selectedSpecialty === "" ? 'hsl(217, 91%, 60%)' : 'transparent',
                                        }}
                                        onMouseEnter={(e) => { if (selectedSpecialty !== "") e.target.style.background = 'hsla(228, 12%, 25%, 1)'; }}
                                        onMouseLeave={(e) => { if (selectedSpecialty !== "") e.target.style.background = 'transparent'; }}
                                    >
                                        All Specialties
                                    </div>
                                    {specialties.map(s => (
                                        <div
                                            key={s}
                                            className="dropdown-item"
                                            onClick={() => { setSelectedSpecialty(s); setIsDropdownOpen(false); }}
                                            style={{
                                                padding: '0.5rem 0.75rem',
                                                cursor: 'pointer',
                                                fontSize: '0.875rem',
                                                color: selectedSpecialty === s ? 'white' : 'hsl(228, 8%, 70%)',
                                                background: selectedSpecialty === s ? 'hsl(217, 91%, 60%)' : 'transparent',
                                            }}
                                            onMouseEnter={(e) => { if (selectedSpecialty !== s) e.target.style.background = 'hsla(228, 12%, 25%, 1)'; }}
                                            onMouseLeave={(e) => { if (selectedSpecialty !== s) e.target.style.background = 'transparent'; }}
                                        >
                                            {s}
                                        </div>
                                    ))}
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>

            {/* Layout Wrapper: Full or Split */}
            <div className="map-analysis-layout" style={{
                display: 'grid',
                gridTemplateColumns: showChatPanel ? '1fr 1fr' : '1fr',
                gap: showChatPanel ? '1.5rem' : '0',
                height: isFullscreen ? '100%' : 'auto',
                transition: 'all 0.4s ease'
            }}>
                {/* Map Section */}
                <div className="map-section" style={{ height: isFullscreen ? '100%' : 'auto' }}>
                    <div
                        ref={setMapRef}
                        className="map-container"
                        onMouseMove={handleMouseMove}
                        style={{
                            height: isFullscreen ? '100%' : showChatPanel ? '450px' : '550px',
                            minHeight: isFullscreen ? '0' : showChatPanel ? '400px' : '550px',
                            transition: 'all 0.3s ease',
                            width: '100%'
                        }}
                    >
                        {/* Control Buttons Overlay */}
                        <div style={{
                            position: 'absolute',
                            top: '1rem',
                            right: '1rem',
                            display: 'flex',
                            gap: '0.5rem',
                            zIndex: 50
                        }}>
                            <button
                                onClick={toggleFullScreen}
                                style={{
                                    background: 'rgba(15, 23, 42, 0.6)',
                                    backdropFilter: 'blur(4px)',
                                    border: '1px solid rgba(255,255,255,0.1)',
                                    color: 'white',
                                    padding: '8px',
                                    borderRadius: '8px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    transition: 'all 0.2s ease'
                                }}
                                title={isFullscreen ? "Exit Full Screen" : "Full Screen"}
                            >
                                {isFullscreen ? <Minimize size={20} /> : <Maximize size={20} />}
                            </button>
                        </div>

                        {/* Moved Legend to Top Left */}
                        <div className="map-legend" style={{
                            position: 'absolute',
                            top: '1rem',
                            left: '1rem',
                            margin: 0,
                            padding: '0.75rem 1rem',
                            display: (isFullscreen || showChatPanel) ? 'none' : 'flex',
                            zIndex: 40,
                            background: 'hsla(228, 15%, 9%, 0.8)',
                            backdropFilter: 'blur(4px)',
                            border: '1px solid hsl(228, 12%, 25%)',
                            borderRadius: '8px',
                            boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
                        }}>
                            <div className="legend-label" style={{ marginBottom: '0.5rem', fontWeight: 600, color: 'hsl(var(--foreground))' }}>Submission Intensity</div>
                            <div className="legend-gradient">
                                <div className="legend-item"><div className="legend-color" style={{ background: "#dbeafe" }}></div><span>Low</span></div>
                                <div className="legend-item"><div className="legend-color" style={{ background: "#93c5fd" }}></div><span>Medium</span></div>
                                <div className="legend-item"><div className="legend-color" style={{ background: "#1d4ed8" }}></div><span>High</span></div>
                            </div>
                        </div>

                        <ComposableMap
                            projection="geoAlbersUsa"
                            projectionConfig={{ scale: 1000 }}
                            style={{ width: '100%', height: '100%' }}
                        >
                            <Geographies geography={geoUrl}>
                                {({ geographies }) => (
                                    <>
                                        {geographies.map((geo) => {
                                            const fips = geo.id;
                                            const stateData = getStateData(fips);
                                            const count = stateData?.count || 0;
                                            const isHovered = hoveredFIPS === fips;
                                            const fillColor = count > 0 ? colorScale(count) : "#e5e7eb";

                                            return (
                                                <Geography
                                                    key={geo.rsmKey}
                                                    geography={geo}
                                                    fill={fillColor}
                                                    stroke={isHovered ? "#3b82f6" : "#fff"}
                                                    strokeWidth={isHovered ? 2 : 0.5}
                                                    style={{
                                                        default: { outline: 'none', cursor: 'pointer', transition: 'all 0.2s ease' },
                                                        hover: { outline: 'none', fill: fillColor, stroke: "#3b82f6", strokeWidth: 2 },
                                                        pressed: { outline: 'none' }
                                                    }}
                                                    onMouseEnter={() => setHoveredFIPS(fips)}
                                                    onMouseLeave={() => setHoveredFIPS(null)}
                                                />
                                            );
                                        })}
                                        {hoveredFIPS && (() => {
                                            const geo = geographies.find(g => g.id === hoveredFIPS);
                                            if (!geo) return null;
                                            const abbr = fipsToAbbr[hoveredFIPS];
                                            if (!abbr) return null;

                                            const geometry = geo.geometry;
                                            if (!geometry) return null;
                                            let candidatePoint = [0, 0];
                                            try {
                                                const coords = geometry.coordinates;
                                                if (!coords || coords.length === 0) return null;
                                                if (geometry.type === "Polygon") candidatePoint = coords[0][0];
                                                else if (geometry.type === "MultiPolygon") candidatePoint = coords[0][0][0];
                                                else return null;
                                                if (!Array.isArray(candidatePoint) || candidatePoint.length < 2) return null;
                                            } catch (e) { return null; }

                                            return (
                                                <Annotation
                                                    subject={candidatePoint}
                                                    dx={0} dy={0}
                                                >
                                                    <text x={0} y={0} fontSize={12} fontWeight={600} fill="#3b82f6" textAnchor="middle" style={{ pointerEvents: 'none', userSelect: 'none', textShadow: '0 1px 2px rgba(0,0,0,0.3)' }}>
                                                        {abbr}
                                                    </text>
                                                </Annotation>
                                            );
                                        })()}
                                    </>
                                )}
                            </Geographies>
                        </ComposableMap>

                        <AnimatePresence>
                            {hoveredFIPS && hoveredStateData && (
                                <motion.div
                                    className="state-tooltip-wrapper"
                                    initial={{ opacity: 0, scale: 0.8 }}
                                    animate={{
                                        opacity: 1,
                                        scale: 1,
                                        x: tooltipPosition.x,
                                        y: tooltipPosition.y
                                    }}
                                    exit={{ opacity: 0, scale: 0.8 }}
                                    style={{
                                        position: 'absolute',
                                        top: 0,
                                        left: 0,
                                        pointerEvents: 'none',
                                        zIndex: 1000
                                    }}
                                >
                                    <div
                                        className="state-tooltip"
                                        style={{
                                            position: 'relative',
                                            transform: `translate(${tooltipPosition.align === 'left' ? 'calc(-100% - 12px)' : '12px'}, calc(-100% - 12px))`,
                                            background: 'hsl(228, 15%, 9%)',
                                            border: '1px solid hsl(var(--border))',
                                            borderRadius: 'var(--radius-md)',
                                            padding: '0.75rem 1rem',
                                            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
                                            minWidth: '180px'
                                        }}
                                    >
                                        <div className="tooltip-header">
                                            <MapPin size={16} />
                                            <strong>{hoveredStateData.name}</strong>
                                        </div>
                                        <div className="tooltip-content">
                                            <div className="tooltip-row">
                                                <span>Submissions:</span>
                                                <strong>{hoveredStateData.count.toLocaleString()}</strong>
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {/* AI Analysis Chat Button (Inside Map) */}
                        {!showChatPanel && (
                            <div style={{
                                position: 'absolute',
                                bottom: '1.5rem',
                                right: '1.5rem',
                                zIndex: 50
                            }}>
                                <button
                                    className="analyze-button"
                                    onClick={handleOpenChat}
                                    disabled={isSending}
                                    style={{
                                        background: 'hsl(217, 91%, 60%)',
                                        color: 'white',
                                        border: 'none',
                                        boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                                        padding: '0.6rem 1.25rem',
                                        borderRadius: '8px',
                                        fontSize: '0.875rem'
                                    }}
                                >
                                    {isLoadingContext ? (
                                        <>
                                            <Loader2 size={18} className="spinning" />
                                            Loading...
                                        </>
                                    ) : (
                                        <>
                                            <MessageSquare size={18} />
                                            AI Analysis Chat
                                        </>
                                    )}
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {/* Chat Panel */}
                <AnimatePresence>
                    {showChatPanel && (
                        <motion.div
                            className="chat-panel"
                            initial={{ opacity: 0, x: 30, scale: 0.95 }}
                            animate={{ opacity: 1, x: 0, scale: 1 }}
                            exit={{ opacity: 0, x: 30, scale: 0.95 }}
                            transition={{ duration: 0.3, ease: 'easeOut' }}
                        >
                            {/* Chat Header */}
                            <div className="chat-header">
                                <div className="chat-header-left">
                                    <div className="chat-header-icon">
                                        <Sparkles size={18} />
                                    </div>
                                    <div>
                                        <h4>AI Analysis</h4>
                                        <span className="chat-context-label">
                                            {contextData ? contextData.filter : 'Loading...'}
                                            {contextData && ` · ${contextData.total_providers} providers`}
                                        </span>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    <button
                                        className="chat-reset-btn"
                                        onClick={handleResetChat}
                                        title="New conversation"
                                    >
                                        <RotateCcw size={16} />
                                    </button>
                                    <button
                                        className="chat-reset-btn"
                                        onClick={handleOpenChat}
                                        title="Close Chat"
                                    >
                                        <X size={16} />
                                    </button>
                                </div>
                            </div>

                            {/* Chat Messages */}
                            <div className="chat-messages">
                                {chatMessages.length === 0 && !isSending && (
                                    <div className="chat-empty-state">
                                        <div className="chat-empty-icon">
                                            <Bot size={32} />
                                        </div>
                                        <h5>Healthcare Data Analyst</h5>
                                        <p>Ask me anything about your provider data, geographic distribution, or data quality metrics.</p>
                                        <div className="suggested-prompts">
                                            {SUGGESTED_PROMPTS.slice(0, 3).map((prompt, i) => (
                                                <button
                                                    key={i}
                                                    className="suggested-prompt-btn"
                                                    onClick={() => handleSendMessage(prompt)}
                                                >
                                                    {prompt}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {chatMessages.map((msg, idx) => (
                                    <motion.div
                                        key={idx}
                                        className={`chat-message ${msg.role}`}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ duration: 0.2, delay: 0.05 }}
                                    >
                                        {msg.role === 'system_notice' ? (
                                            <div className="system-notice">
                                                <Sparkles size={14} />
                                                <span>{msg.content}</span>
                                            </div>
                                        ) : (
                                            <>
                                                <div className="message-avatar">
                                                    {msg.role === 'user' ? (
                                                        <User size={16} />
                                                    ) : (
                                                        <Bot size={16} />
                                                    )}
                                                </div>
                                                <div className="message-body">
                                                    <div className="message-role">
                                                        {msg.role === 'user' ? 'You' : 'AI Analyst'}
                                                    </div>
                                                    <div
                                                        className="message-content"
                                                        dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
                                                    />
                                                </div>
                                            </>
                                        )}
                                    </motion.div>
                                ))}

                                {isSending && (
                                    <motion.div
                                        className="chat-message assistant"
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                    >
                                        <div className="message-avatar">
                                            <Bot size={16} />
                                        </div>
                                        <div className="message-body">
                                            <div className="message-role">AI Analyst</div>
                                            <div className="typing-indicator">
                                                <span></span>
                                                <span></span>
                                                <span></span>
                                            </div>
                                        </div>
                                    </motion.div>
                                )}

                                <div ref={chatEndRef} />
                            </div>

                            {/* Suggested Follow-ups (show after first exchange) */}
                            {chatMessages.length >= 2 && !isSending && (
                                <div className="chat-suggestions-bar">
                                    {SUGGESTED_PROMPTS.filter(p => !chatMessages.find(m => m.content === p))
                                        .slice(0, 2)
                                        .map((prompt, i) => (
                                            <button
                                                key={i}
                                                className="suggestion-chip"
                                                onClick={() => handleSendMessage(prompt)}
                                            >
                                                {prompt}
                                            </button>
                                        ))}
                                </div>
                            )}

                            {/* Chat Input */}
                            <div className="chat-input-area">
                                <div className="chat-input-wrapper">
                                    <input
                                        ref={inputRef}
                                        type="text"
                                        className="chat-input"
                                        placeholder="Ask about your provider data..."
                                        value={chatInput}
                                        onChange={(e) => setChatInput(e.target.value)}
                                        onKeyDown={handleKeyDown}
                                        disabled={isSending}
                                    />
                                    <button
                                        className="chat-send-btn"
                                        onClick={() => handleSendMessage()}
                                        disabled={!chatInput.trim() || isSending}
                                    >
                                        {isSending ? (
                                            <Loader2 size={18} className="spinning" />
                                        ) : (
                                            <Send size={18} />
                                        )}
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </motion.div>
    );
};

export default USMapAnalysis;
