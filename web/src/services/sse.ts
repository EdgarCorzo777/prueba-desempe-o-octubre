import { SeismicEvent } from '../types';

export type SSEStatus = 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING';

export class SSEService {
  private eventSource: EventSource | null = null;
  private statusListeners: Set<(status: SSEStatus) => void> = new Set();
  private eventListeners: Set<(event: SeismicEvent) => void> = new Set();
  private retryTimeout: any = null;
  private retryDelay = 2000;
  private currentStatus: SSEStatus = 'DISCONNECTED';

  subscribe(
    onEvent: (event: SeismicEvent) => void,
    onStatusChange?: (status: SSEStatus) => void
  ): () => void {
    this.eventListeners.add(onEvent);
    if (onStatusChange) {
      this.statusListeners.add(onStatusChange);
      onStatusChange(this.currentStatus);
    }

    if (!this.eventSource) {
      this.initSource();
    }

    return () => {
      this.eventListeners.delete(onEvent);
      if (onStatusChange) {
        this.statusListeners.delete(onStatusChange);
      }
      if (this.eventListeners.size === 0 && this.statusListeners.size === 0) {
        this.disconnect();
      }
    };
  }

  // Backward compatibility wrapper
  connect(
    onEvent: (event: SeismicEvent) => void,
    onStatusChange: (status: SSEStatus) => void
  ) {
    this.subscribe(onEvent, onStatusChange);
  }

  private notifyStatus(status: SSEStatus) {
    this.currentStatus = status;
    this.statusListeners.forEach((listener) => {
      try {
        listener(status);
      } catch (err) {
        console.error('Error in SSE status listener:', err);
      }
    });
  }

  private notifyEvent(event: SeismicEvent) {
    this.eventListeners.forEach((listener) => {
      try {
        listener(event);
      } catch (err) {
        console.error('Error in SSE event listener:', err);
      }
    });
  }

  private initSource() {
    const token = localStorage.getItem('sismowatch_token');
    if (!token) {
      this.notifyStatus('DISCONNECTED');
      return;
    }

    const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const sseUrl = `${API_BASE}/api/stream?token=${encodeURIComponent(token)}`;

    this.notifyStatus('CONNECTING');

    try {
      this.eventSource = new EventSource(sseUrl);

      this.eventSource.addEventListener('connect', () => {
        this.notifyStatus('CONNECTED');
        this.retryDelay = 2000;
      });

      this.eventSource.addEventListener('earthquake', (e: MessageEvent) => {
        try {
          const eventData: SeismicEvent = JSON.parse(e.data);
          this.notifyEvent(eventData);
        } catch (err) {
          console.error('Failed to parse SSE earthquake event:', err);
        }
      });

      this.eventSource.addEventListener('heartbeat', () => {
        this.notifyStatus('CONNECTED');
      });

      this.eventSource.onerror = (err) => {
        console.warn('SSE stream connection error. Retrying...', err);
        this.cleanup();
        this.notifyStatus('RECONNECTING');
        this.retryTimeout = setTimeout(() => {
          this.retryDelay = Math.min(this.retryDelay * 1.5, 30000);
          this.initSource();
        }, this.retryDelay);
      };
    } catch (err) {
      this.notifyStatus('DISCONNECTED');
    }
  }

  disconnect() {
    this.cleanup();
    this.notifyStatus('DISCONNECTED');
  }

  private cleanup() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    if (this.retryTimeout) {
      clearTimeout(this.retryTimeout);
      this.retryTimeout = null;
    }
  }
}

export const sseService = new SSEService();
