"use client";

import Link from "next/link";
import { useState } from "react";

import { franceConnectLoginUrl, walletApiBaseUrl } from "../../lib/api";

type SyncResponse = {
  access_token: string;
  wallet: {
    wallet_id: string;
    balance_cents: number;
    currency: string;
  };
  user: {
    email: string;
    given_name: string;
    family_name: string;
  };
};

const TOKEN_KEY = "pay_wallet_token";

export default function LoginPage() {
  const [status, setStatus] = useState<string>("");
  const [session, setSession] = useState<SyncResponse | null>(null);

  async function syncSession() {
    setStatus("Synchronisation en cours...");
    try {
      const response = await fetch(`${walletApiBaseUrl}/auth/session/sync`, {
        method: "POST",
        credentials: "include"
      });
      const data = (await response.json()) as SyncResponse | { detail?: string };
      if (!response.ok) {
        const detail = "detail" in data ? data.detail || "Erreur de synchronisation." : "Erreur de synchronisation.";
        setStatus(detail);
        return;
      }
      const typed = data as SyncResponse;
      localStorage.setItem(TOKEN_KEY, typed.access_token);
      setSession(typed);
      setStatus("Session wallet synchronisée.");
    } catch (_error) {
      setStatus("Wallet API indisponible.");
    }
  }

  return (
    <main className="shell">
      <h1 className="title">Connexion Wallet</h1>
      <p className="subtitle">Connecte-toi d&apos;abord sur FranceConnect mock, puis sync wallet.</p>

      <section className="panel stack">
        <a className="button" href={franceConnectLoginUrl} target="_blank" rel="noreferrer">
          Ouvrir FranceConnect login
        </a>
        <button className="secondary" type="button" onClick={syncSession}>
          Synchroniser la session wallet
        </button>
        <p className="muted">{status}</p>

        {session ? (
          <div className="panel">
            <p>
              Connecté: <strong>{session.user.given_name} {session.user.family_name}</strong> ({session.user.email})
            </p>
            <p>
              Wallet: <strong>{session.wallet.wallet_id}</strong> - Solde: {session.wallet.balance_cents / 100}{" "}
              {session.wallet.currency}
            </p>
            <Link className="button" href="/dashboard">
              Aller au dashboard
            </Link>
          </div>
        ) : null}
      </section>
    </main>
  );
}

