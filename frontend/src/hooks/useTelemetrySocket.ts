import { useEffect, useRef, useState } from "react";

import type { TickEvent } from "../types/api";

export type ConnectionStatus = "connecting" | "open" | "closed";

interface TelemetryState {
  latestEvent: TickEvent | null;
  status: ConnectionStatus;
}

const RECONNECT_DELAY_MS = 2000;

/**
 * Se conecta al WebSocket de telemetría del backend y reconecta automáticamente
 * si la conexión se cae (el tick engine sigue corriendo aunque el frontend
 * pierda la conexión momentáneamente).
 */
export function useTelemetrySocket(url: string): TelemetryState {
  const [latestEvent, setLatestEvent] = useState<TickEvent | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const reconnectTimer = useRef<number | undefined>(undefined);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let cancelled = false;

    const connect = (): void => {
      setStatus("connecting");
      socket = new WebSocket(url);

      socket.onopen = () => setStatus("open");

      socket.onmessage = (event: MessageEvent<string>) => {
        try {
          const parsed = JSON.parse(event.data) as TickEvent;
          setLatestEvent(parsed);
        } catch {
          console.error("telemetry payload was not valid JSON", event.data);
        }
      };

      socket.onclose = () => {
        setStatus("closed");
        if (!cancelled) {
          reconnectTimer.current = window.setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };

      socket.onerror = () => socket?.close();
    };

    connect();

    return () => {
      cancelled = true;
      window.clearTimeout(reconnectTimer.current);
      socket?.close();
    };
  }, [url]);

  return { latestEvent, status };
}
