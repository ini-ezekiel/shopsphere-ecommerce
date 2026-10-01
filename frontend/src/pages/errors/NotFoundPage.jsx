import { ArrowLeft, Home, SearchX } from "lucide-react";
import { Link } from "react-router";

function NotFoundPage() {
  return (
    <section className="flex min-h-screen items-center justify-center bg-surface-muted px-6 py-16">
      <div className="w-full max-w-xl text-center">
        <div className="mx-auto flex size-16 items-center justify-center rounded-full bg-brand-100 text-brand-600">
          <SearchX aria-hidden="true" className="size-8" />
        </div>

        <p className="mt-6 text-sm font-bold uppercase tracking-[0.2em] text-brand-600">
          Error 404
        </p>

        <h1 className="mt-3 font-display text-4xl font-bold tracking-tight text-neutral-950 sm:text-5xl">
          We couldn’t find that page.
        </h1>

        <p className="mx-auto mt-4 max-w-md leading-7 text-neutral-600">
          The address may be incorrect, or the page may have been moved.
        </p>

        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Link
            to="/"
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full bg-brand-500 px-6 py-3 font-semibold text-white transition hover:bg-brand-600"
          >
            <Home aria-hidden="true" className="size-5" />
            Return home
          </Link>

          <button
            type="button"
            onClick={() => window.history.back()}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-neutral-300 bg-white px-6 py-3 font-semibold text-neutral-900 transition hover:bg-neutral-100"
          >
            <ArrowLeft aria-hidden="true" className="size-5" />
            Go back
          </button>
        </div>
      </div>
    </section>
  );
}

export default NotFoundPage;
