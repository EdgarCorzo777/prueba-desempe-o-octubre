import React from 'react';

export const LoadingView: React.FC<{ message?: string }> = ({
  message = 'Cargando datos certificados del Observatorio...'
}) => (
  <div className="flex flex-col items-center justify-center p-12 text-center text-on-surface-variant font-label-md">
    <span className="material-symbols-outlined animate-spin text-primary text-[36px] mb-3">
      progress_activity
    </span>
    <p className="text-body-md tracking-wide text-on-surface">{message}</p>
  </div>
);

export const EmptyView: React.FC<{ title?: string; message?: string }> = ({
  title = 'No hay registros disponibles',
  message = 'No se encontraron eventos sísmicos para los filtros seleccionados.'
}) => (
  <div className="flex flex-col items-center justify-center p-12 text-center text-on-surface-variant border border-dashed border-outline-variant rounded-xl bg-surface-container-low/50">
    <span className="material-symbols-outlined text-[42px] text-outline mb-2">
      inbox
    </span>
    <h4 className="text-headline-sm font-headline-sm text-on-surface">{title}</h4>
    <p className="text-body-sm text-on-surface-variant max-w-sm mt-1">{message}</p>
  </div>
);

export const ErrorView: React.FC<{ error?: string; message?: string; onRetry?: () => void }> = ({
  error,
  message,
  onRetry
}) => {
  const displayMsg = message || error || 'Ocurrió un error inesperado al consultar el servicio.';
  return (
    <div className="p-6 bg-error-container/40 border border-error text-on-error-container rounded-xl flex flex-col items-center justify-center text-center my-4 shadow-lg">
      <span className="material-symbols-outlined text-error text-[36px] mb-2">
        warning
      </span>
      <h4 className="font-headline-sm font-semibold text-error">
        Fallo de Comunicación o Consulta
      </h4>
      <p className="text-body-sm text-on-error-container/90 mt-1 max-w-md">{displayMsg}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 px-4 py-1.5 bg-error text-on-error rounded-lg text-label-md font-bold flex items-center space-x-1 hover:opacity-90 transition-opacity"
        >
          <span className="material-symbols-outlined text-[16px]">refresh</span>
          <span>Reintentar</span>
        </button>
      )}
    </div>
  );
};
