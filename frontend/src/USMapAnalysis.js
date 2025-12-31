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

// Placeholder data for US states (using state abbreviations)
const stateDataByAbbr = {
    'AL': { name: 'Alabama', count: 245, providers: 1890 },
    'AK': { name: 'Alaska', count: 32, providers: 156 },
    'AZ': { name: 'Arizona', count: 512, providers: 3421 },
    'AR': { name: 'Arkansas', count: 198, providers: 1234 },
    'CA': { name: 'California', count: 3421, providers: 28456 },
    'CO': { name: 'Colorado', count: 456, providers: 3124 },
    'CT': { name: 'Connecticut', count: 234, providers: 1890 },
    'DE': { name: 'Delaware', count: 67, providers: 456 },
    'FL': { name: 'Florida', count: 1890, providers: 12345 },
    'GA': { name: 'Georgia', count: 678, providers: 4567 },
    'HI': { name: 'Hawaii', count: 89, providers: 567 },
    'ID': { name: 'Idaho', count: 123, providers: 789 },
    'IL': { name: 'Illinois', count: 890, providers: 6789 },
    'IN': { name: 'Indiana', count: 456, providers: 3456 },
    'IA': { name: 'Iowa', count: 234, providers: 1890 },
    'KS': { name: 'Kansas', count: 234, providers: 1789 },
    'KY': { name: 'Kentucky', count: 345, providers: 2345 },
    'LA': { name: 'Louisiana', count: 456, providers: 3456 },
    'ME': { name: 'Maine', count: 123, providers: 890 },
    'MD': { name: 'Maryland', count: 456, providers: 3456 },
    'MA': { name: 'Massachusetts', count: 567, providers: 4567 },
    'MI': { name: 'Michigan', count: 789, providers: 5678 },
    'MN': { name: 'Minnesota', count: 456, providers: 3456 },
    'MS': { name: 'Mississippi', count: 234, providers: 1789 },
    'MO': { name: 'Missouri', count: 567, providers: 4567 },
    'MT': { name: 'Montana', count: 89, providers: 567 },
    'NE': { name: 'Nebraska', count: 178, providers: 1234 },
    'NV': { name: 'Nevada', count: 234, providers: 1789 },
    'NH': { name: 'New Hampshire', count: 123, providers: 890 },
    'NJ': { name: 'New Jersey', count: 678, providers: 5678 },
    'NM': { name: 'New Mexico', count: 189, providers: 1234 },
    'NY': { name: 'New York', count: 1234, providers: 9876 },
    'NC': { name: 'North Carolina', count: 789, providers: 5678 },
    'ND': { name: 'North Dakota', count: 67, providers: 456 },
    'OH': { name: 'Ohio', count: 890, providers: 6789 },
    'OK': { name: 'Oklahoma', count: 345, providers: 2345 },
    'OR': { name: 'Oregon', count: 456, providers: 3456 },
    'PA': { name: 'Pennsylvania', count: 987, providers: 7890 },
    'RI': { name: 'Rhode Island', count: 89, providers: 567 },
    'SC': { name: 'South Carolina', count: 345, providers: 2345 },
    'SD': { name: 'South Dakota', count: 89, providers: 567 },
    'TN': { name: 'Tennessee', count: 567, providers: 4567 },
    'TX': { name: 'Texas', count: 2345, providers: 18901 },
    'UT': { name: 'Utah', count: 234, providers: 1789 },
    'VT': { name: 'Vermont', count: 67, providers: 456 },
    'VA': { name: 'Virginia', count: 678, providers: 5678 },
    'WA': { name: 'Washington', count: 567, providers: 4567 },
    'WV': { name: 'West Virginia', count: 189, providers: 1234 },
    'WI': { name: 'Wisconsin', count: 456, providers: 3456 },
    'WY': { name: 'Wyoming', count: 45, providers: 234 },
};

// Convert to FIPS-keyed data
const stateDataByFIPS = Object.fromEntries(
    Object.entries(stateDataByAbbr).map(([abbr, data]) => [
        stateAbbrToFIPS[abbr],
        data
    ])
);

