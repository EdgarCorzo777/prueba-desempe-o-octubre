import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Por favor complete todos los campos.');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.message || 'Error al iniciar sesión.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickFill = (role: 'admin' | 'viewer') => {
    if (role === 'admin') {
      setEmail('admin@sismowatch.internal');
      setPassword('AdminSecure2026!*');
    } else {
      setEmail('viewer@sismowatch.internal');
      setPassword('ViewerSecure2026!*');
    }
    setError(null);
  };

  return (
    <div className="flex flex-col w-full min-h-screen items-center justify-center relative overflow-hidden px-margin py-space-xl bg-surface">
      {/* Diffuse glowing radial blobs */}
      <div className="absolute w-[500px] h-[500px] rounded-full bg-primary-container/10 blur-[120px] -top-24 -left-24 pointer-events-none"></div>
      <div className="absolute w-[500px] h-[500px] rounded-full bg-secondary-container/15 blur-[120px] -bottom-24 -right-24 pointer-events-none"></div>

      {/* Centered Glassmorphic Card */}
      <div className="w-full max-w-[440px] bg-surface-container-low/80 backdrop-blur-2xl rounded-xl p-space-xl shadow-2xl relative z-10 border border-[#1e293b] shadow-[0_0_40px_rgba(0,240,255,0.05)]">
        {/* Header with glowing isotypo */}
        <div className="flex flex-col items-center text-center mb-space-lg">
          <div className="relative flex items-center justify-center w-14 h-14 rounded-xl bg-surface-container-high mb-space-md shadow-[0_0_20px_rgba(0,240,255,0.2)]">
            <span
              className="material-symbols-outlined text-primary text-[32px] animate-pulse"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              pulse_alert
            </span>
            <span className="absolute top-0 right-0 w-3 h-3 bg-primary-container rounded-full animate-ping"></span>
          </div>
          <h1 className="text-headline-lg font-headline-lg text-primary tracking-wider uppercase mb-1">
            SISMoWATCH
          </h1>
          <p className="text-body-sm font-body-sm text-on-surface-variant uppercase tracking-widest">
            Observatorio Geoespacial Sísmico Global
          </p>
        </div>

        {error && (
          <div className="mb-space-md p-3 rounded-lg bg-error-container/80 border border-error text-on-error-container text-body-sm flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">error</span>
            <span>{error}</span>
          </div>
        )}

        {/* Login Form */}
        <form className="space-y-space-md" onSubmit={handleSubmit}>
          <div className="space-y-space-xs">
            <label className="text-label-md font-label-md text-on-surface-variant uppercase">
              Correo Electrónico
            </label>
            <div className="relative flex items-center">
              <span className="material-symbols-outlined absolute left-3 text-on-surface-variant text-[20px]">
                mail
              </span>
              <input
                className="w-full bg-surface-container border border-[#1e293b] rounded-lg pl-11 pr-space-md py-3 text-body-md text-on-surface font-label-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                placeholder="analyst@sismowatch.internal"
                required
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-space-xs">
            <div className="flex items-center justify-between">
              <label className="text-label-md font-label-md text-on-surface-variant uppercase">
                Contraseña
              </label>
              <span className="text-label-sm font-label-sm text-primary hover:underline cursor-pointer">
                ¿Olvidó su clave?
              </span>
            </div>
            <div className="relative flex items-center">
              <span className="material-symbols-outlined absolute left-3 text-on-surface-variant text-[20px]">
                lock
              </span>
              <input
                className="w-full bg-surface-container border border-[#1e293b] rounded-lg pl-11 pr-space-md py-3 text-body-md text-on-surface font-label-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                placeholder="••••••••••••"
                required
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <div className="pt-space-sm">
            <button
              className="w-full h-12 bg-gradient-to-r from-primary-container to-secondary-container text-on-primary-container font-headline-sm rounded-lg flex items-center justify-center space-x-space-sm hover:opacity-95 hover:scale-[1.01] active:scale-[0.99] transition-all shadow-[0_0_20px_rgba(0,240,255,0.2)] disabled:opacity-50"
              type="submit"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="material-symbols-outlined animate-spin text-[20px]">
                    progress_activity
                  </span>
                  <span className="uppercase tracking-wider">Autenticando...</span>
                </>
              ) : (
                <>
                  <span className="uppercase tracking-wider">Iniciar Sesión</span>
                  <span className="material-symbols-outlined text-[20px]">arrow_forward</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Quick Demo Access Panel */}
        <div className="mt-space-xl pt-space-lg border-t border-[#1e293b]">
          <div className="text-label-sm font-label-sm text-on-surface-variant uppercase tracking-widest text-center mb-space-md">
            Acceso Rápido de Demostración
          </div>
          <div className="grid grid-cols-2 gap-space-sm">
            <button
              className="flex items-center justify-center space-x-space-xs bg-surface-container hover:bg-surface-container-high border border-[#1e293b] p-2.5 rounded-lg text-label-md text-primary transition-all"
              type="button"
              onClick={() => handleQuickFill('admin')}
            >
              <span
                className="material-symbols-outlined text-[16px]"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                shield
              </span>
              <span>Administrador</span>
            </button>
            <button
              className="flex items-center justify-center space-x-space-xs bg-surface-container hover:bg-surface-container-high border border-[#1e293b] p-2.5 rounded-lg text-label-md text-secondary transition-all"
              type="button"
              onClick={() => handleQuickFill('viewer')}
            >
              <span
                className="material-symbols-outlined text-[16px]"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                person_check
              </span>
              <span>Visualizador</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
