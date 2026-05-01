import Link from "next/link";

export default function HomePage() {
  return (
    <main className="shell">
      <h1 className="title">Pay Wallet Monopoly</h1>
      <p className="subtitle">Prototype wallet: FranceConnect, top-up Stripe, transfert P2P.</p>

      <section className="panel stack">
        <p>
          Démarre par FranceConnect mock, puis synchronise ta session dans le wallet.
        </p>
        <div>
          <Link href="/login" className="button">
            Ouvrir l&apos;espace Wallet
          </Link>
        </div>
      </section>
    </main>
  );
}

