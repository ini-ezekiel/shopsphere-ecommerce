import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ShieldCheck, Truck, Undo2 } from "lucide-react";
import { Link } from "react-router";

import { getCategories, getProducts } from "../../api/catalog";
import ProductCard from "../../components/product/ProductCard";

function HomePage() {
  const { data } = useQuery({
    queryKey: ["products", "home"],
    queryFn: () => getProducts(),
  });
  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: getCategories,
  });
  const products = data?.results ?? [];

  return (
    <>
      <section className="bg-black text-white">
        <div className="page-container grid min-h-[620px] items-center gap-12 py-16 lg:grid-cols-[1.1fr_0.9fr] lg:py-24">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-neutral-400">New season essentials</p>
            <h1 className="mt-5 max-w-3xl text-5xl font-black leading-[0.96] tracking-[-0.045em] sm:text-6xl lg:text-8xl">
              Style that fits your everyday.
            </h1>
            <p className="mt-7 max-w-xl text-lg leading-8 text-neutral-300">
              Shop dependable fashion, footwear, and accessories in one clean, secure experience.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link to="/products" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full bg-white px-7 font-bold text-black hover:bg-neutral-200">
                Shop now <ArrowRight className="size-5" />
              </Link>
              {categories[0] && (
                <Link to={`/products?category=${categories[0].slug}`} className="inline-flex min-h-12 items-center justify-center rounded-full border border-white/30 px-7 font-bold hover:bg-white hover:text-black">
                  Explore {categories[0].name}
                </Link>
              )}
            </div>
          </div>

          <div className="relative hidden min-h-[430px] lg:block" aria-hidden="true">
            <div className="absolute inset-0 rotate-3 rounded-[3rem] bg-white" />
            <div className="absolute inset-8 -rotate-3 rounded-[2.5rem] border border-white/20 bg-neutral-900" />
            <div className="absolute inset-16 flex items-end rounded-[2rem] bg-gradient-to-br from-neutral-700 to-neutral-950 p-9">
              <p className="max-w-xs text-3xl font-black leading-tight">Simple choices. Strong personal style.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="border-b border-neutral-200 bg-white">
        <div className="page-container grid gap-6 py-7 text-sm sm:grid-cols-3">
          <p className="flex items-center gap-3"><Truck className="size-5" /><span><strong>Reliable delivery</strong><br /><span className="text-neutral-500">Clear fees at checkout</span></span></p>
          <p className="flex items-center gap-3"><ShieldCheck className="size-5" /><span><strong>Secure payment</strong><br /><span className="text-neutral-500">Protected Paystack checkout</span></span></p>
          <p className="flex items-center gap-3"><Undo2 className="size-5" /><span><strong>Order visibility</strong><br /><span className="text-neutral-500">Track status from your account</span></span></p>
        </div>
      </section>

      {products.length > 0 && (
        <section className="page-container py-16 lg:py-20">
          <div className="flex items-end justify-between gap-4">
            <div><p className="eyebrow">Fresh arrivals</p><h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Latest products</h2></div>
            <Link to="/products" className="hidden font-bold hover:underline sm:block">View all</Link>
          </div>
          <div className="mt-8 grid grid-cols-2 gap-4 sm:gap-6 md:grid-cols-3 lg:grid-cols-5">
            {products.map((product) => <ProductCard key={product.id} product={product} />)}
          </div>
          <Link to="/products" className="button-secondary mt-8 w-full sm:hidden">View all products</Link>
        </section>
      )}

      {categories.length > 0 && (
        <section className="bg-neutral-100">
          <div className="page-container py-16">
            <p className="eyebrow">Browse by category</p>
            <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {categories.slice(0, 6).map((category) => (
                <Link key={category.id} to={`/products?category=${category.slug}`} className="group flex min-h-36 items-end justify-between rounded-2xl bg-white p-6 transition hover:bg-black hover:text-white">
                  <span><span className="block text-xl font-bold">{category.name}</span><span className="mt-2 block text-sm text-neutral-500 group-hover:text-neutral-300">{category.description || "Browse the collection"}</span></span>
                  <ArrowRight className="size-5" />
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}
    </>
  );
}

export default HomePage;
