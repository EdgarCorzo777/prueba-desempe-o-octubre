import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  variant?: 'cyan' | 'violet' | 'orange' | 'red' | 'green';
  badge?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = 'cyan',
  badge
}) => {
  const variantStyles = {
    cyan: {
      border: 'border-cyan-500/30 hover:border-cyan-400/60',
      iconBg: 'bg-cyan-500/10 text-cyan-400',
      glow: 'shadow-[0_0_20px_-5px_rgba(6,182,212,0.15)]',
      valColor: 'text-cyan-300'
    },
    violet: {
      border: 'border-violet-500/30 hover:border-violet-400/60',
      iconBg: 'bg-violet-500/10 text-violet-400',
      glow: 'shadow-[0_0_20px_-5px_rgba(139,92,246,0.15)]',
      valColor: 'text-violet-300'
    },
    orange: {
      border: 'border-orange-500/30 hover:border-orange-400/60',
      iconBg: 'bg-orange-500/10 text-orange-400',
      glow: 'shadow-[0_0_20px_-5px_rgba(249,115,22,0.15)]',
      valColor: 'text-orange-400'
    },
    red: {
      border: 'border-red-500/30 hover:border-red-400/60',
      iconBg: 'bg-red-500/10 text-red-400',
      glow: 'shadow-[0_0_20px_-5px_rgba(239,68,68,0.15)]',
      valColor: 'text-red-400'
    },
    green: {
      border: 'border-emerald-500/30 hover:border-emerald-400/60',
      iconBg: 'bg-emerald-500/10 text-emerald-400',
      glow: 'shadow-[0_0_20px_-5px_rgba(16,185,129,0.15)]',
      valColor: 'text-emerald-400'
    }
  };

  const current = variantStyles[variant];

  return (
    <div className={`relative overflow-hidden rounded-xl bg-sismo-surface/80 backdrop-blur-md border ${current.border} p-5 transition-all duration-300 ${current.glow}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold tracking-wider uppercase text-slate-400">{title}</span>
        <div className={`p-2 rounded-lg ${current.iconBg}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className={`text-3xl font-extrabold tracking-tight ${current.valColor}`}>{value}</span>
        {badge && (
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
            {badge}
          </span>
        )}
      </div>
      {subtitle && <p className="mt-1 text-xs text-slate-500 font-medium">{subtitle}</p>}
    </div>
  );
};
