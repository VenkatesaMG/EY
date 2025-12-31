import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { UserPlus, LayoutDashboard, Sparkles, Map } from 'lucide-react';
import './App.css';
import OnboardingForm from './OnboardingForm';
import Dashboard from './Dashboard';
import ProviderDetail from './ProviderDetail';
import AnalysisPage from './AnalysisPage';

const pageVariants = {
  initial: {
    opacity: 0,
    y: 20,
  },
  in: {
    opacity: 1,
    y: 0,
  },
  out: {
    opacity: 0,
    y: -20,
  }
};

const pageTransition = {
  type: 'tween',
  ease: 'anticipate',
  duration: 0.4
};

function App() {
  const [view, setView] = useState('onboard');
  const [selectedProviderId, setSelectedProviderId] = useState(null);

  const handleSelectProvider = (id) => {
    setSelectedProviderId(id);
    setView('detail');
  };

  const handleNavClick = (newView) => {
    setView(newView);
    if (newView !== 'detail') {
      setSelectedProviderId(null);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Sparkles size={20} style={{ opacity: 0.8 }} />
            HealthValidator.ai
          </span>
        </h1>
        <nav>
          <button
            className={view === 'onboard' ? 'active' : ''}
            onClick={() => handleNavClick('onboard')}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <UserPlus size={16} />
              Onboard New
            </span>
          </button>
          <button
            className={view === 'dashboard' || view === 'detail' ? 'active' : ''}
            onClick={() => handleNavClick('dashboard')}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <LayoutDashboard size={16} />
              Dashboard
            </span>
          </button>
          <button
            className={view === 'analysis' ? 'active' : ''}
            onClick={() => handleNavClick('analysis')}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Map size={16} />
              Analysis
            </span>
          </button>
        </nav>
      </header>

      <main className="App-content">
        <AnimatePresence mode="wait">
          {view === 'onboard' && (
            <motion.div
              key="onboard"
              initial="initial"
              animate="in"
              exit="out"
              variants={pageVariants}
              transition={pageTransition}
            >
              <OnboardingForm />
            </motion.div>
          )}

          {view === 'dashboard' && (
            <motion.div
              key="dashboard"
              initial="initial"
              animate="in"
              exit="out"
              variants={pageVariants}
              transition={pageTransition}
            >
              <Dashboard 
                onSelectProvider={handleSelectProvider}
                onNavigateToAnalysis={() => handleNavClick('analysis')}
              />
            </motion.div>
          )}

          {view === 'detail' && selectedProviderId && (
            <motion.div
              key="detail"
              initial="initial"
              animate="in"
              exit="out"
              variants={pageVariants}
              transition={pageTransition}
            >
              <ProviderDetail
                providerId={selectedProviderId}
                onBack={() => handleNavClick('dashboard')}
              />
            </motion.div>
          )}

          {view === 'analysis' && (
            <motion.div
              key="analysis"
              initial="initial"
              animate="in"
              exit="out"
              variants={pageVariants}
              transition={pageTransition}
            >
              <AnalysisPage />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer style={{
        padding: '1.5rem 2rem',
        borderTop: '1px solid hsl(228, 12%, 18%)',
        textAlign: 'center',
        fontSize: '0.8125rem',
        color: 'hsl(228, 8%, 40%)'
      }}>
        <p style={{ margin: 0 }}>
          © 2024 HealthValidator.ai — Powered by AI-driven data validation
        </p>
      </footer>
    </div>
  );
}

export default App;
