import { Heart } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router";
import { toast } from "sonner";

import { useAuth } from "../../features/auth/AuthContext";
import { useWishlist } from "../../features/wishlist/WishlistContext";
import { getApiError } from "../../lib/errors";

function formatNaira(value) {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    maximumFractionDigits: 0,
  }).format(Number(value));
}

function ProductCard({ product }) {
  const navigate = useNavigate();
  const location = useLocation();

  const { isAuthenticated } = useAuth();

  const { isWishlisted, isUpdating, toggleWishlist } = useWishlist();

  const productIsWishlisted = isWishlisted(product.id);
  const wishlistIsUpdating = isUpdating(product.id);

  async function handleWishlistClick(event) {
    event.preventDefault();
    event.stopPropagation();

    if (!isAuthenticated) {
      toast.info("Sign in to save products.");

      navigate("/login", {
        state: {
          from: location,
        },
      });

      return;
    }

    try {
      const result = await toggleWishlist(product);

      toast.success(
        result.added
          ? "Added to your wishlist."
          : "Removed from your wishlist.",
      );
    } catch (error) {
      toast.error(getApiError(error, "Unable to update your wishlist."));
    }
  }

  return (
    <article className="group relative rounded-2xl">
      <Link
        to={`/products/${product.slug}`}
        className="block rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-4"
      >
        <div className="aspect-4/5 overflow-hidden rounded-2xl bg-neutral-100 p-4">
          {product.primary_image?.image ? (
            <img
              src={product.primary_image.image}
              alt={product.primary_image.alt_text || product.name}
              loading="lazy"
              className="h-full w-full object-contain transition duration-300 group-hover:scale-105"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-neutral-500">
              No image available
            </div>
          )}
        </div>

        <div className="pt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
            {product.brand?.name || product.category?.name}
          </p>

          <h2 className="mt-1 line-clamp-2 font-semibold text-neutral-950">
            {product.name}
          </h2>

          <p className="mt-2 font-bold text-neutral-950">
            {formatNaira(product.starting_price)}
          </p>

          <p
            className={`mt-2 text-sm font-medium ${
              product.is_in_stock ? "text-green-700" : "text-red-700"
            }`}
          >
            {product.is_in_stock ? "In stock" : "Out of stock"}
          </p>
        </div>
      </Link>

      <button
        type="button"
        onClick={handleWishlistClick}
        disabled={wishlistIsUpdating}
        aria-label={
          productIsWishlisted
            ? `Remove ${product.name} from wishlist`
            : `Add ${product.name} to wishlist`
        }
        aria-pressed={productIsWishlisted}
        className="absolute right-3 top-3 flex size-11 items-center justify-center rounded-full border border-neutral-200 bg-white text-neutral-900 shadow-sm transition hover:scale-105 hover:border-black disabled:cursor-wait disabled:opacity-60"
      >
        <Heart
          className={`size-5 ${
            productIsWishlisted ? "fill-red-500 text-red-500" : ""
          }`}
        />
      </button>
    </article>
  );
}

export default ProductCard;
