import React, { useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Sparkles, MapPin, Maximize, Minimize } from 'lucide-react';
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

const USMapAnalysis = () => {
    const [hoveredFIPS, setHoveredFIPS] = useState(null);
    const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
    const [mapRef, setMapRef] = useState(null);
    const [containerRef, setContainerRef] = useState(null);
    const [analysisResult, setAnalysisResult] = useState(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);

    // UI State
    const [showAnalysisPanel, setShowAnalysisPanel] = useState(false);
    const [isFullscreen, setIsFullscreen] = useState(false);

    // Real Data State
    const [stateStats, setStateStats] = useState({});

    // Fetch Real Data on Mount
    React.useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await fetch('http://localhost:8000/analytics/geo-distribution');
                const counts = await res.json();

                // Merge with static metadata
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
    }, []);

    // Handle Fullscreen changes
    React.useEffect(() => {
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
                "#dbeafe", // lightest blue
                "#bfdbfe",
                "#93c5fd",
                "#60a5fa",
                "#3b82f6", // medium blue
                "#1d4ed8"  // darkest blue
            ]);
    }, [stateStats]);

    // Handle mouse move for tooltip positioning with edge detection
    const handleMouseMove = useCallback((event) => {
        if (mapRef) {
            const rect = mapRef.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;

            // Check if we are past 60% of the width
            const isNearRight = x > (rect.width * 0.6);

            setTooltipPosition({
                x: x,
                y: y,
                align: isNearRight ? 'left' : 'right'
            });
        }
    }, [mapRef]);

    const handleAnalyzeToggle = async () => {
        const willShow = !showAnalysisPanel;
        setShowAnalysisPanel(willShow);

        // If opening and no result, fetch it automatically
        if (willShow && !analysisResult && !isAnalyzing) {
            handleRunAnalysis();
        }
    };

    const handleRunAnalysis = async () => {
        setIsAnalyzing(true);
        setAnalysisResult(null);

        try {
            // Prepare Real Data for Analysis
            const activeStates = Object.entries(stateStats)
                .filter(([_, data]) => data.count > 0)
                .map(([abbr, data]) => ({
                    state: data.name,
                    abbr: abbr,
                    submissions: data.count
                }))
                .sort((a, b) => b.submissions - a.submissions);

            const summary = {
                totalStates: activeStates.length,
                totalSubmissions: activeStates.reduce((acc, curr) => acc + curr.submissions, 0),
                totalProviders: activeStates.reduce((acc, curr) => acc + curr.submissions, 0),
                topStates: activeStates.slice(0, 5)
            };

            const res = await fetch('http://localhost:8000/analyze/map-data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    summary,
                    states: activeStates
                })
            });

            const result = await res.json();
            if (result.success) {
                setAnalysisResult(result.analysis);
            } else {
                setAnalysisResult("Analysis failed to generate insights.");
            }

        } catch (e) {
            console.error("Analysis failed", e);
            setAnalysisResult("Error connecting to analysis service.");
        } finally {
            setIsAnalyzing(false);
        }
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
                <h3>Geographic Analysis</h3>
                <p style={{ color: 'hsl(228, 8%, 55%)', fontSize: '0.875rem', marginTop: '0.5rem' }}>
                    Provider submissions and distribution across US states
                </p>
            </div>

            {/* Layout Wrapper: Full or Split */}
            <div className="map-analysis-layout" style={{
                display: 'grid',
                gridTemplateColumns: showAnalysisPanel ? '3fr 1fr' : '1fr',
                gap: showAnalysisPanel ? '1.5rem' : '0',
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
                            height: isFullscreen ? '100%' : '550px',
                            minHeight: isFullscreen ? '0' : '550px'
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

                                            // Fallback point if geometry logic fails or simple check
                                            // Ideally use centroid, here using a simplified check for robustness
                                            // For now, skipping complex centroid content to keep it simple as before
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
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '1rem' }}>
                        <div className="map-legend" style={{ margin: 0, padding: '0.75rem 1rem', display: isFullscreen ? 'none' : 'flex' }}>
                            <div className="legend-label" style={{ marginBottom: '0.5rem' }}>Submission Intensity</div>
                            <div className="legend-gradient">
                                <div className="legend-item"><div className="legend-color" style={{ background: "#dbeafe" }}></div><span>Low</span></div>
                                <div className="legend-item"><div className="legend-color" style={{ background: "#93c5fd" }}></div><span>Medium</span></div>
                                <div className="legend-item"><div className="legend-color" style={{ background: "#1d4ed8" }}></div><span>High</span></div>
                            </div>
                        </div>

                        <div className="analyze-section" style={{ marginLeft: 'auto' }}>
                            <button
                                className="analyze-button"
                                onClick={handleAnalyzeToggle}
                                disabled={isAnalyzing && !showAnalysisPanel}
                                style={{
                                    background: showAnalysisPanel ? 'hsl(228, 12%, 18%)' : 'hsl(var(--primary))',
                                    color: showAnalysisPanel ? 'hsl(var(--foreground))' : 'white',
                                    border: showAnalysisPanel ? '1px solid hsl(var(--border))' : 'none'
                                }}
                            >
                                {isAnalyzing ? (
                                    <>
                                        <Loader2 size={18} className="spinning" />
                                        Analyzing...
                                    </>
                                ) : (
                                    <>
                                        <Sparkles size={18} />
                                        {showAnalysisPanel ? 'Close Analysis' : 'Analyze Map'}
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>

                <AnimatePresence>
                    {showAnalysisPanel && (
                        <motion.div
                            className="analysis-section-side"
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 20 }}
                            style={{
                                height: '100%',
                                overflowY: 'hidden',
                                display: 'flex',
                                flexDirection: 'column'
                            }}
                        >
                            {analysisResult ? (
                                <motion.div
                                    className="analysis-result"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    style={{ height: '100%', borderRadius: 'var(--radius-md)' }}
                                >
                                    <div className="analysis-header-section">
                                        <Sparkles size={20} color="#3b82f6" />
                                        <h4>Strategic Insights</h4>
                                    </div>
                                    <div className="analysis-content">
                                        {analysisResult}
                                    </div>
                                </motion.div>
                            ) : (
                                <motion.div
                                    className="analysis-placeholder"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    style={{ height: '100%' }}
                                >
                                    <div style={{
                                        display: 'flex',
                                        flexDirection: 'column',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        height: '100%',
                                        padding: '2rem',
                                        textAlign: 'center',
                                        color: 'hsl(228, 8%, 55%)'
                                    }}>
                                        <Loader2 size={32} className="spinning" style={{ marginBottom: '1rem', opacity: 0.5 }} />
                                        <p>Generating insights...</p>
                                    </div>
                                </motion.div>
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </motion.div>
    );
};

export default USMapAnalysis;
