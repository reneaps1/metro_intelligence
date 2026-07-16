import { useEffect, useRef, useState } from "react";
import { API_BASE_URL, getAccessToken } from "../api";
import type { LiveMonitorEvent, LiveSocketConnectionState } from "./types";

// LM.1 (docs/tasks/LM1-live-monitor-mvp.md): opens the Live Monitor
// WebSocket for a set of characteristics, reconnecting with exponential
// backoff if the connection drops, and exposing the typed event stream.
// Aggregating events per characteristic (for the grid/sparklines) is the
// caller's job -- this hook only owns the socket lifecycle.

const MAX_RETAINED_EVENTS = 1000;
const INITIAL_BACKOFF_MS = 1000;
const MAX_BACKOFF_MS = 10000;

function buildWsUrl(characteristicIds: string[]): string | null {
  const token = getAccessToken();
  if (!token || characteristicIds.length === 0) return null;
  const wsBase = API_BASE_URL.replace(/^http/, "ws");
  const params = new URLSearchParams({ token, characteristic_ids: characteristicIds.join(",") });
  return `${wsBase}/ws/live-monitor?${params.toString()}`;
}

export interface UseLiveSocketResult {
  events: LiveMonitorEvent[];
  connectionState: LiveSocketConnectionState;
}

export function useLiveSocket(characteristicIds: string[]): UseLiveSocketResult {
  const [events, setEvents] = useState<LiveMonitorEvent[]>([]);
  const [connectionState, setConnectionState] = useState<LiveSocketConnectionState>("connecting");
  const key = [...characteristicIds].sort().join(",");

  // Refs (not state) for reconnect bookkeeping: none of this should trigger
  // a re-render, and the cleanup closure needs the *current* socket/timer,
  // not the one captured when the effect first ran.
  const socketRef = useRef<WebSocket | null>(null);
  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const backoffRef = useRef(INITIAL_BACKOFF_MS);
  const unmountedRef = useRef(false);

  useEffect(() => {
    unmountedRef.current = false;
    setEvents([]);

    const ids = key ? key.split(",") : [];

    function connect(): void {
      const url = buildWsUrl(ids);
      if (!url) {
        setConnectionState("closed");
        return;
      }

      setConnectionState((prev) => (prev === "open" ? prev : "connecting"));
      const socket = new WebSocket(url);
      socketRef.current = socket;

      socket.onopen = () => {
        backoffRef.current = INITIAL_BACKOFF_MS;
        setConnectionState("open");
      };

      socket.onmessage = (message: MessageEvent<string>) => {
        try {
          const event = JSON.parse(message.data) as LiveMonitorEvent;
          setEvents((prev) => {
            const next = [...prev, event];
            return next.length > MAX_RETAINED_EVENTS ? next.slice(next.length - MAX_RETAINED_EVENTS) : next;
          });
        } catch {
          // Malformed frame -- ignore rather than crash the whole panel.
        }
      };

      socket.onclose = () => {
        socketRef.current = null;
        if (unmountedRef.current) return;
        setConnectionState("reconnecting");
        const delay = backoffRef.current;
        backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF_MS);
        retryTimeoutRef.current = setTimeout(connect, delay);
      };
    }

    connect();

    return () => {
      unmountedRef.current = true;
      if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
      socketRef.current?.close();
      socketRef.current = null;
    };
    // `key` (the sorted, comma-joined id set) is the only thing that should
    // reopen the socket -- a fresh array reference with the same ids must not.
  }, [key]);

  return { events, connectionState };
}
