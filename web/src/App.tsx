import React, { useState, useEffect } from 'react';
import { useAuth, AuthProvider } from './context/AuthContext';
import { Navbar, MainTabType } from './components/Navbar';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { ReportsPage } from './pages/ReportsPage';
import { PipelineQualityPage } from './pages/PipelineQualityPage';
import { FloatingChatWidget } from './components/FloatingChatWidget';
import { LiveToastNotification } from './components/LiveToastNotification';
import { ScreenCrackEffect } from './components/ScreenCrackEffect';
import { LoadingView } from './components/StateViews';
import { sseService, SSEStatus } from './services/sse';

const VALID_TABS: MainTabType[] = ['dashboard', 'reports', 'pipeline'];

const getAllowedTabs = (isAdmin: boolean): MainTabType[] =>
  isAdmin ? VALID_TABS : ['dashboard'];

const getTabFromHashOrStorage = (isAdmin: boolean): MainTabType => {
  const allowed = getAllowedTabs(isAdmin);
  if (typeof window !== 'undefined') {
    const rawHash = window.location.hash.replace('#', '').trim() as MainTabType;
    if (allowed.includes(rawHash)) {
      return rawHash;
    }
    const saved = localStorage.getItem('sismowatch_active_tab') as MainTabType;
    if (saved && allowed.includes(saved)) {
      return saved;
    }
  }
  return 'dashboard';
};

const MainLayout: React.FC = () => {
  const { user, loading, isAdmin } = useAuth();
  const [currentTab, setCurrentTab] = useState<MainTabType>(() => getTabFromHashOrStorage(isAdmin));
  const [sseStatus, setSseStatus] = useState<SSEStatus>('DISCONNECTED');

  const allowedTabs = getAllowedTabs(isAdmin);

  const handleSelectTab = (tab: MainTabType) => {
    if (!allowedTabs.includes(tab)) return;
    setCurrentTab(tab);
    if (typeof window !== 'undefined') {
      window.location.hash = tab;
      localStorage.setItem('sismowatch_active_tab', tab);
    }
  };

  useEffect(() => {
    const handleHashChange = () => {
      const hashTab = window.location.hash.replace('#', '').trim() as MainTabType;
      if (allowedTabs.includes(hashTab)) {
        setCurrentTab(hashTab);
        localStorage.setItem('sismowatch_active_tab', hashTab);
      } else {
        setCurrentTab('dashboard');
        if (typeof window !== 'undefined') window.location.hash = 'dashboard';
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, [allowedTabs]);

  useEffect(() => {
    if (user) {
      if (!allowedTabs.includes(currentTab)) {
        setCurrentTab('dashboard');
      }
      if (!window.location.hash) {
        window.location.hash = currentTab;
      }
      const unsubscribe = sseService.subscribe(
        () => {}, // Handled by LiveToastNotification and listeners
        (status) => setSseStatus(status)
      );
      return () => unsubscribe();
    } else {
      sseService.disconnect();
    }
  }, [user, allowedTabs, currentTab]);

  if (loading) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <LoadingView message="Iniciando Observatorio SismoWatch..." />
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return (
    <div className="min-h-screen bg-surface flex flex-col font-body-md text-on-surface">
      {/* Realtime Toast Notifications */}
      <LiveToastNotification />

      {/* Efecto de grietas en pantalla ante sismos/tsunamis en vivo */}
      <ScreenCrackEffect />

      {/* Top Navbar */}
      <Navbar
        sseStatus={sseStatus}
        currentTab={currentTab}
        onSelectTab={handleSelectTab}
      />

      {/* Main Full-Width Content Container with top offset for fixed navbar */}
      <main className="flex-1 w-full pt-16 bg-surface">
        <div className="py-space-md">
          {currentTab === 'dashboard' && <DashboardPage />}
          {isAdmin && currentTab === 'reports' && (
            <div className="max-w-7xl mx-auto px-margin py-space-xl">
              <ReportsPage />
            </div>
          )}
          {isAdmin && currentTab === 'pipeline' && (
            <div className="max-w-7xl mx-auto px-margin py-space-xl">
              <PipelineQualityPage />
            </div>
          )}
        </div>
      </main>

      {/* Observatory Footer */}
      <footer className="w-full bg-surface-container-low py-space-xl border-t border-outline-variant/20 mt-space-xl">
        <div className="max-w-7xl mx-auto px-margin text-center text-on-surface-variant text-body-sm font-label-md">
          &copy; 2026 SismoWatch Observatorio Global. Todos los derechos reservados.
        </div>
      </footer>

      {/* Floating Chatbot Widget (Bottom Right) */}
      <FloatingChatWidget />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <MainLayout />
    </AuthProvider>
  );
};

export default App;
