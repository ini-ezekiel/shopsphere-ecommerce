import { Link } from "react-router";

import BrandLogo from "./BrandLogo";

function AuthShell({ eyebrow, title, description, children, footer }) {
  return (
    <section className="bg-neutral-50 px-4 py-12 sm:px-6 sm:py-16">
      <div className="mx-auto w-full max-w-md">
        <div className="mb-8 text-center">
          <BrandLogo />
          <p className="mt-8 text-xs font-bold uppercase tracking-[0.24em] text-neutral-500">
            {eyebrow}
          </p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-neutral-950">
            {title}
          </h1>
          {description && (
            <p className="mt-3 leading-6 text-neutral-600">{description}</p>
          )}
        </div>

        <div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm sm:p-8">
          {children}
        </div>

        {footer && <p className="mt-6 text-center text-sm text-neutral-600">{footer}</p>}

        <p className="mt-4 text-center text-sm">
          <Link to="/products" className="font-semibold text-neutral-950 hover:underline">
            Continue shopping
          </Link>
        </p>
      </div>
    </section>
  );
}

export default AuthShell;
