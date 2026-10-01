import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Boxes, ImagePlus, Pencil, Plus, Search, Tags, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import {
  createStaffProduct,
  getStaffBrands,
  getStaffCategories,
  getStaffProducts,
  updateStaffProduct,
} from "../../api/staff";
import StaffCategoryManager from "../../components/staff/StaffCategoryManager";
import StaffProductImageManager from "../../components/staff/StaffProductImageManager";
import StaffProductVariantManager from "../../components/staff/StaffProductVariantManager";
import { getApiError } from "../../lib/errors";
import { formatNaira } from "../../lib/format";

const emptyForm = {
  name: "",
  slug: "",
  description: "",
  category_id: "",
  brand_id: "",
  is_active: true,
};

function getResults(data) {
  if (Array.isArray(data)) {
    return data;
  }

  return data?.results || [];
}

function createSlug(value) {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");
}

function StaffProductListPage() {
  const queryClient = useQueryClient();

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [ordering, setOrdering] = useState("-created_at");
  const [page, setPage] = useState(1);

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [slugWasEdited, setSlugWasEdited] = useState(false);

  const [isCategoryManagerOpen, setIsCategoryManagerOpen] = useState(false);
  const [imageProduct, setImageProduct] = useState(null);
  const [variantProduct, setVariantProduct] = useState(null);

  const productParams = {
    page,
    ordering,
  };

  if (search) {
    productParams.search = search;
  }

  if (activeFilter) {
    productParams.is_active = activeFilter;
  }

  if (categoryFilter) {
    productParams.category = categoryFilter;
  }

  const {
    data: productData,
    isPending,
    isError,
    error,
  } = useQuery({
    queryKey: [
      "staff-products",
      search,
      activeFilter,
      categoryFilter,
      ordering,
      page,
    ],
    queryFn: () => getStaffProducts(productParams),
  });

  const { data: categoryData } = useQuery({
    queryKey: ["staff-categories"],
    queryFn: () =>
      getStaffCategories({
        ordering: "name",
        page_size: 100,
      }),
  });

  const { data: brandData } = useQuery({
    queryKey: ["staff-brands"],
    queryFn: () =>
      getStaffBrands({
        ordering: "name",
        page_size: 100,
      }),
  });

  const saveMutation = useMutation({
    mutationFn: ({ productId, payload }) => {
      if (productId) {
        return updateStaffProduct(productId, payload);
      }

      return createStaffProduct(payload);
    },

    onSuccess: (savedProduct, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["staff-products"],
      });

      queryClient.invalidateQueries({
        queryKey: ["staff-dashboard"],
      });

      toast.success(
        variables.productId
          ? "Product updated successfully."
          : "Product created. Now add its variant and unique SKU.",
      );

      closeForm();

      if (!variables.productId && savedProduct?.id) {
        setVariantProduct(savedProduct);
      }
    },

    onError: (mutationError) => {
      toast.error(
        getApiError(
          mutationError,
          editingProduct
            ? "Unable to update this product."
            : "Unable to create the product.",
        ),
      );
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ productId, isActive }) =>
      updateStaffProduct(productId, {
        is_active: isActive,
      }),

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["staff-products"],
      });

      queryClient.invalidateQueries({
        queryKey: ["staff-dashboard"],
      });

      toast.success("Product status updated.");
    },

    onError: (mutationError) => {
      toast.error(
        getApiError(mutationError, "Unable to update the product status."),
      );
    },
  });

  const products = getResults(productData);
  const categories = getResults(categoryData);
  const brands = getResults(brandData);

  function closeForm() {
    setIsFormOpen(false);
    setEditingProduct(null);
    setForm(emptyForm);
    setSlugWasEdited(false);
  }

  function openCreateForm() {
    setEditingProduct(null);
    setForm(emptyForm);
    setSlugWasEdited(false);
    setIsFormOpen(true);
  }

  function openEditForm(product) {
    setEditingProduct(product);

    setForm({
      name: product.name || "",
      slug: product.slug || "",
      description: product.description || "",
      category_id: product.category?.id ? String(product.category.id) : "",
      brand_id: product.brand?.id ? String(product.brand.id) : "",
      is_active: Boolean(product.is_active),
    });

    setSlugWasEdited(true);
    setIsFormOpen(true);
  }

  function handleNameChange(event) {
    const name = event.target.value;

    setForm((current) => ({
      ...current,
      name,
      slug: slugWasEdited ? current.slug : createSlug(name),
    }));
  }

  function handleSearch(event) {
    event.preventDefault();
    setSearch(searchInput.trim());
    setPage(1);
  }

  function handleSubmit(event) {
    event.preventDefault();

    if (!form.category_id) {
      toast.error("Select a product category.");
      return;
    }

    const payload = {
      name: form.name.trim(),
      slug: form.slug.trim(),
      description: form.description.trim(),
      category_id: Number(form.category_id),
      brand_id: form.brand_id ? Number(form.brand_id) : null,
      is_active: form.is_active,
    };

    saveMutation.mutate({
      productId: editingProduct?.id || null,
      payload,
    });
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Catalog management
          </p>

          <h1 className="mt-2 text-3xl font-bold tracking-tight text-neutral-950">
            Products
          </h1>

          <p className="mt-2 text-sm text-neutral-500">
            Manage products, images, variants, unique SKUs, and availability.
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => setIsCategoryManagerOpen(true)}
            className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-neutral-300 bg-white px-5 text-sm font-bold text-neutral-800 hover:bg-neutral-100"
          >
            <Tags className="size-4" />
            Categories
          </button>

          <button
            type="button"
            onClick={openCreateForm}
            className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-black px-5 text-sm font-bold text-white hover:bg-neutral-800"
          >
            <Plus className="size-4" />
            Add product
          </button>
        </div>
      </section>

      <section className="rounded-2xl border border-neutral-200 bg-white p-4">
        <div className="grid gap-3 lg:grid-cols-[minmax(240px,1fr)_180px_200px_180px]">
          <form onSubmit={handleSearch} className="relative">
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-neutral-500"
            />

            <input
              type="search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Search name, slug or SKU"
              className="min-h-11 w-full rounded-xl border border-neutral-300 pl-11 pr-4 text-sm outline-none focus:border-black"
            />
          </form>

          <select
            value={activeFilter}
            onChange={(event) => {
              setActiveFilter(event.target.value);
              setPage(1);
            }}
            className="min-h-11 rounded-xl border border-neutral-300 bg-white px-3 text-sm outline-none focus:border-black"
          >
            <option value="">All statuses</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>

          <select
            value={categoryFilter}
            onChange={(event) => {
              setCategoryFilter(event.target.value);
              setPage(1);
            }}
            className="min-h-11 rounded-xl border border-neutral-300 bg-white px-3 text-sm outline-none focus:border-black"
          >
            <option value="">All categories</option>

            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>

          <select
            value={ordering}
            onChange={(event) => {
              setOrdering(event.target.value);
              setPage(1);
            }}
            className="min-h-11 rounded-xl border border-neutral-300 bg-white px-3 text-sm outline-none focus:border-black"
          >
            <option value="-created_at">Newest first</option>
            <option value="created_at">Oldest first</option>
            <option value="name">Name A–Z</option>
            <option value="-name">Name Z–A</option>
            <option value="-updated_at">Recently updated</option>
          </select>
        </div>
      </section>

      {isFormOpen && (
        <section className="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-neutral-950">
                {editingProduct ? "Edit product" : "Create product"}
              </h2>

              <p className="mt-1 text-sm text-neutral-500">
                Save the product first, then use Images to upload its photos.
              </p>
            </div>

            <button
              type="button"
              onClick={closeForm}
              aria-label="Close product form"
              className="flex size-10 items-center justify-center rounded-full hover:bg-neutral-100"
            >
              <X className="size-5" />
            </button>
          </div>

          <form
            onSubmit={handleSubmit}
            className="mt-6 grid gap-5 md:grid-cols-2"
          >
            <div>
              <label
                htmlFor="staff-product-name"
                className="text-sm font-semibold text-neutral-800"
              >
                Product name
              </label>

              <input
                id="staff-product-name"
                value={form.name}
                onChange={handleNameChange}
                required
                maxLength={255}
                className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 px-4 text-sm outline-none focus:border-black"
              />
            </div>

            <div>
              <label
                htmlFor="staff-product-slug"
                className="text-sm font-semibold text-neutral-800"
              >
                Slug
              </label>

              <input
                id="staff-product-slug"
                value={form.slug}
                onChange={(event) => {
                  setSlugWasEdited(true);

                  setForm((current) => ({
                    ...current,
                    slug: createSlug(event.target.value),
                  }));
                }}
                required
                className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 px-4 text-sm outline-none focus:border-black"
              />
            </div>

            <div>
              <div className="flex items-center justify-between gap-3">
                <label
                  htmlFor="staff-product-category"
                  className="text-sm font-semibold text-neutral-800"
                >
                  Category
                </label>

                <button
                  type="button"
                  onClick={() => setIsCategoryManagerOpen(true)}
                  className="text-xs font-bold text-neutral-600 hover:text-black hover:underline"
                >
                  Manage categories
                </button>
              </div>

              <select
                id="staff-product-category"
                value={form.category_id}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    category_id: event.target.value,
                  }))
                }
                required
                className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-4 text-sm outline-none focus:border-black"
              >
                <option value="">Select category</option>

                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor="staff-product-brand"
                className="text-sm font-semibold text-neutral-800"
              >
                Brand
              </label>

              <select
                id="staff-product-brand"
                value={form.brand_id}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    brand_id: event.target.value,
                  }))
                }
                className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-4 text-sm outline-none focus:border-black"
              >
                <option value="">No brand</option>

                {brands.map((brand) => (
                  <option key={brand.id} value={brand.id}>
                    {brand.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="md:col-span-2">
              <label
                htmlFor="staff-product-description"
                className="text-sm font-semibold text-neutral-800"
              >
                Description
              </label>

              <textarea
                id="staff-product-description"
                value={form.description}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
                required
                rows={5}
                className="mt-2 w-full rounded-xl border border-neutral-300 px-4 py-3 text-sm outline-none focus:border-black"
              />
            </div>

            <label className="flex items-center gap-3 text-sm font-semibold text-neutral-800 md:col-span-2">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    is_active: event.target.checked,
                  }))
                }
                className="size-4 accent-black"
              />
              Product is active
            </label>

            <div className="flex flex-wrap gap-3 md:col-span-2">
              <button
                type="submit"
                disabled={saveMutation.isPending}
                className="rounded-xl bg-black px-5 py-3 text-sm font-bold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {saveMutation.isPending
                  ? "Saving…"
                  : editingProduct
                    ? "Save changes"
                    : "Create product"}
              </button>

              <button
                type="button"
                onClick={closeForm}
                disabled={saveMutation.isPending}
                className="rounded-xl border border-neutral-300 px-5 py-3 text-sm font-bold text-neutral-700 hover:bg-neutral-100"
              >
                Cancel
              </button>
            </div>
          </form>
        </section>
      )}

      <section className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
        {isPending ? (
          <p className="p-6 text-neutral-600">Loading products…</p>
        ) : isError ? (
          <p className="m-5 rounded-xl bg-red-50 p-4 text-red-700">
            {getApiError(error, "Unable to load products.")}
          </p>
        ) : products.length === 0 ? (
          <div className="p-8 text-center">
            <p className="font-semibold text-neutral-800">No products found</p>

            <p className="mt-1 text-sm text-neutral-500">
              Change the filters or create a product.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-neutral-200">
              <thead className="bg-neutral-50">
                <tr>
                  <th className="px-5 py-4 text-left text-xs font-bold uppercase tracking-wide text-neutral-500">
                    Product
                  </th>
                  <th className="px-5 py-4 text-left text-xs font-bold uppercase tracking-wide text-neutral-500">
                    Category
                  </th>
                  <th className="px-5 py-4 text-left text-xs font-bold uppercase tracking-wide text-neutral-500">
                    Price
                  </th>
                  <th className="px-5 py-4 text-left text-xs font-bold uppercase tracking-wide text-neutral-500">
                    Variants / SKU
                  </th>
                  <th className="px-5 py-4 text-left text-xs font-bold uppercase tracking-wide text-neutral-500">
                    Status
                  </th>
                  <th className="px-5 py-4 text-right text-xs font-bold uppercase tracking-wide text-neutral-500">
                    Actions
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-neutral-200">
                {products.map((product) => {
                  const primaryImage =
                    product.images?.find((image) => image.is_primary) ||
                    product.images?.[0];

                  return (
                    <tr key={product.id} className="hover:bg-neutral-50">
                      <td className="px-5 py-4">
                        <div className="flex min-w-60 items-center gap-3">
                          <div className="flex size-14 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-neutral-100">
                            {primaryImage?.image ? (
                              <img
                                src={primaryImage.image}
                                alt={primaryImage.alt_text || product.name}
                                className="h-full w-full object-contain"
                              />
                            ) : (
                              <span className="text-xs text-neutral-400">
                                No image
                              </span>
                            )}
                          </div>

                          <div>
                            <p className="font-bold text-neutral-950">
                              {product.name}
                            </p>
                            <p className="mt-1 text-xs text-neutral-500">
                              {product.slug}
                            </p>
                            {product.brand?.name && (
                              <p className="mt-1 text-xs text-neutral-500">
                                {product.brand.name}
                              </p>
                            )}
                          </div>
                        </div>
                      </td>

                      <td className="px-5 py-4 text-sm text-neutral-700">
                        {product.category?.name || "—"}
                      </td>

                      <td className="px-5 py-4 text-sm font-semibold text-neutral-950">
                        {product.starting_price
                          ? formatNaira(product.starting_price)
                          : "No price"}
                      </td>

                      <td className="px-5 py-4 text-sm text-neutral-700">
                        <p>
                          {product.variant_count}{" "}
                          {product.variant_count === 1 ? "variant" : "variants"}
                        </p>
                        {product.variants?.length > 0 ? (
                          <p className="mt-1 max-w-52 truncate font-mono text-xs text-neutral-500">
                            {product.variants
                              .map((variant) => variant.sku)
                              .join(", ")}
                          </p>
                        ) : (
                          <p className="mt-1 text-xs font-semibold text-amber-700">
                            SKU required
                          </p>
                        )}
                      </td>

                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex rounded-full px-3 py-1 text-xs font-bold ${
                            product.is_active
                              ? "bg-green-100 text-green-800"
                              : "bg-neutral-200 text-neutral-700"
                          }`}
                        >
                          {product.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>

                      <td className="px-5 py-4">
                        <div className="flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => setVariantProduct(product)}
                            className="inline-flex items-center gap-1 rounded-lg border border-neutral-300 px-3 py-2 text-xs font-bold text-neutral-700 hover:bg-neutral-100"
                          >
                            <Boxes className="size-3.5" />
                            Variants / SKU
                          </button>

                          <button
                            type="button"
                            onClick={() => setImageProduct(product)}
                            className="inline-flex items-center gap-1 rounded-lg border border-neutral-300 px-3 py-2 text-xs font-bold text-neutral-700 hover:bg-neutral-100"
                          >
                            <ImagePlus className="size-3.5" />
                            Images
                          </button>

                          <button
                            type="button"
                            onClick={() => openEditForm(product)}
                            className="inline-flex items-center gap-1 rounded-lg border border-neutral-300 px-3 py-2 text-xs font-bold text-neutral-700 hover:bg-neutral-100"
                          >
                            <Pencil className="size-3.5" />
                            Edit
                          </button>

                          <button
                            type="button"
                            disabled={statusMutation.isPending}
                            onClick={() =>
                              statusMutation.mutate({
                                productId: product.id,
                                isActive: !product.is_active,
                              })
                            }
                            className={`rounded-lg px-3 py-2 text-xs font-bold ${
                              product.is_active
                                ? "bg-red-50 text-red-700 hover:bg-red-100"
                                : "bg-green-50 text-green-700 hover:bg-green-100"
                            }`}
                          >
                            {product.is_active ? "Deactivate" : "Activate"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {!isPending && !isError && productData && (
          <div className="flex items-center justify-between border-t border-neutral-200 px-5 py-4">
            <p className="text-sm text-neutral-500">
              {productData.count ?? products.length} products
            </p>

            <div className="flex gap-2">
              <button
                type="button"
                disabled={!productData.previous}
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                className="rounded-lg border border-neutral-300 px-3 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40"
              >
                Previous
              </button>

              <span className="flex min-w-10 items-center justify-center text-sm font-semibold">
                {page}
              </span>

              <button
                type="button"
                disabled={!productData.next}
                onClick={() => setPage((current) => current + 1)}
                className="rounded-lg border border-neutral-300 px-3 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </section>

      {isCategoryManagerOpen && (
        <StaffCategoryManager onClose={() => setIsCategoryManagerOpen(false)} />
      )}

      {imageProduct && (
        <StaffProductImageManager
          product={imageProduct}
          onClose={() => setImageProduct(null)}
        />
      )}

      {variantProduct && (
        <StaffProductVariantManager
          product={variantProduct}
          onClose={() => setVariantProduct(null)}
        />
      )}
    </div>
  );
}

export default StaffProductListPage;
