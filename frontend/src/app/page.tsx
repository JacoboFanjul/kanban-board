"use client";

import { useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { LoginForm } from "@/components/LoginForm";
import { apiGetMe, apiLogout, getStoredToken, removeToken, storeToken } from "@/lib/api";

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const stored = getStoredToken();
    if (!stored) {
      setReady(true);
      return;
    }
    apiGetMe(stored).then((user) => {
      if (user) setToken(stored);
      else removeToken();
      setReady(true);
    });
  }, []);

  const handleLogin = (newToken: string) => {
    storeToken(newToken);
    setToken(newToken);
  };

  const handleLogout = async () => {
    try {
      if (token) await apiLogout(token);
    } finally {
      removeToken();
      setToken(null);
    }
  };

  if (!ready) return null;
  if (!token) return <LoginForm onLogin={handleLogin} />;
  return <KanbanBoard token={token} onLogout={handleLogout} />;
}
