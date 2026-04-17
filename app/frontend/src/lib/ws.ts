type EventHandler = (data: Record<string, unknown>) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: Map<string, Set<EventHandler>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private _isConnected = false;

  constructor(url: string) {
    this.url = url;
  }

  get isConnected(): boolean {
    return this._isConnected;
  }

  connect(tenantId: string, userId: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    const wsUrl = `${this.url}?tenant_id=${tenantId}&user_id=${userId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this._isConnected = true;
      this.reconnectAttempts = 0;
      this.emit("connection:open", {});
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as { type: string; data: Record<string, unknown> };
        this.emit(message.type, message.data);
      } catch {
        // ignore malformed messages
      }
    };

    this.ws.onclose = () => {
      this._isConnected = false;
      this.emit("connection:close", {});
      this.attemptReconnect(tenantId, userId);
    };

    this.ws.onerror = () => {
      this._isConnected = false;
    };
  }

  private attemptReconnect(tenantId: string, userId: string): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;

    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    this.reconnectAttempts++;

    this.reconnectTimeout = setTimeout(() => {
      this.connect(tenantId, userId);
    }, delay);
  }

  on(event: string, handler: EventHandler): () => void {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);

    return () => {
      this.handlers.get(event)?.delete(handler);
    };
  }

  private emit(event: string, data: Record<string, unknown>): void {
    this.handlers.get(event)?.forEach((handler) => handler(data));
  }

  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    this.ws?.close();
    this.ws = null;
    this._isConnected = false;
  }
}

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";
export const wsClient = new WebSocketClient(WS_BASE_URL);
