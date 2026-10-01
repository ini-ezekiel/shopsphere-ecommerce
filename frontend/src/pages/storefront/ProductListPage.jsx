import { useQuery } from "@tanstack/react-query";
import { ChevronDown, SearchX } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router";

import { getBrands, getCategories, getProducts } from "../../api/catalog";
import ProductCard from "../../components/product/ProductCard";

function ProductListPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const searchTerm = searchParams.get("search")?.trim() || "";
  const category = searchParams.get("category")?.trim() || "";
  const brand = searchParams.get("brand")?.trim() || "";
  const ordering = searchParams.get("ordering") || "";
  const inStock = searchParams.get("in_stock") === "true";
  const minPrice = searchParams.get("min_price") || "";
  const maxPrice = searchParams.get("max_price") || "";
  const page = Math.max(1, Number(searchParams.get("page") || 1));
  const hasActiveFilters = Boolean(
    category || brand || ordering || inStock || minPrice || maxPrice,
  );

  const [isPriceOpen, setIsPriceOpen] = useState(Boolean(minPrice || maxPrice));

  const filters = {};

  if (searchTerm) {
    filters.search = searchTerm;
  }

  if (category) {
    filters.category = category;
  }

  if (brand) {
    filters.brand = brand;
  }

  if (ordering) {
    filters.ordering = ordering;
  }

  if (inStock) {
    filters.in_stock = true;
  }

  if (minPrice) {
    filters.min_price = minPrice;
  }

  if (maxPrice) {
    filters.max_price = maxPrice;
  }

  if (page > 1) {
    filters.page = page;
  }

  const { data: categories = [], isPending: categoriesPending } = useQuery({
    queryKey: ["categories"],
    queryFn: getCategories,
  });

  const { data: brands = [], isPending: brandsPending } = useQuery({
    queryKey: ["brands"],
    queryFn: getBrands,
  });

  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ["products", filters],
    queryFn: () => getProducts(filters),
  });

  const products = data?.results ?? [];

  const heading = searchTerm
    ? `Results for “${searchTerm}”`
    : category
      ? category.replaceAll("-", " ")
      : "Shop all products";

  function handleFilterChange(event) {
    const updatedParams = new URLSearchParams(searchParams);
    const { name, value } = event.target;

    if (value) {
      updatedParams.set(name, value);
    } else {
      updatedParams.delete(name);
    }

    updatedParams.delete("page");
    setSearchParams(updatedParams);
  }

  function handleOrderingChange(event) {
    const updatedParams = new URLSearchParams(searchParams);
    const value = event.target.value;

    if (value) {
      updatedParams.set("ordering", value);
    } else {
      updatedParams.delete("ordering");
    }

    updatedParams.delete("page");
    setSearchParams(updatedParams);
  }

  function handleStockChange(event) {
    const updatedParams = new URLSearchParams(searchParams);

    if (event.target.checked) {
      updatedParams.set("in_stock", "true");
    } else {
      updatedParams.delete("in_stock");
    }

    updatedParams.delete("page");
    setSearchParams(updatedParams);
  }

  function handlePriceSubmit(event) {
    event.preventDefault();

    const form = event.currentTarget;
    const formData = new FormData(form);
    const minimum = String(formData.get("min_price") || "").trim();
    const maximum = String(formData.get("max_price") || "").trim();
    const maximumInput = form.elements.max_price;

    maximumInput.setCustomValidity("");

    if (minimum && maximum && Number(minimum) > Number(maximum)) {
      maximumInput.setCustomValidity(
        "Maximum price must be greater than or equal to minimum price.",
      );
      maximumInput.reportValidity();
      return;
    }

    const updatedParams = new URLSearchParams(searchParams);

    if (minimum) {
      updatedParams.set("min_price", minimum);
    } else {
      updatedParams.delete("min_price");
    }

    if (maximum) {
      updatedParams.set("max_price", maximum);
    } else {
      updatedParams.delete("max_price");
    }

    updatedParams.delete("page");
    setSearchParams(updatedParams);
  }

  function handleClearFilters() {
    const updatedParams = new URLSearchParams();

    if (searchTerm) {
      updatedParams.set("search", searchTerm);
    }

    setSearchParams(updatedParams);
    setIsPriceOpen(false);
  }

  function goToPage(nextPage) {
    const updatedParams = new URLSearchParams(searchParams);

    if (nextPage > 1) {
      updatedParams.set("page", String(nextPage));
    } else {
      updatedParams.delete("page");
    }

    setSearchParams(updatedParams);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <section className="mx-auto min-h-[60vh] max-w-360 px-6 py-10 sm:px-8 lg:px-10">
      <div className="border-b border-border pb-8">
        <p className="text-sm font-bold uppercase tracking-[0.2em] text-brand-600">
          ShopSphere catalogue
        </p>

        <h1 className="mt-3 font-display text-3xl font-bold capitalize tracking-tight text-neutral-950 sm:text-4xl">
          {heading}
        </h1>

        <p className="mt-3 text-neutral-600">
          {data
            ? `${data.count} product${data.count === 1 ? "" : "s"} found`
            : "Loading products"}
        </p>
      </div>

      <div className="flex flex-col gap-4 pt-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-5">
          <label className="flex items-center gap-2 text-sm font-medium text-neutral-700">
            Category
            <select
              name="category"
              value={category}
              onChange={handleFilterChange}
              disabled={categoriesPending}
              className="min-h-11 rounded-xl border border-neutral-300 bg-white px-3 text-neutral-950 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:cursor-wait disabled:opacity-60"
            >
              <option value="">
                {categoriesPending ? "Loading..." : "All categories"}
              </option>

              {categories.map((item) => (
                <option key={item.id} value={item.slug}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>

          <label className="flex items-center gap-2 text-sm font-medium text-neutral-700">
            Brand
            <select
              name="brand"
              value={brand}
              onChange={handleFilterChange}
              disabled={brandsPending}
              className="min-h-11 rounded-xl border border-neutral-300 bg-white px-3 text-neutral-950 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:cursor-wait disabled:opacity-60"
            >
              <option value="">
                {brandsPending ? "Loading..." : "All brands"}
              </option>

              {brands.map((item) => (
                <option key={item.id} value={item.slug}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>

          <label className="inline-flex cursor-pointer items-center gap-3 text-sm font-medium text-neutral-700">
            <input
              type="checkbox"
              checked={inStock}
              onChange={handleStockChange}
              className="size-4 rounded border-neutral-300 accent-brand-500"
            />
            In stock only
          </label>

          <button
            type="button"
            onClick={() => setIsPriceOpen((current) => !current)}
            aria-expanded={isPriceOpen}
            aria-controls="price-filter"
            className={`inline-flex min-h-11 items-center gap-2 rounded-xl border px-4 text-sm font-semibold transition ${
              minPrice || maxPrice
                ? "border-brand-500 bg-brand-50 text-brand-700"
                : "border-neutral-300 bg-white text-neutral-800 hover:bg-neutral-100"
            }`}
          >
            Search with price
            <ChevronDown
              aria-hidden="true"
              className={`size-4 transition-transform ${
                isPriceOpen ? "rotate-180" : ""
              }`}
            />
          </button>

          {hasActiveFilters && (
            <button
              type="button"
              onClick={handleClearFilters}
              className="min-h-11 rounded-xl border border-neutral-300 bg-white px-4 text-sm font-semibold text-neutral-800 transition hover:border-red-300 hover:bg-red-50 hover:text-red-700"
            >
              Clear filters
            </button>
          )}
        </div>

        <label className="flex items-center gap-3 text-sm font-medium text-neutral-700">
          Sort by
          <select
            value={ordering}
            onChange={handleOrderingChange}
            className="min-h-11 rounded-xl border border-neutral-300 bg-white px-4 py-2 text-neutral-950 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          >
            <option value="">Default</option>
            <option value="-created_at">Newest</option>
            <option value="name">Name: A–Z</option>
            <option value="catalog_price">Price: Low to high</option>
            <option value="-catalog_price">Price: High to low</option>
          </select>
        </label>
      </div>

      {isPriceOpen && (
        <form
          id="price-filter"
          key={`${minPrice}-${maxPrice}`}
          onSubmit={handlePriceSubmit}
          className="mt-5 flex w-full flex-col gap-3 rounded-2xl border border-border bg-neutral-50 p-4 sm:w-fit sm:flex-row sm:items-end"
        >
          <label className="w-full text-sm font-medium text-neutral-700 sm:w-36">
            Minimum price
            <input
              type="number"
              name="min_price"
              min="0"
              step="1"
              defaultValue={minPrice}
              placeholder="₦0"
              className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-4 text-neutral-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </label>

          <label className="w-full text-sm font-medium text-neutral-700 sm:w-36">
            Maximum price
            <input
              type="number"
              name="max_price"
              min="0"
              step="1"
              defaultValue={maxPrice}
              placeholder="₦100,000"
              className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-4 text-neutral-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </label>

          <button
            type="submit"
            className="min-h-11 rounded-xl bg-neutral-950 px-6 py-2 font-semibold text-white transition hover:bg-neutral-800"
          >
            Apply price
          </button>
        </form>
      )}

      {isPending && (
        <div
          aria-label="Loading products"
          className="grid grid-cols-2 gap-3 py-8 sm:gap-5 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
        >
          {Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="animate-pulse">
              <div className="aspect-4/5 rounded-2xl bg-neutral-200" />
              <div className="mt-4 h-3 w-20 rounded bg-neutral-200" />
              <div className="mt-3 h-4 w-full rounded bg-neutral-200" />
              <div className="mt-3 h-5 w-24 rounded bg-neutral-200" />
            </div>
          ))}
        </div>
      )}

      {isError && (
        <div className="flex min-h-80 flex-col items-center justify-center text-center">
          <div className="flex size-14 items-center justify-center rounded-full bg-neutral-100 text-neutral-600">
            <SearchX aria-hidden="true" className="size-6" />
          </div>

          <h2 className="mt-5 font-display text-xl font-bold text-neutral-950">
            We couldn’t load the products
          </h2>

          <p className="mt-2 max-w-md text-neutral-600">
            Something went wrong while loading the catalogue. Please try again.
          </p>

          <button
            type="button"
            onClick={() => refetch()}
            className="button-primary mt-6"
          >
            Try again
          </button>
        </div>
      )}

      {!isPending && !isError && products.length === 0 && (
        <div className="flex min-h-80 flex-col items-center justify-center text-center">
          <div className="flex size-14 items-center justify-center rounded-full bg-neutral-100 text-neutral-600">
            <SearchX aria-hidden="true" className="size-6" />
          </div>

          <h2 className="mt-5 font-display text-xl font-bold text-neutral-950">
            No matching products
          </h2>

          <p className="mt-2 max-w-md text-neutral-600">
            Try another search or category.
          </p>
        </div>
      )}

      {!isPending && !isError && products.length > 0 && (
        <>
          <div className="grid grid-cols-2 gap-3 py-8 sm:gap-5 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>

          {(data.previous || data.next) && (
            <nav
              aria-label="Product pages"
              className="flex items-center justify-center gap-3 pb-8"
            >
              <button
                type="button"
                disabled={!data.previous}
                onClick={() => goToPage(page - 1)}
                className="button-secondary disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-sm font-semibold text-neutral-600">
                Page {page}
              </span>
              <button
                type="button"
                disabled={!data.next}
                onClick={() => goToPage(page + 1)}
                className="button-secondary disabled:opacity-40"
              >
                Next
              </button>
            </nav>
          )}
        </>
      )}
    </section>
  );
}

export default ProductListPage;
