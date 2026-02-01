import React, { useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Sparkles, MapPin } from 'lucide-react';
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
    const [analysisResult, setAnalysisResult] = useState(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);

    // Real Data State
    const [stateStats, setStateStats] = useState({}); // { CA: { count: 10, providers: 50, name: "California" } }

    // Fetch Real Data on Mount
    React.useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await fetch('http://localhost:8000/analytics/geo-distribution');
                const counts = await res.json(); // { "CA": 5, "TX": 2 }

                // Merge with static metadata
                const mergedData = {};
                Object.keys(stateAbbrToFIPS).forEach(abbr => {
                    const count = counts[abbr] || 0;
                    mergedData[abbr] = {
                        name: stateNames[abbr],
                        count: count,
                        providers: count * 1 // In real app, querying total providers vs submissions might differ
                    };
                });
                setStateStats(mergedData);
            } catch (e) {
                console.error("Failed to fetch geo stats", e);
            }
        };
        fetchData();

        // Poll every 5 seconds to keep map live
        const interval = setInterval(fetchData, 5000);
        return () => clearInterval(interval);
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

        // If all zero, return lightest blue or gray
        if (maxCount === 0) return () => "#f3f4f6";

        return scaleQuantize()
            .domain([minCount, maxCount || 1]) // Avoid domain [0,0]
            .range([
                "#dbeafe", // lightest blue
                "#bfdbfe",
                "#93c5fd",
                "#60a5fa",
                "#3b82f6", // medium blue
                "#1d4ed8"  // darkest blue
            ]);
    }, [stateStats]);

    // Handle mouse move for tooltip positioning
    const handleMouseMove = useCallback((event) => {
        if (mapRef) {
            const rect = mapRef.getBoundingClientRect();
            setTooltipPosition({
                x: event.clientX - rect.left,
                y: event.clientY - rect.top
            });
        }
    }, [mapRef]);

    const handleAnalyze = async () => {
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
                totalProviders: activeStates.reduce((acc, curr) => acc + curr.submissions, 0), // Simulating 1:1 for now
                topStates: activeStates.slice(0, 5)
            };

            // Call Gemini Analysis Endpoint
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

    const hoveredStateData = hoveredFIPS ? getStateData(hoveredFIPS) : null;

    return (
        <motion.div
            className="us-map-analysis-container"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
        >
            <div className="analysis-header">
                <h3>Geographic Analysis</h3>
                <p style={{ color: 'hsl(228, 8%, 55%)', fontSize: '0.875rem', marginTop: '0.5rem' }}>
                    Provider submissions and distribution across US states
                </p>
            </div>

            {/* Map and Analysis Side by Side */}
            <div className="map-analysis-layout">
                {/* Map Section */}
                <div className="map-section">
                    <div
                        ref={setMapRef}
                        className="map-container"
                        onMouseMove={handleMouseMove}
                    >
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
                                            const fillColor = count > 0 ? colorScale(count) : "#e5e7eb"; // Gray for no data

                                            return (
                                                <Geography
                                                    key={geo.rsmKey}
                                                    geography={geo}
                                                    fill={fillColor}
                                                    stroke={isHovered ? "#3b82f6" : "#fff"}
                                                    strokeWidth={isHovered ? 2 : 0.5}
                                                    style={{
                                                        default: {
                                                            outline: 'none',
                                                            cursor: 'pointer',
                                                            transition: 'all 0.2s ease',
                                                        },
                                                        hover: {
                                                            outline: 'none',
                                                            fill: isHovered ? fillColor : fillColor,
                                                            stroke: "#3b82f6",
                                                            strokeWidth: 2,
                                                        },
                                                        pressed: {
                                                            outline: 'none',
                                                        }
                                                    }}
                                                    onMouseEnter={() => {
                                                        setHoveredFIPS(fips);
                                                    }}
                                                    onMouseLeave={() => {
                                                        setHoveredFIPS(null);
                                                    }}
                                                />
                                            );
                                        })}

                                        {/* State Labels - Show abbreviation on hover */}
                                        {hoveredFIPS && (() => {
                                            const geo = geographies.find(g => g.id === hoveredFIPS);
                                            if (!geo) return null;
                                            const abbr = fipsToAbbr[hoveredFIPS];
                                            if (!abbr) return null;

                                            // Get coordinates from geography - robust centroid validation
                                            const geometry = geo.geometry;
                                            if (!geometry) return null;

                                            // Use centroid if available (some projections add it) or fallback to simple calculation
                                            // But finding a point on surface is safer:
                                            let candidatePoint = [0, 0];

                                            try {
                                                const coords = geometry.coordinates;
                                                if (!coords || coords.length === 0) return null;

                                                if (geometry.type === "Polygon") {
                                                    // coords[0] is the outer ring. coords[0][0] is the first point.
                                                    candidatePoint = coords[0][0];
                                                } else if (geometry.type === "MultiPolygon") {
                                                    // coords[0] is first Polygon. coords[0][0] is first ring. coords[0][0][0] is first point.
                                                    candidatePoint = coords[0][0][0];
                                                } else {
                                                    // fallback
                                                    return null;
                                                }

                                                // Ensure we have numbers
                                                if (!Array.isArray(candidatePoint) || candidatePoint.length < 2 || typeof candidatePoint[0] !== 'number') {
                                                    return null;
                                                }
                                            } catch (e) {
                                                return null;
                                            }

                                            return (
                                                <Annotation
                                                    key={`label-${hoveredFIPS}`}
                                                    subject={candidatePoint}
                                                    dx={0}
                                                    dy={0}
                                                >
                                                    <text
                                                        x={0}
                                                        y={0}
                                                        fontSize={12}
                                                        fontWeight={600}
                                                        fill="#3b82f6"
                                                        textAnchor="middle"
                                                        style={{
                                                            pointerEvents: 'none',
                                                            userSelect: 'none',
                                                            textShadow: '0 1px 2px rgba(0,0,0,0.3)'
                                                        }}
                                                    >
                                                        {abbr}
                                                    </text>
                                                </Annotation>
                                            );
                                        })()}
                                    </>
                                )}
                            </Geographies>
                        </ComposableMap>

                        {/* Tooltip */}
                        <AnimatePresence>
                            {hoveredFIPS && hoveredStateData && (
                                <motion.div
                                    className="state-tooltip"
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
                                        left: tooltipPosition.x + 10,
                                        top: tooltipPosition.y - 10,
                                        pointerEvents: 'none',
                                        zIndex: 1000,
                                        transform: 'translate(0, -100%)'
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
                                        <div className="tooltip-row">
                                            <span>Providers:</span>
                                            <strong>{hoveredStateData.providers.toLocaleString()}</strong>
                                        </div>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    {/* Legend */}
                    <div className="map-legend">
                        <div className="legend-label">Submission Intensity</div>
                        <div className="legend-gradient">
                            <div className="legend-item">
                                <div className="legend-color" style={{ background: "#dbeafe" }}></div>
                                <span>Low</span>
                            </div>
                            <div className="legend-item">
                                <div className="legend-color" style={{ background: "#93c5fd" }}></div>
                                <span>Medium</span>
                            </div>
                            <div className="legend-item">
                                <div className="legend-color" style={{ background: "#1d4ed8" }}></div>
                                <span>High</span>
                            </div>
                            <div className="legend-item">
                                <div className="legend-color" style={{ background: "#e5e7eb" }}></div>
                                <span>No Data</span>
                            </div>
                        </div>
                    </div>

                    {/* Analyze Button */}
                    <div className="analyze-section">
                        <button
                            className="analyze-button"
                            onClick={handleAnalyze}
                            disabled={isAnalyzing}
                        >
                            {isAnalyzing ? (
                                <>
                                    <Loader2 size={18} className="spinning" />
                                    Analyzing...
                                </>
                            ) : (
                                <>
                                    <Sparkles size={18} />
                                    Analyze Data
                                </>
                            )}
                        </button>
                    </div>
                </div>

                {/* Analysis Result Section */}
                <div className="analysis-section-side">
                    <AnimatePresence>
                        {analysisResult ? (
                            <motion.div
                                className="analysis-result"
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                            >
                                <div className="analysis-header-section">
                                    <Sparkles size={20} color="#3b82f6" />
                                    <h4>Strategic Recommendations</h4>
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
                                    <Sparkles size={48} style={{ marginBottom: '1rem', opacity: 0.3 }} />
                                    <h4 style={{ marginBottom: '0.5rem', color: 'hsl(228, 8%, 40%)' }}>
                                        Ready for Analysis
                                    </h4>
                                    <p style={{ fontSize: '0.875rem' }}>
                                        Click "Analyze Data" to view strategic expansion recommendations and identify areas for network growth.
                                    </p>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </motion.div>
    );
};

export default USMapAnalysis;
