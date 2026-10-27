import React from 'react';
import { useAuth } from '../context/AuthContext';

export type MainTabType = 'dashboard' | 'reports' | 'pipeline';

interface NavbarProps {
  sseStatus: 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING';
  currentTab: MainTabType;
  onSelectTab: (tab: MainTabType) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ sseStatus, currentTab, onSelectTab }) => {
  const { user, logout, isAdmin } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  React.useEffect(() => {
    setMobileMenuOpen(false);
  }, [currentTab]);

  const getBeacon = () => {
    switch (sseStatus) {
      case 'CONNECTED':
        return {
          color: 'bg-emerald-400',
          text: 'EN VIVO',
          textCol: 'text-emerald-400',
        };
      case 'RECONNECTING':
      case 'CONNECTING':
        return {
          color: 'bg-amber-400',
          text: 'CONECTANDO',
          textCol: 'text-amber-400',
        };
      default:
        return {
          color: 'bg-error',
          text: 'DESCONECTADO',
          textCol: 'text-error',
        };
    }
  };

  const beacon = getBeacon();

  const navItems = [
    { id: 'dashboard' as MainTabType, label: 'Dashboard', path: 'dashboard' },
    ...(isAdmin
      ? [
          { id: 'reports' as MainTabType, label: 'Reportes e IA', path: 'reportes-ia' },
          { id: 'pipeline' as MainTabType, label: 'Pipeline y Calidad', path: 'pipeline-calidad' },
        ]
      : []),
  ];

  return (
    <header className="fixed top-0 w-full z-50 bg-surface/80 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.04)] border-b border-outline-variant/30">
      <div className="h-16 max-w-7xl mx-auto px-margin flex items-center justify-between">
        {/* Brand Logo & Isotypo */}
        <div className="flex items-center space-x-space-md">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-surface-container-high shadow-[0_0_15px_rgba(0,240,255,0.15)]">
            <span
              className="material-symbols-outlined text-primary animate-pulse"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              pulse_alert
            </span>
            <span className="absolute top-0 right-0 w-2.5 h-2.5 bg-primary-container rounded-full animate-ping"></span>
          </div>
          <div>
            <span className="text-headline-sm font-headline-sm text-primary tracking-wider uppercase block">
              SISMoWATCH
            </span>
            <span className="hidden sm:block text-label-sm font-label-sm text-on-surface-variant tracking-widest uppercase block">
              OBSERVATORIO GLOBAL
            </span>
          </div>
        </div>

        {/* Navigation Tabs (desktop) */}
        <nav
          className="hidden md:flex items-center space-x-space-sm bg-surface-container-low p-1 rounded-xl border border-outline-variant/20"
          data-active-classes="bg-primary-container text-on-primary-container font-bold"
        >
          {navItems.map((item) => {
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                data-path={item.path}
                className={`px-space-md py-1.5 rounded-lg text-label-md transition-all ${
                  isActive
                    ? 'bg-primary-container text-on-primary-container font-bold shadow-sm'
                    : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high'
                }`}
              >
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Hamburger (mobile): la navegación no debe desaparecer en pantallas pequeñas */}
        {navItems.length > 1 && (
          <button
            className="md:hidden p-2 rounded-lg bg-surface-container-low border border-outline-variant/30 text-on-surface-variant hover:text-on-surface transition-colors"
            onClick={() => setMobileMenuOpen((v) => !v)}
            data-path="menu-mobile"
            title="Menú de navegación"
            aria-label="Abrir menú"
            aria-expanded={mobileMenuOpen}
          >
            <span className="material-symbols-outlined text-[24px]">
              {mobileMenuOpen ? 'close' : 'menu'}
            </span>
          </button>
        )}

        {/* Right side controls: SSE Beacon & Profile */}
        <div className="flex items-center space-x-space-md">
          {/* Live Stream Beacon */}
          <div className="hidden lg:flex items-center space-x-space-xs bg-surface-container-high px-space-sm py-1 rounded-full border border-outline-variant/30">
            <span className={`w-2 h-2 rounded-full ${beacon.color} animate-pulse`}></span>
            <span className={`text-label-sm ${beacon.textCol} font-label-sm tracking-wide`}>
              {beacon.text}
            </span>
          </div>

          {/* User Role Badge */}
          {user && (
            <div className="flex items-center space-x-space-xs bg-surface-container-highest px-3 py-1 rounded-full border border-outline-variant">
              <span
                className={`material-symbols-outlined text-[16px] ${
                  isAdmin ? 'text-secondary' : 'text-primary'
                }`}
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                {isAdmin ? 'shield' : 'person_check'}
              </span>
              <span
                className={`text-label-sm ${
                  isAdmin ? 'text-secondary' : 'text-primary'
                } font-label-sm uppercase`}
              >
                {isAdmin ? 'ADMINISTRADOR' : 'VISUALIZADOR'}
              </span>
            </div>
          )}

          {/* User Avatar Circle */}
          <div
            className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary"
            title={user?.full_name || 'Usuario'}
          >
            <span className="material-symbols-outlined text-on-primary text-[18px]">
              person
            </span>
          </div>

          {/* Logout Button */}
          <button
            onClick={logout}
            className="p-2 text-on-surface-variant hover:text-error transition-colors"
            title="Cerrar sesión"
          >
            <span className="material-symbols-outlined text-[20px]">logout</span>
          </button>
        </div>
      </div>

      {/* Mobile Navigation Dropdown */}
      {mobileMenuOpen && (
        <nav
          className="md:hidden absolute top-16 left-0 w-full bg-surface/95 backdrop-blur-xl border-b border-outline-variant/40 shadow-xl z-40 p-3 space-y-1"
          data-path="menu-mobile-overlay"
        >
          {navItems.map((item) => {
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full text-left px-space-md py-2.5 rounded-lg text-label-md border transition-all ${
                  isActive
                    ? 'bg-primary-container text-on-primary-container font-bold border-primary-fixed-dim'
                    : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high border-transparent'
                }`}
              >
                {item.label}
              </button>
            );
          })}
          <div className="pt-2 border-t border-outline-variant/30 flex items-center justify-between">
            <div className="flex items-center space-x-space-xs px-space-sm">
              <span className={`w-2 h-2 rounded-full ${beacon.color} animate-pulse`}></span>
              <span className={`text-label-sm ${beacon.textCol}`}>{beacon.text}</span>
            </div>
            <button
              onClick={logout}
              className="px-space-md py-2 rounded-lg text-label-md text-on-surface-variant hover:text-error"
            >
              Cerrar sesión
            </button>
          </div>
        </nav>
      )}
    </header>
  );
};
