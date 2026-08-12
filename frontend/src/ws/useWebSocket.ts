import { useCallback, useEffect, useRef, useState } from "react";

export type WebSocketState = "idle" | "connecting" | "open" | "closed" | "auth-error";

interface UseWebSocketOptions<TMessage> {
  path: string;
  enabled?: boolean;
  connectionKey?: string | number | null;
  maxReconnects?: number;
  onMessage: (message: TMessage) => void;
  onOpen?: () => void;
  onClose?: (event: CloseEvent, reconnectAttempt: number) => void;
}

const loginPath = () => "/login";

/**
 * Shared authenticated WebSocket transport.
 *
 * Close code 1008 is the backend AuthGuard's authentication failure. It is a
 * terminal state: clear pending work, redirect to login, and never reconnect.
 */
export function useWebSocket<TMessage>({
  path,
  enabled = true,
  connectionKey = null,
  maxReconnects = 5,
  onMessage,
  onOpen,
  onClose,
}: UseWebSocketOptions<TMessage>) {
  const socketRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<number | null>(null);
  const queueRef = useRef<string[]>([]);
  const callbacksRef = useRef({ onMessage, onOpen, onClose });
  const [state, setState] = useState<WebSocketState>(enabled ? "connecting" : "idle");
  const [reconnectAttempt, setReconnectAttempt] = useState(0);

  useEffect(() => {
    callbacksRef.current = { onMessage, onOpen, onClose };
  }, [onMessage, onOpen, onClose]);

  useEffect(() => {
    if (!enabled) {
      setState("idle");
      setReconnectAttempt(0);
      queueRef.current = [];
      return;
    }

    let disposed = false;
    let attempts = 0;

    const connect = () => {
      if (disposed) return;
      setState("connecting");
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const socket = new WebSocket(`${protocol}//${window.location.host}${path}`);
      socketRef.current = socket;

      socket.onopen = () => {
        if (disposed) return;
        attempts = 0;
        setReconnectAttempt(0);
        setState("open");
        for (const payload of queueRef.current.splice(0)) socket.send(payload);
        callbacksRef.current.onOpen?.();
      };

      socket.onmessage = (event) => {
        try {
          callbacksRef.current.onMessage(JSON.parse(String(event.data)) as TMessage);
        } catch {
          // Ignore non-JSON frames; every Xanax application message is JSON.
        }
      };

      socket.onerror = () => setState("closed");

      socket.onclose = async (event) => {
        if (socketRef.current === socket) socketRef.current = null;
        if (disposed) return;

        if (event.code === 1008) {
          queueRef.current = [];
          if (timerRef.current !== null) window.clearTimeout(timerRef.current);
          timerRef.current = null;
          setState("auth-error");
          callbacksRef.current.onClose?.(event, attempts);
          window.location.assign(loginPath());
          return;
        }

        setState("closed");
        callbacksRef.current.onClose?.(event, attempts);
        // Current Uvicorn/ASGI turns a close-before-accept from AuthGuard into a
        // rejected handshake (client code 1006). Confirm auth before retrying so
        // both that runtime behavior and the intended 1008 behavior terminate.
        try {
          const response = await fetch("/api/auth/me", { cache: "no-store" });
          if (disposed) return;
          if (response.status === 401) {
            queueRef.current = [];
            setState("auth-error");
            window.location.assign(loginPath());
            return;
          }
        } catch {
          // The server may genuinely be offline; bounded reconnect handles it.
        }
        if (disposed) return;
        if (attempts >= maxReconnects) return;
        attempts += 1;
        setReconnectAttempt(attempts);
        timerRef.current = window.setTimeout(connect, Math.min(attempts * 1000, 5000));
      };
    };

    connect();
    return () => {
      disposed = true;
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
      timerRef.current = null;
      queueRef.current = [];
      const socket = socketRef.current;
      socketRef.current = null;
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    };
  }, [connectionKey, enabled, maxReconnects, path]);

  const send = useCallback((message: unknown): boolean => {
    const payload = typeof message === "string" ? message : JSON.stringify(message);
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(payload);
      return true;
    }
    if (socket?.readyState === WebSocket.CONNECTING) queueRef.current.push(payload);
    return false;
  }, []);

  return { state, reconnectAttempt, send, isOpen: state === "open" };
}
