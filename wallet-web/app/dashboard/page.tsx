"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { walletApiBaseUrl } from "../../lib/api";

const TOKEN_KEY = "pay_wallet_token";

type MeResponse = {
  user: {
    given_name: string;
    family_name: string;
    email: string;
  };
  wallet: {
    wallet_id: string;
    balance_cents: number;
    currency: string;
  };
};

type Tx = {
  id: number;
  transaction_type: string;
  amount_cents: number;
  counterparty_wallet_id: string | null;
  topup_id: string | null;
  created_at: string;
};

export default function DashboardPage() {
  const [token, setToken] = useState<string | null>(null);
  const [me, setMe] = useState<MeResponse | null>(null);
  const [transactions, setTransactions] = useState<Tx[]>([]);
  const [status, setStatus] = useState<string>("");
  const [topupAmountEur, setTopupAmountEur] = useState<string>("20");
  const [recipientWalletId, setRecipientWalletId] = useState<string>("");
  const [transferAmountEur, setTransferAmountEur] = useState<string>("10");

  useEffect(() => {
    const raw = localStorage.getItem(TOKEN_KEY);
    setToken(raw);
  }, []);

  useEffect(() => {
    if (!token) return;
    void refreshData(token);
  }, [token]);

  async function api(path: string, init: RequestInit = {}) {
    if (!token) throw new Error("Missing token");
    const response = await fetch(`${walletApiBaseUrl}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...(init.headers || {})
      }
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error((data as { detail?: string }).detail || "API error");
    }
    return data;
  }

  async function refreshData(currentToken: string) {
    try {
      const [meData, txData] = await Promise.all([
        fetch(`${walletApiBaseUrl}/wallet/me`, {
          headers: { Authorization: `Bearer ${currentToken}` }
        }).then(async (res) => {
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Unable to load profile");
          return data as MeResponse;
        }),
        fetch(`${walletApiBaseUrl}/wallet/transactions?page=1&page_size=20`, {
          headers: { Authorization: `Bearer ${currentToken}` }
        }).then(async (res) => {
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Unable to load transactions");
          return data as { items: Tx[] };
        })
      ]);

      setMe(meData);
      setTransactions(txData.items || []);
      setStatus("");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Erreur de chargement");
    }
  }

  async function submitTopup(event: FormEvent) {
    event.preventDefault();
    const eur = Number(topupAmountEur);
    const amountCents = Math.round(eur * 100);
    if (!Number.isFinite(amountCents) || amountCents <= 0) {
      setStatus("Montant de recharge invalide.");
      return;
    }
    try {
      const data = await api("/wallet/topups", {
        method: "POST",
        body: JSON.stringify({ amount_cents: amountCents })
      });
      const url = (data as { payment_url: string }).payment_url;
      setStatus("Top-up créé. Ouvre le lien Stripe pour payer.");
      window.open(url, "_blank", "noopener,noreferrer");
      await refreshData(token!);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Erreur top-up");
    }
  }

  async function submitTransfer(event: FormEvent) {
    event.preventDefault();
    const eur = Number(transferAmountEur);
    const amountCents = Math.round(eur * 100);
    if (!recipientWalletId.trim()) {
      setStatus("Wallet destinataire requis.");
      return;
    }
    try {
      await api("/wallet/transfers/p2p", {
        method: "POST",
        body: JSON.stringify({
          recipient_wallet_id: recipientWalletId.trim(),
          amount_cents: amountCents
        })
      });
      setStatus("Transfert envoyé.");
      setRecipientWalletId("");
      await refreshData(token!);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Erreur transfert");
    }
  }

  if (!token) {
    return (
      <main className="shell">
        <h1 className="title">Dashboard Wallet</h1>
        <section className="panel stack">
          <p>Token absent. Connecte-toi d&apos;abord.</p>
          <Link className="button" href="/login">
            Aller à la page Login
          </Link>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      <h1 className="title">Dashboard Wallet</h1>
      <p className="subtitle">Top-up Stripe, transferts P2P et historique.</p>

      {me ? (
        <section className="panel">
          <p>
            Utilisateur:{" "}
            <strong>
              {me.user.given_name} {me.user.family_name}
            </strong>{" "}
            ({me.user.email})
          </p>
          <p>
            Wallet: <strong>{me.wallet.wallet_id}</strong>
          </p>
          <p>
            Solde:{" "}
            <strong>
              {(me.wallet.balance_cents / 100).toFixed(2)} {me.wallet.currency}
            </strong>
          </p>
        </section>
      ) : null}

      <section className="panel row">
        <form className="stack" onSubmit={submitTopup}>
          <h2>Recharger le wallet</h2>
          <div>
            <label htmlFor="topupAmountEur">Montant (EUR)</label>
            <input
              id="topupAmountEur"
              type="number"
              min="1"
              step="0.01"
              value={topupAmountEur}
              onChange={(event) => setTopupAmountEur(event.target.value)}
            />
          </div>
          <button type="submit">Créer un top-up Stripe</button>
        </form>

        <form className="stack" onSubmit={submitTransfer}>
          <h2>Transfert P2P</h2>
          <div>
            <label htmlFor="recipientWalletId">Wallet destinataire</label>
            <input
              id="recipientWalletId"
              placeholder="Ex: WAL12AB34CD"
              value={recipientWalletId}
              onChange={(event) => setRecipientWalletId(event.target.value)}
            />
          </div>
          <div>
            <label htmlFor="transferAmountEur">Montant (EUR)</label>
            <input
              id="transferAmountEur"
              type="number"
              min="1"
              step="0.01"
              value={transferAmountEur}
              onChange={(event) => setTransferAmountEur(event.target.value)}
            />
          </div>
          <button className="secondary" type="submit">
            Envoyer le transfert
          </button>
        </form>
      </section>

      <section className="panel stack">
        <h2>Historique</h2>
        <ul className="tx-list">
          {transactions.map((tx) => (
            <li key={tx.id} className="tx-item">
              <strong>{tx.transaction_type}</strong> - {(tx.amount_cents / 100).toFixed(2)} EUR
              {tx.counterparty_wallet_id ? ` - contrepartie: ${tx.counterparty_wallet_id}` : ""}
              {tx.topup_id ? ` - topup: ${tx.topup_id}` : ""}
            </li>
          ))}
        </ul>
      </section>

      <p className="muted">{status}</p>
    </main>
  );
}

