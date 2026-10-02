import {
  ArrowRight,
  CheckCircle2,
  PackageCheck,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
} from "lucide-react";
import { Link } from "react-router";

import { useAuth } from "../../features/auth/AuthContext";

const values = [
  {
    title: "Thoughtful selection",
    description:
      "We focus on fashion, footwear, accessories, and everyday products that combine usefulness with personal style.",
    icon: Sparkles,
  },
  {
    title: "Clear product information",
    description:
      "We present useful descriptions, prices, images, options, and availability so you can make informed choices.",
    icon: PackageCheck,
  },
  {
    title: "Secure shopping",
    description:
      "Your account and payment experience are designed with security, privacy, and customer confidence in mind.",
    icon: ShieldCheck,
  },
];

const promises = [
  "Honest and useful product information",
  "Transparent prices and delivery fees",
  "Secure payment through Paystack",
  "Order updates through your ShopSphere account",
  "A shopping experience that continues to improve",
];

function AboutPage() {
  const { isAuthenticated, isAuthLoading } = useAuth();

  return (
    <>
      <section className="bg-black text-white">
        <div className="page-container py-20 sm:py-24 lg:py-32">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-neutral-400">
            About ShopSphere
          </p>

          <h1 className="mt-6 max-w-5xl text-5xl font-black leading-[0.96] tracking-[-0.045em] sm:text-6xl lg:text-8xl">
            Everything you love, all within your sphere.
          </h1>

          <p className="mt-8 max-w-2xl text-lg leading-8 text-neutral-300 sm:text-xl">
            ShopSphere brings dependable fashion, footwear, accessories, and
            everyday essentials into one clean and secure shopping experience.
          </p>

          <Link
            to="/products"
            className="mt-10 inline-flex min-h-12 items-center justify-center gap-2 rounded-full bg-white px-7 font-bold text-black transition hover:bg-neutral-200"
          >
            Explore products
            <ArrowRight aria-hidden="true" className="size-5" />
          </Link>
        </div>
      </section>

      <section className="page-container py-16 sm:py-20 lg:py-28">
        <div className="grid gap-12 lg:grid-cols-[0.8fr_1.2fr] lg:gap-20">
          <div>
            <p className="eyebrow">Our story</p>

            <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
              Shopping should feel simple, clear, and dependable.
            </h2>
          </div>

          <div className="space-y-6 text-base leading-8 text-neutral-600 sm:text-lg">
            <p>
              ShopSphere was created around a straightforward idea: customers
              should be able to discover products they like, understand exactly
              what they are buying, and complete their orders with confidence.
            </p>

            <p>
              Online shopping can become frustrating when product details are
              unclear, prices are difficult to understand, or customers cannot
              follow the progress of an order. We are building ShopSphere to
              offer a more organized and dependable alternative.
            </p>

            <p>
              Our catalogue is designed to grow across fashion, footwear,
              accessories, and lifestyle products without losing the clean and
              focused experience at the centre of the store.
            </p>
          </div>
        </div>
      </section>

      <section className="bg-neutral-100">
        <div className="page-container py-16 sm:py-20 lg:py-24">
          <div className="max-w-2xl">
            <p className="eyebrow">What guides us</p>

            <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
              Built around better everyday shopping.
            </h2>

            <p className="mt-4 leading-7 text-neutral-600">
              Every part of ShopSphere is shaped by three priorities: useful
              choices, clear information, and customer confidence.
            </p>
          </div>

          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {values.map(({ title, description, icon: Icon }) => (
              <article
                key={title}
                className="rounded-2xl border border-neutral-200 bg-white p-6 sm:p-7"
              >
                <div className="flex size-12 items-center justify-center rounded-full bg-black text-white">
                  <Icon aria-hidden="true" className="size-5" />
                </div>

                <h3 className="mt-6 text-xl font-bold">{title}</h3>

                <p className="mt-3 text-sm leading-7 text-neutral-600">
                  {description}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="page-container py-16 sm:py-20 lg:py-28">
        <div className="grid overflow-hidden rounded-4xl bg-black text-white lg:grid-cols-2">
          <div className="p-7 sm:p-10 lg:p-14">
            <p className="text-xs font-bold uppercase tracking-[0.25em] text-neutral-400">
              Our mission
            </p>

            <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
              To make products easier to discover and safer to purchase.
            </h2>

            <p className="mt-5 max-w-xl leading-8 text-neutral-300">
              We aim to build lasting customer trust through straightforward
              information, secure transactions, responsible order handling, and
              an experience that respects your time.
            </p>

            <ShoppingBag
              aria-hidden="true"
              className="mt-10 size-10 text-neutral-400"
            />
          </div>

          <div className="bg-neutral-900 p-7 sm:p-10 lg:p-14">
            <h3 className="text-xl font-bold">Our promise to you</h3>

            <div className="mt-7 space-y-5">
              {promises.map((promise) => (
                <p
                  key={promise}
                  className="flex items-start gap-3 text-sm leading-6 text-neutral-300"
                >
                  <CheckCircle2
                    aria-hidden="true"
                    className="mt-0.5 size-5 shrink-0 text-white"
                  />

                  <span>{promise}</span>
                </p>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="border-t border-neutral-200 bg-white">
        <div className="page-container flex flex-col items-start justify-between gap-8 py-16 sm:py-20 lg:flex-row lg:items-center">
          <div>
            <p className="eyebrow">Explore your sphere</p>

            <h2 className="mt-3 max-w-2xl text-3xl font-bold tracking-tight sm:text-4xl">
              Find something that fits your everyday.
            </h2>
          </div>

          <div className="flex min-h-12 flex-wrap gap-3">
            <Link
              to="/products"
              className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full bg-black px-7 font-bold text-white transition hover:bg-neutral-800"
            >
              Shop products
              <ArrowRight aria-hidden="true" className="size-5" />
            </Link>

            {!isAuthLoading &&
              (isAuthenticated ? (
                <Link
                  to="/account"
                  className="inline-flex min-h-12 items-center justify-center rounded-full border border-neutral-300 px-7 font-bold text-neutral-900 transition hover:bg-neutral-100"
                >
                  My account
                </Link>
              ) : (
                <Link
                  to="/register"
                  className="inline-flex min-h-12 items-center justify-center rounded-full border border-neutral-300 px-7 font-bold text-neutral-900 transition hover:bg-neutral-100"
                >
                  Create an account
                </Link>
              ))}
          </div>
        </div>
      </section>
    </>
  );
}

export default AboutPage;
