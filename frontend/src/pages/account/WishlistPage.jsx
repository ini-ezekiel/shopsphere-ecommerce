import { Heart } from "lucide-react";
import { Link } from "react-router";

import ProductCard from "../../components/product/ProductCard";
import { useWishlist } from "../../features/wishlist/WishlistContext";

function WishlistPage() {
  const { items, isWishlistLoading } = useWishlist();

  if (isWishlistLoading) {
    return (
      <div>
        <h2 className="text-2xl font-bold">My wishlist</h2>

        <p className="mt-4 text-neutral-600">Loading your saved products…</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">My wishlist</h2>

          <p className="mt-2 text-sm text-neutral-600">
            {items.length === 1
              ? "1 saved product"
              : `${items.length} saved products`}
          </p>
        </div>
      </div>

      {items.length === 0 ? (
        <section className="mt-6 rounded-2xl border border-dashed border-neutral-300 px-6 py-14 text-center">
          <Heart className="mx-auto size-10 text-neutral-400" />

          <h3 className="mt-4 text-lg font-bold text-neutral-950">
            Your wishlist is empty
          </h3>

          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-neutral-600">
            Save products you like and return to them whenever you are ready to
            shop.
          </p>

          <Link to="/products" className="button-primary mt-6 inline-flex">
            Browse products
          </Link>
        </section>
      ) : (
        <div className="mt-6 grid gap-x-5 gap-y-10 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <ProductCard key={item.id} product={item.product} />
          ))}
        </div>
      )}
    </div>
  );
}

export default WishlistPage;
