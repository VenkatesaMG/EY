import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    ChevronLeft, ChevronRight, Maximize2, Minimize2,
    Shield, Cpu, Sparkles, Users, Database, Globe,
    Mail, Search, FileCheck, Map, Brain, ArrowRight,
    CheckCircle, Zap, Lock, BarChart3, Layers,
    Activity, Target, Bot, Server, Play, Monitor
} from 'lucide-react';
import './App.css';

/* ─────────────── HELPER COMPONENTS ─────────────── */
function SlideHeader({ icon: Icon, title, subtitle, color }) {
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ width: 44, height: 44, borderRadius: 12, background: `${color}18`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Icon size={22} color={color} />
            </div>
            <div>
                <h2 style={{ fontSize: '1.65rem', fontWeight: 700, letterSpacing: '-0.03em', margin: 0 }}>{title}</h2>
                <p style={{ fontSize: '0.9rem', color: 'hsl(228,8%,55%)', margin: 0 }}>{subtitle}</p>
            </div>
        </div>
    );
}
function StatCard({ value, label, color, icon: Icon }) {
    return (
        <div style={{ background: 'hsl(228,12%,11%)', border: '1px solid hsl(228,12%,18%)', borderRadius: 14, padding: '1.5rem 1.25rem', textAlign: 'center', flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <Icon size={26} color={color} style={{ marginBottom: '0.5rem' }} />
            <div style={{ fontSize: '2.2rem', fontWeight: 800, color, letterSpacing: '-0.03em', lineHeight: 1.1 }}>{value}</div>
            <div style={{ fontSize: '0.8rem', color: 'hsl(228,8%,55%)', marginTop: '0.35rem', lineHeight: 1.4 }}>{label}</div>
        </div>
    );
}
function ArchBox({ title, color, items }) {
    return (
        <div style={{ background: 'hsl(228,12%,11%)', border: '1px solid hsl(228,12%,18%)', borderRadius: 14, padding: '1.25rem', borderTop: `3px solid ${color}`, flex: 1, display: 'flex', flexDirection: 'column' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.6rem', color }}>{title}</h3>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-evenly' }}>
                {items.map((item, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.4rem 0', fontSize: '0.85rem', color: 'hsl(228,8%,65%)' }}>
                        <div style={{ width: 5, height: 5, borderRadius: '50%', background: color, flexShrink: 0 }} />
                        {item}
                    </div>
                ))}
            </div>
        </div>
    );
}
function TechGroup({ title, color, items }) {
    return (
        <div style={{ background: 'hsl(228,12%,11%)', border: '1px solid hsl(228,12%,18%)', borderRadius: 12, padding: '1rem', flex: 1, display: 'flex', flexDirection: 'column' }}>
            <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color, marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{title}</h4>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-evenly' }}>
                {items.map((item, i) => (
                    <div key={i} style={{ padding: '0.45rem 0', borderBottom: i < items.length - 1 ? '1px solid hsl(228,12%,16%)' : 'none' }}>
                        <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'hsl(0,0%,90%)' }}>{item.name}</div>
                        <div style={{ fontSize: '0.75rem', color: 'hsl(228,8%,50%)' }}>{item.why}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}
function ImpactCard({ stakeholder, benefit, icon: Icon, color }) {
    return (
        <div style={{ background: 'hsl(228,12%,11%)', border: '1px solid hsl(228,12%,18%)', borderRadius: 14, padding: '1.5rem', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', gap: '0.75rem', flex: 1 }}>
            <div style={{ width: 50, height: 50, borderRadius: 14, background: `${color}18`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Icon size={24} color={color} />
            </div>
            <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>{stakeholder}</div>
            <div style={{ fontSize: '0.875rem', color: 'hsl(228,8%,55%)', lineHeight: 1.5 }}>{benefit}</div>
        </div>
    );
}
function MiniStat({ value, label, color }) {
    return (
        <div style={{ background: 'hsl(228,12%,11%)', border: '1px solid hsl(228,12%,18%)', borderRadius: 10, padding: '1rem 0.85rem', textAlign: 'center', flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color }}>{value}</div>
            <div style={{ fontSize: '0.72rem', color: 'hsl(228,8%,50%)', marginTop: 3 }}>{label}</div>
        </div>
    );
}

/* ─────────────── SLIDE DATA ─────────────── */
/* CORE: slides 0-2 (present these first) → slide 3 = DEMO → slides 4+ = appendix */
const DEMO_SLIDE_INDEX = 3;

const slides = [
    /* ========== SLIDE 0 — Problem + What We Built (COMBINED OPENER) ========== */
    {
        id: 'problem-solution',
        category: 'CORE',
        render: () => (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div style={{ width: 44, height: 44, borderRadius: 12, background: '#3b82f618', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Shield size={22} color="#3b82f6" />
                    </div>
                    <div>
                        <h2 style={{ fontSize: '1.65rem', fontWeight: 700, letterSpacing: '-0.03em', margin: 0, background: 'linear-gradient(135deg, #fff 30%, #60a5fa 70%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>HealthValidator.ai</h2>
                        <p style={{ fontSize: '0.85rem', color: 'hsl(228,8%,55%)', margin: 0 }}>AI-Powered Healthcare Provider Data Validation & Enrichment</p>
                    </div>
                </div>
                {/* Problem stats */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
                    <StatCard value="52%" label="Provider directories have inaccuracies" color="#ef4444" icon={Activity} />
                    <StatCard value="$100/day" label="CMS fine per violation per provider" color="#f59e0b" icon={BarChart3} />
                    <StatCard value="10M+" label="Providers in NPPES Registry" color="#3b82f6" icon={Users} />
                </div>
                {/* Our solution pipeline */}
                <div style={{ background: 'hsl(228,12%,11%)', border: '1px solid hsl(228,12%,18%)', borderRadius: 14, padding: '1.25rem', flex: 1, display: 'flex', flexDirection: 'column' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.6rem', color: '#60a5fa' }}>🚀 Our Solution — Complete Lifecycle</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', flex: 1, alignContent: 'space-evenly' }}>
                        {[
                            { icon: FileCheck, label: 'Multi-modal Ingestion', desc: 'Form, PDF/OCR, CSV batch', color: '#3b82f6' },
                            { icon: Shield, label: 'NPI Verification', desc: 'Real-time NPPES Registry lookup', color: '#8b5cf6' },
                            { icon: Brain, label: 'Hybrid AI Validation', desc: 'Deterministic + LLM comparison', color: '#06b6d4' },
                            { icon: Globe, label: 'Auto Enrichment', desc: 'Web scraping + Hunter.io email', color: '#10b981' },
                            { icon: Mail, label: 'Provider Verification', desc: 'Email-based self-service portal', color: '#f59e0b' },
                            { icon: Lock, label: 'Governance & Audit', desc: 'Field-level audit trail + scoring', color: '#ef4444' },
                        ].map((s, i) => (
                            <div key={i} style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', padding: '0.65rem 0.75rem', borderRadius: 10, background: `${s.color}0a`, border: `1px solid ${s.color}15` }}>
                                <s.icon size={18} color={s.color} style={{ flexShrink: 0 }} />
                                <div>
                                    <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>{s.label}</div>
                                    <div style={{ fontSize: '0.75rem', color: 'hsl(228,8%,50%)' }}>{s.desc}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        ),
    },

    /* ========== SLIDE 1 — Architecture + Innovation ========== */
    {
        id: 'architecture-innovation',
        category: 'CORE',
        render: () => (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                <SlideHeader icon={Cpu} title="Architecture & Innovation" subtitle="Multi-Agent AI System — What Makes Us Unique" color="#8b5cf6" />
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                    <ArchBox title="4 AI Agents" color="#f59e0b" items={['🔍 Extractor — OCR + LLM (PDF/Image → JSON)', '🌐 Enrichment — DuckDuckGo + Selenium + Hunter.io', '✉️ Email — SMTP token-based verification', '📊 Network Gap — ReAct agent + geodesic analysis']} />
                    <ArchBox title="Tech Stack" color="#3b82f6" items={['Frontend: React 19 + Framer Motion + D3 Maps', 'Backend: FastAPI (async) + SQLAlchemy 2.0', 'LLM: Groq Cloud — Llama 3.3 70B (~200 tok/s)', 'DB: PostgreSQL (6 tables) + asyncpg']} />
                </div>
                {/* Key innovations */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem', flex: 1, alignContent: 'stretch' }}>
                    {[
                        { title: 'Hybrid Validation', desc: 'Levenshtein + Jaccard + LLM semantic analysis combined', icon: Shield, color: '#06b6d4' },
                        { title: 'Closed-Loop Verification', desc: 'Providers self-correct via secure email portal', icon: Mail, color: '#10b981' },
                        { title: 'Auto Enrichment', desc: 'Don\'t just flag gaps — actively find missing data from the web', icon: Search, color: '#f59e0b' },
                    ].map((item, i) => (
                        <div key={i} style={{ background: 'hsl(228,12%,11%)', border: '1px solid hsl(228,12%,18%)', borderRadius: 12, padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', justifyContent: 'center' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <item.icon size={16} color={item.color} />
                                <span style={{ fontWeight: 700, fontSize: '0.9rem', color: item.color }}>{item.title}</span>
                            </div>
                            <span style={{ fontSize: '0.78rem', color: 'hsl(228,8%,55%)', lineHeight: 1.45 }}>{item.desc}</span>
                        </div>
                    ))}
                </div>
                <div style={{ background: 'linear-gradient(135deg, hsl(217,60%,25%,0.3), hsl(199,50%,20%,0.2))', border: '1px solid hsl(217,60%,30%,0.4)', borderRadius: 10, padding: '0.75rem 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <Zap size={18} color="#f59e0b" />
                    <span style={{ fontSize: '0.85rem', color: 'hsl(228,8%,70%)' }}>
                        <strong style={{ color: '#fbbf24' }}>Confidence Scoring:</strong> Records below 70% auto-flagged for human review. Every field change logged in immutable audit trail.
                    </span>
                </div>
            </div>
        ),
    },

    /* ========== SLIDE 2 — Impact & Benefit ========== */
    {
        id: 'impact',
        category: 'CORE',
        render: () => (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                <SlideHeader icon={Users} title="Impact & End-User Benefit" subtitle="Who Benefits, How It Scales" color="#10b981" />
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem', flex: 1 }}>
                    <ImpactCard stakeholder="Health Plan Ops" benefit="Saves hundreds of man-hours per directory update cycle" icon={BarChart3} color="#3b82f6" />
                    <ImpactCard stakeholder="Compliance Teams" benefit="Full audit trail for CMS audits & No Surprises Act" icon={Shield} color="#10b981" />
                    <ImpactCard stakeholder="Patients" benefit="Right doctor, right location, first try — no more misdirection" icon={Users} color="#ec4899" />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '0.6rem' }}>
                    <MiniStat value="Seconds" label="Per-provider validation (was hours)" color="#3b82f6" />
                    <MiniStat value="Auto-fill" label="Missing email, phone, website" color="#10b981" />
                    <MiniStat value="< 70%" label="Auto-flags for human review" color="#f59e0b" />
                    <MiniStat value="100%" label="Field-level audit coverage" color="#8b5cf6" />
                </div>
                <div style={{ background: 'hsl(228,12%,11%)', border: '1px solid hsl(228,12%,18%)', borderRadius: 14, padding: '1.25rem', flex: 1 }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem', color: '#34d399' }}>✨ Self-Improving Data Ecosystem</h3>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                        {['Ingest', 'Validate (NPPES)', 'Enrich (Web)', 'Email Provider', 'Provider Corrects', 'Audit Logged', 'Data Improves'].map((step, i) => (
                            <React.Fragment key={i}>
                                <span style={{ padding: '0.4rem 0.75rem', borderRadius: 8, background: i === 6 ? '#10b98122' : 'hsl(228,12%,14%)', border: `1px solid ${i === 6 ? '#10b98144' : 'hsl(228,12%,22%)'}`, fontSize: '0.8rem', color: i === 6 ? '#34d399' : 'hsl(228,8%,65%)', fontWeight: 500 }}>{step}</span>
                                {i < 6 && <ArrowRight size={12} color="hsl(228,8%,30%)" />}
                            </React.Fragment>
                        ))}
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'hsl(228,8%,50%)', marginTop: '0.75rem', lineHeight: 1.5 }}>
                        Providers themselves verify data via secure email links — directories get more accurate over time without manual effort.
                    </p>
                </div>
            </div>
        ),
    },

    /* ========== SLIDE 3 — DEMO TIME ========== */
    {
        id: 'demo',
        category: null,
        render: () => (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', textAlign: 'center', gap: '2.5rem' }}>
                <div style={{ width: 90, height: 90, borderRadius: '50%', background: 'linear-gradient(135deg, #3b82f6, #06b6d4)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 60px rgba(59,130,246,0.35)', animation: 'pulse 2s ease-in-out infinite' }}>
                    <Monitor size={44} color="#fff" />
                </div>
                <h1 style={{ fontSize: '3.5rem', fontWeight: 800, letterSpacing: '-0.04em', background: 'linear-gradient(135deg, #fff 30%, #60a5fa 70%, #06b6d4)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                    Live Demo
                </h1>
                <p style={{ fontSize: '1.2rem', color: 'hsl(228,8%,55%)', maxWidth: 500, lineHeight: 1.7 }}>
                    Let's see HealthValidator.ai in action — onboarding, validation, enrichment, and analytics.
                </p>
                <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.5rem' }}>
                    {[
                        { label: 'CSV Upload → Pipeline', color: '#3b82f6' },
                        { label: 'Provider Drill-down', color: '#8b5cf6' },
                        { label: 'Enrichment', color: '#10b981' },
                        { label: 'AI Map Chat', color: '#f59e0b' },
                    ].map((d, i) => (
                        <div key={i} style={{ padding: '0.5rem 1rem', borderRadius: 10, background: `${d.color}15`, border: `1px solid ${d.color}30`, fontSize: '0.85rem', color: d.color, fontWeight: 600 }}>
                            {d.label}
                        </div>
                    ))}
                </div>
                <p style={{ fontSize: '0.8rem', color: 'hsl(228,8%,35%)', marginTop: '1rem' }}>Navigate to other tabs ← to show the live product</p>
            </div>
        ),
    },

    /* ======== APPENDIX SLIDES (if time permits) ======== */

    /* 4 — Deep-dive: Validation Pipeline */
    {
        id: 'validation',
        category: 'Appendix',
        render: () => (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <SlideHeader icon={Shield} title="Hybrid Validation Pipeline" subtitle="Deterministic + AI for Maximum Accuracy" color="#06b6d4" />
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem', flex: 1 }}>
                    <div style={{ background: 'hsl(228,12%,11%)', border: '1px solid hsl(228,12%,18%)', borderRadius: 14, padding: '1.5rem' }}>
                        <h3 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '1rem', color: '#06b6d4', display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Cpu size={18} /> Deterministic Matching</h3>
                        {[{ algo: 'Levenshtein Distance', use: 'Fuzzy name matching' }, { algo: 'Jaccard Similarity', use: 'Address comparison (set-based)' }, { algo: 'Exact Match', use: 'NPI number & taxonomy codes' }].map((a, i) => (
                            <div key={i} style={{ padding: '0.75rem', borderRadius: 8, background: 'hsl(199,50%,20%,0.2)', border: '1px solid hsl(199,50%,20%,0.3)', marginBottom: '0.5rem' }}>
                                <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#22d3ee' }}>{a.algo}</div>
                                <div style={{ fontSize: '0.8rem', color: 'hsl(228,8%,55%)', marginTop: 2 }}>{a.use}</div>
                            </div>
                        ))}
                    </div>
                    <div style={{ background: 'hsl(228,12%,11%)', border: '1px solid hsl(228,12%,18%)', borderRadius: 14, padding: '1.5rem' }}>
                        <h3 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '1rem', color: '#a78bfa', display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Brain size={18} /> LLM Semantic Analysis</h3>
                        {[{ feat: 'Field-by-field comparison', detail: 'Name, address, phone, specialty' }, { feat: 'Per-field confidence scores', detail: '0-100% with reasoning' }, { feat: 'Issue identification', detail: 'phone_mismatch, city_mismatch, etc.' }, { feat: 'Natural language explanation', detail: 'Human-readable validation report' }].map((f, i) => (
                            <div key={i} style={{ padding: '0.75rem', borderRadius: 8, background: 'hsl(270,50%,20%,0.15)', border: '1px solid hsl(270,50%,20%,0.25)', marginBottom: '0.5rem' }}>
                                <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#c4b5fd' }}>{f.feat}</div>
                                <div style={{ fontSize: '0.8rem', color: 'hsl(228,8%,55%)', marginTop: 2 }}>{f.detail}</div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        ),
    },

    /* 5 — Deep-dive: Tech Stack */
    {
        id: 'tech',
        category: 'Appendix',
        render: () => (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <SlideHeader icon={Server} title="Full Technology Stack" subtitle="Production-Grade Infrastructure" color="#10b981" />
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', flex: 1 }}>
                    <TechGroup title="AI / LLM" color="#a78bfa" items={[{ name: 'Groq Cloud API', why: 'Fastest inference (~200 tok/s)' }, { name: 'Llama 3.3 70B', why: 'Open-source, no vendor lock-in' }, { name: 'LangChain Core', why: 'Prompt templates + parsers' }]} />
                    <TechGroup title="Backend" color="#34d399" items={[{ name: 'FastAPI', why: 'Async REST framework' }, { name: 'SQLAlchemy 2.0', why: 'Async ORM' }, { name: 'asyncpg', why: 'Non-blocking PostgreSQL' }]} />
                    <TechGroup title="Frontend" color="#60a5fa" items={[{ name: 'React 19', why: 'Latest UI framework' }, { name: 'Framer Motion', why: 'Fluid transitions' }, { name: 'react-simple-maps', why: 'US choropleth map' }]} />
                    <TechGroup title="Data Sources" color="#f472b6" items={[{ name: 'NPPES Registry', why: 'Official CMS provider DB' }, { name: 'Hunter.io', why: 'Email discovery API' }, { name: 'DuckDuckGo', why: 'Web search for enrichment' }]} />
                    <TechGroup title="Scraping & OCR" color="#fbbf24" items={[{ name: 'Selenium', why: 'Headless Chrome' }, { name: 'Pytesseract', why: 'Image OCR' }, { name: 'PyPDF', why: 'PDF extraction' }]} />
                    <TechGroup title="Infrastructure" color="#fb923c" items={[{ name: 'PostgreSQL', why: '6 normalized tables' }, { name: 'Gmail SMTP', why: 'Email verification' }, { name: 'Uvicorn', why: 'ASGI server' }]} />
                </div>
            </div>
        ),
    },

    /* 6 — Deep-dive: Governance */
    {
        id: 'governance',
        category: 'Appendix',
        render: () => (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <SlideHeader icon={Database} title="Data Governance & Audit Trail" subtitle="Enterprise-Grade Data Integrity" color="#ef4444" />
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem', flex: 1 }}>
                    <div style={{ background: 'hsl(228,12%,11%)', border: '1px solid hsl(228,12%,18%)', borderRadius: 14, padding: '1.5rem' }}>
                        <h3 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '1rem', color: '#60a5fa' }}>📊 6 Normalized Tables</h3>
                        {[{ table: 'providers_master_per', desc: 'Personal info' }, { table: 'providers_master_prof', desc: 'Professional info' }, { table: 'providers_master_meta', desc: 'Validation metadata' }, { table: 'raw_provider_submissions', desc: 'Submission log' }, { table: 'provider_audit_log', desc: 'Change history' }, { table: 'market_expansion_opportunities', desc: 'Gap analytics' }].map((t, i) => (
                            <div key={i} style={{ display: 'flex', gap: '0.75rem', padding: '0.5rem 0', borderBottom: i < 5 ? '1px solid hsl(228,12%,16%)' : 'none' }}>
                                <code style={{ fontSize: '0.7rem', color: '#60a5fa', background: 'hsl(217,60%,25%,0.2)', padding: '0.15rem 0.5rem', borderRadius: 4, fontFamily: 'monospace', whiteSpace: 'nowrap', height: 'fit-content' }}>{t.table}</code>
                                <span style={{ fontSize: '0.8rem', color: 'hsl(228,8%,55%)' }}>{t.desc}</span>
                            </div>
                        ))}
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        <div style={{ background: 'hsl(228,12%,11%)', border: '1px solid hsl(228,12%,18%)', borderRadius: 14, padding: '1.25rem', flex: 1 }}>
                            <h3 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '0.75rem', color: '#f87171' }}>🔒 Governance Rules</h3>
                            {['NPI = source of truth for core fields', 'Enrichment only fills gaps, never overwrites', 'Conflicts resolved by rule hierarchy', 'Records < 70% confidence → human review'].map((r, i) => (
                                <div key={i} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', padding: '0.4rem 0' }}><CheckCircle size={14} color="#10b981" /><span style={{ fontSize: '0.85rem', color: 'hsl(228,8%,65%)' }}>{r}</span></div>
                            ))}
                        </div>
                        <div style={{ background: 'hsl(228,12%,11%)', border: '1px solid hsl(228,12%,18%)', borderRadius: 14, padding: '1.25rem', flex: 1 }}>
                            <h3 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '0.75rem', color: '#fbbf24' }}>📝 Audit Trail Logs</h3>
                            {['Field name + table name', 'Old value → New value', 'Source (NPI / enrichment / provider)', 'Actor + timestamp'].map((f, i) => (
                                <div key={i} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', padding: '0.35rem 0' }}><div style={{ width: 6, height: 6, borderRadius: '50%', background: '#fbbf24', flexShrink: 0 }} /><span style={{ fontSize: '0.85rem', color: 'hsl(228,8%,65%)' }}>{f}</span></div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        ),
    },

    /* 7 — Thank You */
    {
        id: 'thankyou',
        category: null,
        render: () => (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', textAlign: 'center', gap: '2rem' }}>
                <div style={{ width: 80, height: 80, borderRadius: '50%', background: 'linear-gradient(135deg, #10b981, #06b6d4)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 60px rgba(16,185,129,0.3)' }}>
                    <CheckCircle size={40} color="#fff" />
                </div>
                <h1 style={{ fontSize: '3rem', fontWeight: 800, letterSpacing: '-0.04em', background: 'linear-gradient(135deg, #fff 30%, #34d399 70%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Thank You</h1>
                <p style={{ fontSize: '1.25rem', color: 'hsl(228,8%,55%)', maxWidth: 560, lineHeight: 1.6 }}>HealthValidator.ai — Built for smarter healthcare data governance</p>
                <div style={{ display: 'flex', gap: '2rem', marginTop: '1rem' }}>
                    {[{ label: 'Multi-Agent AI', color: '#3b82f6' }, { label: 'Hybrid Validation', color: '#06b6d4' }, { label: 'Self-Improving', color: '#10b981' }, { label: 'Audit-Ready', color: '#f59e0b' }].map((b, i) => (
                        <div key={i} style={{ textAlign: 'center' }}>
                            <div style={{ width: 48, height: 48, borderRadius: 12, background: `${b.color}18`, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 0.5rem' }}><Sparkles size={20} color={b.color} /></div>
                            <span style={{ fontSize: '0.8rem', color: b.color, fontWeight: 600 }}>{b.label}</span>
                        </div>
                    ))}
                </div>
                <p style={{ marginTop: '2rem', fontSize: '0.9rem', color: 'hsl(228,8%,40%)' }}>Questions? 🚀</p>
            </div>
        ),
    },
];

/* ──────────────────────── CATEGORY COLORS ─────────────────────────── */
const categoryColors = {
    'CORE': '#3b82f6',
    'Appendix': 'hsl(228,8%,40%)',
};

/* ───────────────────────── MAIN COMPONENT ─────────────────────────── */
const PresentationPage = () => {
    const [current, setCurrent] = useState(0);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const total = slides.length;

    const goNext = useCallback(() => setCurrent(c => Math.min(c + 1, total - 1)), [total]);
    const goPrev = useCallback(() => setCurrent(c => Math.max(c - 1, 0)), []);

    const toggleFullscreen = useCallback(() => {
        if (!document.fullscreenElement) document.documentElement.requestFullscreen?.();
        else document.exitFullscreen?.();
    }, []);

    useEffect(() => {
        const handler = (e) => {
            if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); goNext(); }
            if (e.key === 'ArrowLeft') { e.preventDefault(); goPrev(); }
            if (e.key === 'f' || e.key === 'F') toggleFullscreen();
            if (e.key === 'Escape' && document.fullscreenElement) document.exitFullscreen?.();
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [goNext, goPrev, toggleFullscreen]);

    useEffect(() => {
        const h = () => setIsFullscreen(!!document.fullscreenElement);
        document.addEventListener('fullscreenchange', h);
        return () => document.removeEventListener('fullscreenchange', h);
    }, []);

    const slide = slides[current];
    const cat = slide.category;
    const isCore = current < DEMO_SLIDE_INDEX;
    const isDemo = current === DEMO_SLIDE_INDEX;

    return (
        <div style={{
            height: isFullscreen ? '100vh' : 'calc(100vh - 140px)',
            display: 'flex', flexDirection: 'column',
            background: isFullscreen ? 'hsl(228,15%,6%)' : 'transparent',
            ...(isFullscreen ? { position: 'fixed', inset: 0, zIndex: 9999, padding: '1rem 1.5rem' } : {})
        }}>
            {/* Top bar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexShrink: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span style={{ fontSize: '0.8rem', color: 'hsl(228,8%,40%)', fontWeight: 600 }}>{current + 1} / {total}</span>
                    {isCore && <span style={{ padding: '0.2rem 0.6rem', borderRadius: 6, fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', background: '#3b82f618', color: '#3b82f6', border: '1px solid #3b82f633' }}>CORE PITCH</span>}
                    {isDemo && <span style={{ padding: '0.2rem 0.6rem', borderRadius: 6, fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', background: '#10b98118', color: '#10b981', border: '1px solid #10b98133' }}>DEMO TIME</span>}
                    {!isCore && !isDemo && cat === 'Appendix' && <span style={{ padding: '0.2rem 0.6rem', borderRadius: 6, fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', background: 'hsl(228,12%,14%)', color: 'hsl(228,8%,45%)', border: '1px solid hsl(228,12%,22%)' }}>DEEP DIVE</span>}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    {/* Dots with section separator */}
                    <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginRight: '0.75rem' }}>
                        {slides.map((_, i) => (
                            <React.Fragment key={i}>
                                {i === DEMO_SLIDE_INDEX && <div style={{ width: 1, height: 14, background: 'hsl(228,12%,25%)', margin: '0 3px' }} />}
                                <button
                                    onClick={() => setCurrent(i)}
                                    style={{
                                        width: i === current ? 20 : 8, height: 8, borderRadius: 4,
                                        background: i === current ? (i < DEMO_SLIDE_INDEX ? '#3b82f6' : i === DEMO_SLIDE_INDEX ? '#10b981' : 'hsl(228,8%,45%)') : 'hsl(228,12%,20%)',
                                        border: 'none', cursor: 'pointer', transition: 'all 0.3s', padding: 0,
                                    }}
                                    aria-label={`Slide ${i + 1}`}
                                />
                            </React.Fragment>
                        ))}
                    </div>
                    <button onClick={toggleFullscreen} style={{ background: 'hsl(228,12%,14%)', border: '1px solid hsl(228,12%,22%)', borderRadius: 8, padding: '0.4rem', cursor: 'pointer', display: 'flex', alignItems: 'center', color: 'hsl(228,8%,55%)' }}>
                        {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                    </button>
                </div>
            </div>

            {/* Progress */}
            <div style={{ height: 3, background: 'hsl(228,12%,14%)', borderRadius: 2, marginBottom: '0.5rem', flexShrink: 0, overflow: 'hidden' }}>
                <motion.div style={{ height: '100%', borderRadius: 2, background: isCore ? '#3b82f6' : isDemo ? '#10b981' : 'hsl(228,8%,35%)' }} animate={{ width: `${((current + 1) / total) * 100}%` }} transition={{ duration: 0.4, ease: 'easeInOut' }} />
            </div>

            {/* Content */}
            <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
                <AnimatePresence mode="wait">
                    <motion.div key={current} initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -40 }} transition={{ duration: 0.35, ease: 'easeInOut' }} style={{ height: '100%', padding: '0.25rem 0.25rem' }}>
                        {slide.render()}
                    </motion.div>
                </AnimatePresence>
            </div>

            {/* Nav */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.65rem', flexShrink: 0 }}>
                <button onClick={goPrev} disabled={current === 0} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.6rem 1.25rem', borderRadius: 10, background: current === 0 ? 'hsl(228,12%,11%)' : 'hsl(228,12%,14%)', border: '1px solid hsl(228,12%,22%)', color: current === 0 ? 'hsl(228,8%,30%)' : 'hsl(228,8%,70%)', cursor: current === 0 ? 'not-allowed' : 'pointer', fontSize: '0.85rem', fontWeight: 500, fontFamily: 'inherit', transition: 'all 0.2s' }}>
                    <ChevronLeft size={16} /> Previous
                </button>
                {current === DEMO_SLIDE_INDEX - 1 ? (
                    <button onClick={goNext} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.7rem 1.5rem', borderRadius: 10, background: 'linear-gradient(135deg, #10b981, #06b6d4)', border: 'none', color: '#fff', cursor: 'pointer', fontSize: '0.9rem', fontWeight: 700, fontFamily: 'inherit', boxShadow: '0 0 25px rgba(16,185,129,0.3)' }}>
                        <Play size={16} /> Start Demo
                    </button>
                ) : (
                    <button onClick={goNext} disabled={current === total - 1} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.6rem 1.25rem', borderRadius: 10, background: current === total - 1 ? 'hsl(228,12%,11%)' : 'linear-gradient(135deg, #3b82f6, #06b6d4)', border: current === total - 1 ? '1px solid hsl(228,12%,22%)' : 'none', color: current === total - 1 ? 'hsl(228,8%,30%)' : '#fff', cursor: current === total - 1 ? 'not-allowed' : 'pointer', fontSize: '0.85rem', fontWeight: 600, fontFamily: 'inherit', boxShadow: current === total - 1 ? 'none' : '0 0 20px rgba(59,130,246,0.2)' }}>
                        Next <ChevronRight size={16} />
                    </button>
                )}
            </div>
        </div>
    );
};

export default PresentationPage;
