import React from 'react';
import { LayoutDashboard, Radio, FileText, CheckCircle2, MessageSquareCode, ShieldAlert } from 'lucide-react';

export type TabType = 'dashboard' | 'live' | 'reports' | 'pipeline' | 'chat';

interface SidebarProps {
  currentTab: TabType;
  onSelectTab: (tab: TabType) => void;
  isAdmin: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab, isAdmin }) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'live', label: 'Monitor en Vivo', icon: Radio },
    { id: 'reports', label: 'Reportes e IA', icon: FileText },
    { id: 'pipeline', label: 'Pipeline y Calidad', icon: CheckCircle2 },
    { id: 'chat', label: 'Asistente IA', icon: MessageSquareCode },
  ];

  return (
    <aside className="w-64 border-r border-slate-800 bg-sismo-darker/60 flex flex-col justify-between py-6 px-3 shrink-0">
      <nav className="space-y-1.5">
        <div className="px-3 pb-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">
          Operaciones Sísmicas
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id as TabType)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all duration-200 ${
                isActive
                  ? 'bg-gradient-to-r from-cyan-500/20 to-sky-500/10 text-cyan-300 border border-cyan-500/40 shadow-glow-cyan'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 border border-transparent'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Security Status Box */}
      <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-[11px]">
        <div className="flex items-center gap-2 font-bold text-slate-300 mb-1">
          <ShieldAlert className="w-3.5 h-3.5 text-cyan-400" />
          Seguridad Medallion
        </div>
        <p className="text-slate-400 text-[10px] leading-relaxed">
          Acceso de lectura restringido a la capa <strong className="text-cyan-300">Curated</strong>. Aislamiento de capas Bronze y Silver verificado.
        </p>
      </div>
    </aside>
  );
};
