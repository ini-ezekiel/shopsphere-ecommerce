import { ChevronLeft, ChevronRight, ShieldCheck, ShoppingBag, Star, Truck } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { toast } from "sonner";
import { addCartItem } from "../../api/cart";
import { getProduct } from "../../api/catalog";
import ProductReviews from "../../components/product/ProductReviews";
import { useAuth } from "../../features/auth/AuthContext";
import { getApiError } from "../../lib/errors";
import { formatNaira } from "../../lib/format";

function ProductImageGallery({ images, name }) {
  const [selectedImageId, setSelectedImageId] = useState(null);
  const gesture = useRef(null);
  const selectedIndex = Math.max(0, images.findIndex((image) =>
    image.id === (selectedImageId ?? images.find((item) => item.is_primary)?.id ?? images[0]?.id)
  ));
  const selectedImage = images[selectedIndex];
  const hasMultipleImages = images.length > 1;

  function changeImage(direction) {
    if (!hasMultipleImages) return;
    const nextIndex = (selectedIndex + direction + images.length) % images.length;
    setSelectedImageId(images[nextIndex].id);
  }

  function handlePointerDown(event) {
    if (!hasMultipleImages || !event.isPrimary || event.button !== 0 ||
        event.target.closest("button")) return;
    gesture.current = { id: event.pointerId, x: event.clientX, y: event.clientY };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerUp(event) {
    const start = gesture.current;
    gesture.current = null;
    if (!start || start.id !== event.pointerId) return;
    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    if (Math.abs(dx) >= 50 && Math.abs(dx) > Math.abs(dy) * 1.2) {
      changeImage(dx < 0 ? 1 : -1);
    }
  }

  return (
    <div>
      <div
        role="region"
        aria-label={`${name} image gallery`}
        aria-roledescription="carousel"
        tabIndex={hasMultipleImages ? 0 : undefined}
        style={{ touchAction: "pan-y pinch-zoom" }}
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
        onPointerCancel={() => { gesture.current = null; }}
        onLostPointerCapture={() => { gesture.current = null; }}
        onKeyDown={(event) => {
          if (event.target !== event.currentTarget || !hasMultipleImages) return;
          if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
            event.preventDefault();
            changeImage(event.key === "ArrowLeft" ? -1 : 1);
          }
        }}
        className="relative aspect-square select-none overflow-hidden rounded-3xl bg-neutral-100 p-6 outline-none focus-visible:ring-2 focus-visible:ring-brand-500 sm:p-10"
      >
        {selectedImage ? (
          <img
            src={selectedImage.image}
            alt={selectedImage.alt_text || name}
            draggable={false}
            className={`h-full w-full object-contain ${hasMultipleImages ? "cursor-grab active:cursor-grabbing" : ""}`}
          />
        ) : (
          <div className="flex h-full items-center justify-center text-neutral-500">
            No image available
          </div>
        )}
        {hasMultipleImages && (
          <>
            <button type="button" aria-label="Previous product image"
              onClick={() => changeImage(-1)}
              className="absolute left-3 top-1/2 flex size-11 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-neutral-950 shadow-sm hover:bg-white focus-visible:outline-2 focus-visible:outline-brand-500">
              <ChevronLeft className="size-6" aria-hidden="true" />
            </button>
            <button type="button" aria-label="Next product image"
              onClick={() => changeImage(1)}
              className="absolute right-3 top-1/2 flex size-11 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-neutral-950 shadow-sm hover:bg-white focus-visible:outline-2 focus-visible:outline-brand-500">
              <ChevronRight className="size-6" aria-hidden="true" />
            </button>
            <span aria-live="polite" aria-atomic="true"
              className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-white/90 px-3 py-1 text-xs font-semibold text-neutral-700">
              {selectedIndex + 1} / {images.length}
            </span>
          </>
        )}
      </div>
      {hasMultipleImages && (
        <div className="mt-4 flex gap-3 overflow-x-auto pb-2" aria-label="Choose product image">
          {images.map((image, index) => (
            <button key={image.id} type="button"
              onClick={() => setSelectedImageId(image.id)}
              aria-label={`View image ${index + 1}: ${image.alt_text || name}`}
              aria-pressed={selectedImage?.id === image.id}
              className={`size-20 shrink-0 overflow-hidden rounded-xl border bg-neutral-100 p-2 focus-visible:outline-2 focus-visible:outline-brand-500 ${selectedImage?.id === image.id ? "border-brand-500" : "border-neutral-200"}`}>
              <img src={image.image} alt="" draggable={false} className="h-full w-full object-contain" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ProductDetailPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuth();
  const [selectedVariantId, setSelectedVariantId] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const {
    data: product,
    isPending,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["product", slug],
    queryFn: () => getProduct(slug),
    enabled: Boolean(slug),
  });
  const selectedVariant = product
    ? (product.variants.find((variant) => variant.id === selectedVariantId) ??
      product.variants[0])
    : null;
  const cartMutation = useMutation({
    mutationFn: () => addCartItem({ variant_id: selectedVariant.id, quantity }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cart"] });
      toast.success("Added to your cart.");
    },
    onError: (error) => toast.error(getApiError(error, "Unable to add this item.")),
  });
  if (isPending) {
    return (
      <section className="mx-auto max-w-360 animate-pulse px-6 py-10 sm:px-8 lg:px-10">
        <div className="grid gap-10 lg:grid-cols-2">
          <div className="aspect-square rounded-3xl bg-neutral-200" />
          <div>
            <div className="h-4 w-24 rounded bg-neutral-200" />
            <div className="mt-5 h-10 w-3/4 rounded bg-neutral-200" />
            <div className="mt-5 h-6 w-36 rounded bg-neutral-200" />
            <div className="mt-8 h-24 rounded bg-neutral-200" />
          </div>
        </div>
      </section>
    );
  }
  if (isError) {
    const isNotFound = error?.response?.status === 404;
    return (
      <section className="mx-auto flex min-h-[60vh] max-w-xl flex-col items-center justify-center px-4 text-center">
        <h1 className="font-display text-3xl font-bold text-neutral-950">
          {isNotFound ? "Product not found" : "We couldn’t load this product"}
        </h1>
        <p className="mt-3 text-neutral-600">
          {isNotFound
            ? "This product may have been removed or is no longer available."
            : "Check your connection and try again."}
        </p>
        <div className="mt-7 flex flex-wrap justify-center gap-3">
          {!isNotFound && (
            <button
              type="button"
              onClick={() => refetch()}
              className="min-h-11 rounded-full bg-brand-500 px-6 py-3 font-semibold text-white hover:bg-brand-600"
            >
              Retry
            </button>
          )}
          <Link
            to="/products"
            className="inline-flex min-h-11 items-center justify-center rounded-full border border-neutral-300 px-6 py-3 font-semibold hover:bg-neutral-100"
          >
            Browse products
          </Link>
        </div>
      </section>
    );
  }
  function handleAddToCart() {
    if (!isAuthenticated) {
      navigate("/login", { state: { from: { pathname: `/products/${slug}` } } });
      return;
    }
    if (selectedVariant?.is_in_stock) {
      cartMutation.mutate();
    }
  }
  return (
    <section className="mx-auto max-w-360 px-6 py-8 sm:px-8 lg:px-10 lg:py-12">
      <nav
        aria-label="Breadcrumb"
        className="mb-8 flex flex-wrap items-center gap-2 text-sm text-neutral-600"
      >
        <Link to="/" className="hover:text-brand-600">
          Home
        </Link>
        <ChevronRight aria-hidden="true" className="size-4" />
        <Link to="/products" className="hover:text-brand-600">
          Products
        </Link>
        <ChevronRight aria-hidden="true" className="size-4" />
        <span className="text-neutral-950">{product.name}</span>
      </nav>
      <div className="grid gap-10 lg:grid-cols-2 lg:gap-16">
        <ProductImageGallery key={slug} images={product.images ?? []} name={product.name} />
        <div className="lg:py-4">
          <p className="text-sm font-bold uppercase tracking-[0.18em] text-brand-600">
            {product.brand?.name || product.category?.name}
          </p>
          <h1 className="mt-3 font-display text-4xl font-bold tracking-tight text-neutral-950 sm:text-5xl">
            {product.name}
          </h1>
          <div className="mt-4 flex items-center gap-2 text-sm">
            <Star
              aria-hidden="true"
              className="size-5 fill-amber-400 text-amber-400"
            />
            <span className="font-semibold text-neutral-950">
              {product.average_rating}
            </span>
            <span className="text-neutral-500">
              ({product.review_count}{" "}
              {product.review_count === 1 ? "review" : "reviews"})
            </span>
          </div>
          {selectedVariant && (
            <div className="mt-7">
              <p className="text-3xl font-bold text-neutral-950">
                {formatNaira(selectedVariant.current_price)}
              </p>
              {selectedVariant.discount_price && (
                <p className="mt-1 text-sm text-neutral-500 line-through">
                  {formatNaira(selectedVariant.price)}
                </p>
              )}
            </div>
          )}
          <p className="mt-7 leading-7 text-neutral-600">
            {product.description}
          </p>
          {selectedVariant?.attributes?.color && (
            <p className="mt-6 text-sm text-neutral-700">
              Colour:{" "}
              <span className="font-semibold text-neutral-950">
                {selectedVariant.attributes.color}
              </span>
            </p>
          )}
          {product.variants.length > 0 && (
            <fieldset className="mt-8">
              <legend className="font-semibold text-neutral-950">
                Select size
              </legend>
              <div className="mt-3 flex flex-wrap gap-3">
                {product.variants.map((variant) => {
                  const isSelected = selectedVariant?.id === variant.id;
                  return (
                    <button
                      key={variant.id}
                      type="button"
                      disabled={!variant.is_in_stock}
                      onClick={() => setSelectedVariantId(variant.id)}
                      className={`min-h-11 rounded-xl border px-4 py-2 text-sm font-semibold transition ${
                        isSelected
                          ? "border-brand-500 bg-brand-50 text-brand-700"
                          : "border-neutral-300 bg-white text-neutral-800 hover:border-neutral-500"
                      } disabled:cursor-not-allowed disabled:opacity-40`}
                    >
                      {variant.attributes?.size || variant.name}
                    </button>
                  );
                })}
              </div>
            </fieldset>
          )}
          {selectedVariant && (
            <div className="mt-6 rounded-2xl border border-border bg-neutral-50 p-4">
              <p
                className={`font-semibold ${
                  selectedVariant.is_in_stock
                    ? "text-green-700"
                    : "text-red-700"
                }`}
              >
                {selectedVariant.is_in_stock
                  ? "Available in stock"
                  : "Currently out of stock"}
              </p>
            </div>
          )}
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <label className="sr-only" htmlFor="product-quantity">Quantity</label>
            <select
              id="product-quantity"
              value={quantity}
              onChange={(event) => setQuantity(Number(event.target.value))}
              className="min-h-12 rounded-full border border-neutral-300 bg-white px-5 font-semibold"
            >
              {[1, 2, 3, 4, 5].map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
            <button
              type="button"
              onClick={handleAddToCart}
              disabled={!selectedVariant?.is_in_stock || cartMutation.isPending}
              className="button-primary flex-1 gap-2"
            >
              <ShoppingBag className="size-5" aria-hidden="true" />
              {cartMutation.isPending ? "Adding…" : "Add to cart"}
            </button>
          </div>
          <div className="mt-8 grid gap-3 border-t border-neutral-200 pt-6 text-sm text-neutral-600 sm:grid-cols-2">
            <p className="flex items-center gap-2"><Truck className="size-5 text-black" /> Delivery calculated at checkout</p>
            <p className="flex items-center gap-2"><ShieldCheck className="size-5 text-black" /> Secure payment with Paystack</p>
          </div>
        </div>
      </div>
      <ProductReviews productSlug={product.slug} reviewCount={product.review_count} />
    </section>
  );
}
export default ProductDetailPage;