const USMapAnalysis = () => {
    const [hoveredFIPS, setHoveredFIPS] = useState(null);
    const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
    const [mapRef, setMapRef] = useState(null);
    const [analysisResult, setAnalysisResult] = useState(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);

    // Calculate color scale using d3-scale
    const colorScale = useMemo(() => {
        const counts = Object.values(stateDataByFIPS).map(d => d.count);
        const minCount = Math.min(...counts);
        const maxCount = Math.max(...counts);
        
        return scaleQuantize()
            .domain([minCount, maxCount])
            .range([
                "#dbeafe", // lightest blue
                "#bfdbfe",
                "#93c5fd",
                "#60a5fa",
                "#3b82f6", // medium blue
                "#1d4ed8"  // darkest blue
            ]);
    }, []);

    // Get state data by FIPS
    const getStateData = (fips) => {
        return stateDataByFIPS[fips] || null;
    };

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

        // Simulate loading delay
        await new Promise(resolve => setTimeout(resolve, 1500));

        // Mock analysis suggestions for insurance company
        const mockAnalysis = `STRATEGIC EXPANSION RECOMMENDATIONS

Based on the geographic distribution analysis of your provider network, here are key insights and recommendations:

📍 HIGH-PRIORITY EXPANSION OPPORTUNITIES

1. TEXAS (TX) - Critical Gap Identified
   • Current Coverage: Strong presence (2,345 submissions)
   • Recommendation: Increase provider density in rural areas
   • Focus Areas: West Texas, Panhandle region
   • Department Priority: Primary Care and Emergency Medicine

2. CALIFORNIA (CA) - Market Leadership Opportunity
   • Current Coverage: Excellent (3,421 submissions)
   • Recommendation: Expand specialty care networks
   • Focus Areas: Central Valley, Inland Empire
   • Department Priority: Cardiology, Oncology, Mental Health

3. FLORIDA (FL) - Growing Market
   • Current Coverage: Strong (1,890 submissions)
   • Recommendation: Enhance geriatric care networks
   • Focus Areas: Southwest Florida, Treasure Coast
   • Department Priority: Geriatrics, Home Health Services

⚠️ DEPARTMENTS REQUIRING IMMEDIATE ATTENTION

1. MENTAL HEALTH SERVICES
   • Current Status: Underrepresented across 15+ states
   • Critical States: Montana, Wyoming, North Dakota, South Dakota
   • Action Required: Recruit 200+ mental health providers in underserved regions

2. PEDIATRIC SPECIALTY CARE
   • Current Status: Gaps in rural areas
   • Critical States: Arkansas, Mississippi, Alabama
   • Action Required: Establish pediatric specialty networks in 8 target markets

3. TELEHEALTH INFRASTRUCTURE
   • Current Status: Limited coverage in remote areas
   • Recommendation: Invest in telehealth partnerships
   • Target: 30% increase in virtual care providers

📊 REGIONAL STRATEGY

NORTHEAST REGION
• Strengths: Strong urban coverage
• Weaknesses: Rural access gaps
• Action: Expand into Maine, Vermont, New Hampshire rural markets

SOUTHWEST REGION
• Strengths: Growing presence in major metros
• Weaknesses: Specialty care gaps
• Action: Focus on oncology and cardiology networks

MIDWEST REGION
• Strengths: Consistent coverage
• Weaknesses: Limited specialty access
• Action: Partner with regional health systems

💡 QUICK WINS

1. Partner with existing high-performing providers in Texas and California
2. Launch telehealth initiatives in underserved states (MT, WY, ND, SD)
3. Recruit specialty providers in high-demand areas (Cardiology, Oncology)
4. Expand mental health network by 25% in next 6 months

These recommendations are based on current provider distribution patterns and market demand analysis.`;

        setAnalysisResult(mockAnalysis);
        setIsAnalyzing(false);
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
                                    
                                    // Get coordinates from geography - use a point from the geometry
                                    const coords = geo.coordinates;
                                    let centerX = 0, centerY = 0;
                                    
                                    if (coords && coords.length > 0) {
                                        // For polygons, get the first ring's first point as approximate center
                                        const firstRing = Array.isArray(coords[0][0]) ? coords[0] : coords;
                                        const firstPoint = firstRing[0];
                                        centerX = firstPoint[0];
                                        centerY = firstPoint[1];
                                    }
                                    
                                    return (
                                        <Annotation
                                            key={`label-${hoveredFIPS}`}
                                            subject={[centerX, centerY]}
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
