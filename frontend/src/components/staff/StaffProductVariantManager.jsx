import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { Boxes, Pencil, Plus, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import {
  createStaffProductVariant,
  getStaffProductVariants,
  updateStaffProductVariant,
} from "../../api/staff";
import { getApiError } from "../../lib/errors";
import { formatNaira } from "../../lib/format";

const emptyForm = {
  name: "",
  sku: "",
  attributes: "{}",
  price: "",
  discount_price: "",
  initial_quantity: "0",
  is_active: true,
};

function getResults(data) {
  return Array.isArray(data) ? data : data?.results || [];
}

function StaffProductVariantManager({ product, onClose }) {
  const queryClient = useQueryClient();
  const [editingVariant, setEditingVariant] = useState(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);

  const {
    data,
    isPending,
    isError,
    error,
  } = useQuery({
    queryKey: ["staff-product-variants", product.id],
    queryFn: () =>
      getStaffProductVariants(product.id, {
        ordering: "id",
      }),
  });

  const saveMutation = useMutation({
    mutationFn: ({ variantId, payload }) => {
      if (variantId) {
        return updateStaffProductVariant(variantId, payload);
      }

      return createStaffProductVariant(product.id, payload);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["staff-product-variants", product.id],
      });
      queryClient.invalidateQueries({
        queryKey: ["staff-products"],
      });
      queryClient.invalidateQueries({
        queryKey: ["staff-inventory"],
      });
      queryClient.invalidateQueries({
        queryKey: ["products"],
      });

      toast.success(
        variables.variantId
          ? "Variant updated successfully."
          : "Variant and inventory created successfully.",
      );
      closeForm();
    },
    onError: (mutationError) => {
      toast.error(
        getApiError(
          mutationError,
          editingVariant
            ? "Unable to update this variant."
            : "Unable to create this variant.",
        ),
      );
    },
  });

  const variants = getResults(data);

  function closeForm() {
    setEditingVariant(null);
    setForm(emptyForm);
    setIsFormOpen(false);
  }

  function openCreateForm() {
    setEditingVariant(null);
    setForm(emptyForm);
    setIsFormOpen(true);
  }

  function openEditForm(variant) {
    setEditingVariant(variant);
    setForm({
      name: variant.name || "",
      sku: variant.sku || "",
      attributes: JSON.stringify(
        variant.attributes || {},
        null,
        2,
      ),
      price: variant.price ?? "",
      discount_price: variant.discount_price ?? "",
      initial_quantity: "0",
      is_active: Boolean(variant.is_active),
    });
    setIsFormOpen(true);
  }

  function updateField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function handleSubmit(event) {
    event.preventDefault();

    let attributes;

    try {
      attributes = JSON.parse(form.attributes || "{}");
    } catch {
      toast.error("Attributes must be valid JSON.");
      return;
    }

    if (
      !attributes ||
      Array.isArray(attributes) ||
      typeof attributes !== "object"
    ) {
      toast.error("Attributes must be a JSON object.");
      return;
    }

    const payload = {
      name: form.name.trim(),
      sku: form.sku.trim().toUpperCase(),
      attributes,
      price: form.price,
      discount_price: form.discount_price || null,
      is_active: form.is_active,
    };

    if (!editingVariant) {
      payload.initial_quantity = Number(form.initial_quantity || 0);
    }

    saveMutation.mutate({
      variantId: editingVariant?.id || null,
      payload,
    });
  }

  return (
    <div
      className="fixed inset-0 z-70 overflow-y-auto bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="variant-manager-title"
    >
      <div className="mx-auto my-6 max-w-5xl rounded-2xl bg-white shadow-2xl">
        <header className="flex items-start justify-between gap-4 border-b border-neutral-200 p-5 sm:p-6">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
              {product.name}
            </p>
            <h2
              id="variant-manager-title"
              className="mt-1 text-2xl font-bold text-neutral-950"
            >
              Variants and SKUs
            </h2>
            <p className="mt-2 text-sm text-neutral-600">
              Every variant must have its own globally unique SKU.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close variant manager"
            className="flex size-10 shrink-0 items-center justify-center rounded-full hover:bg-neutral-100"
          >
            <X className="size-5" />
          </button>
        </header>

        <div className="space-y-6 p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-neutral-600">
              Stock changes after creation are made on the Inventory page.
            </p>
            <button
              type="button"
              onClick={openCreateForm}
              className="inline-flex min-h-10 items-center gap-2 rounded-xl bg-black px-4 text-sm font-bold text-white hover:bg-neutral-800"
            >
              <Plus className="size-4" />
              Add variant
            </button>
          </div>

          {isFormOpen && (
            <form
              onSubmit={handleSubmit}
              className="grid gap-5 rounded-2xl border border-neutral-200 bg-neutral-50 p-5 md:grid-cols-2"
            >
              <div className="flex items-start justify-between gap-3 md:col-span-2">
                <div>
                  <h3 className="font-bold text-neutral-950">
                    {editingVariant
                      ? "Edit variant"
                      : "Create variant"}
                  </h3>
                  <p className="mt-1 text-xs text-neutral-500">
                    Example SKU: NIKE-AIR-BLK-42
                  </p>
                </div>
                <button
                  type="button"
                  onClick={closeForm}
                  aria-label="Close variant form"
                  className="flex size-9 items-center justify-center rounded-full hover:bg-neutral-200"
                >
                  <X className="size-4" />
                </button>
              </div>

              <div>
                <label
                  htmlFor="staff-variant-name"
                  className="text-sm font-semibold text-neutral-800"
                >
                  Variant name
                </label>
                <input
                  id="staff-variant-name"
                  value={form.name}
                  onChange={(event) =>
                    updateField("name", event.target.value)
                  }
                  placeholder="Black / Size 42"
                  required
                  maxLength={150}
                  className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-4 text-sm outline-none focus:border-black"
                />
              </div>

              <div>
                <label
                  htmlFor="staff-variant-sku"
                  className="text-sm font-semibold text-neutral-800"
                >
                  Unique SKU
                </label>
                <input
                  id="staff-variant-sku"
                  value={form.sku}
                  onChange={(event) =>
                    updateField(
                      "sku",
                      event.target.value.toUpperCase(),
                    )
                  }
                  placeholder="NIKE-AIR-BLK-42"
                  required
                  maxLength={50}
                  autoCapitalize="characters"
                  className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-4 font-mono text-sm uppercase outline-none focus:border-black"
                />
              </div>

              <div>
                <label
                  htmlFor="staff-variant-price"
                  className="text-sm font-semibold text-neutral-800"
                >
                  Regular price (NGN)
                </label>
                <input
                  id="staff-variant-price"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.price}
                  onChange={(event) =>
                    updateField("price", event.target.value)
                  }
                  required
                  className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-4 text-sm outline-none focus:border-black"
                />
              </div>

              <div>
                <label
                  htmlFor="staff-variant-discount-price"
                  className="text-sm font-semibold text-neutral-800"
                >
                  Discount price (optional)
                </label>
                <input
                  id="staff-variant-discount-price"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.discount_price}
                  onChange={(event) =>
                    updateField(
                      "discount_price",
                      event.target.value,
                    )
                  }
                  className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-4 text-sm outline-none focus:border-black"
                />
              </div>

              {!editingVariant && (
                <div>
                  <label
                    htmlFor="staff-variant-initial-quantity"
                    className="text-sm font-semibold text-neutral-800"
                  >
                    Initial stock quantity
                  </label>
                  <input
                    id="staff-variant-initial-quantity"
                    type="number"
                    min="0"
                    step="1"
                    value={form.initial_quantity}
                    onChange={(event) =>
                      updateField(
                        "initial_quantity",
                        event.target.value,
                      )
                    }
                    required
                    className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-4 text-sm outline-none focus:border-black"
                  />
                </div>
              )}

              <div className={editingVariant ? "md:col-span-2" : ""}>
                <label
                  htmlFor="staff-variant-attributes"
                  className="text-sm font-semibold text-neutral-800"
                >
                  Attributes (JSON)
                </label>
                <textarea
                  id="staff-variant-attributes"
                  value={form.attributes}
                  onChange={(event) =>
                    updateField("attributes", event.target.value)
                  }
                  rows={4}
                  spellCheck="false"
                  placeholder={'{"color": "Black", "size": "42"}'}
                  className="mt-2 w-full rounded-xl border border-neutral-300 bg-white px-4 py-3 font-mono text-sm outline-none focus:border-black"
                />
              </div>

              <label className="flex items-center gap-3 text-sm font-semibold text-neutral-800 md:col-span-2">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(event) =>
                    updateField("is_active", event.target.checked)
                  }
                  className="size-4 accent-black"
                />
                Variant is active
              </label>

              <div className="flex flex-wrap gap-3 md:col-span-2">
                <button
                  type="submit"
                  disabled={saveMutation.isPending}
                  className="rounded-xl bg-black px-5 py-3 text-sm font-bold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {saveMutation.isPending
                    ? "Saving…"
                    : editingVariant
                      ? "Save variant"
                      : "Create variant"}
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
          )}

          {isPending ? (
            <p className="rounded-xl bg-neutral-50 p-5 text-neutral-600">
              Loading variants…
            </p>
          ) : isError ? (
            <p className="rounded-xl bg-red-50 p-5 text-red-700">
              {getApiError(error, "Unable to load product variants.")}
            </p>
          ) : variants.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-neutral-300 p-8 text-center">
              <Boxes className="mx-auto size-9 text-neutral-400" />
              <p className="mt-3 font-bold text-neutral-900">
                No variants yet
              </p>
              <p className="mt-1 text-sm text-neutral-500">
                Add at least one variant before selling this product.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-2xl border border-neutral-200">
              <table className="min-w-full divide-y divide-neutral-200">
                <thead className="bg-neutral-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-neutral-500">
                      Variant / SKU
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-neutral-500">
                      Attributes
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-neutral-500">
                      Price
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-neutral-500">
                      Available
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-neutral-500">
                      Status
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-bold uppercase tracking-wide text-neutral-500">
                      Action
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200">
                  {variants.map((variant) => (
                    <tr key={variant.id}>
                      <td className="px-4 py-4">
                        <p className="font-semibold text-neutral-950">
                          {variant.name}
                        </p>
                        <p className="mt-1 font-mono text-xs text-neutral-600">
                          {variant.sku}
                        </p>
                      </td>
                      <td className="px-4 py-4 text-xs text-neutral-600">
                        {Object.keys(variant.attributes || {}).length
                          ? Object.entries(variant.attributes)
                              .map(([key, value]) => `${key}: ${value}`)
                              .join(" · ")
                          : "Default"}
                      </td>
                      <td className="px-4 py-4 text-sm font-semibold text-neutral-950">
                        {formatNaira(
                          variant.current_price ?? variant.price,
                        )}
                        {variant.discount_price && (
                          <p className="mt-1 text-xs font-normal text-neutral-400 line-through">
                            {formatNaira(variant.price)}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-4 text-sm text-neutral-700">
                        {variant.inventory?.available_quantity ?? 0}
                      </td>
                      <td className="px-4 py-4">
                        <span
                          className={`inline-flex rounded-full px-3 py-1 text-xs font-bold ${
                            variant.is_active
                              ? "bg-green-100 text-green-800"
                              : "bg-neutral-200 text-neutral-700"
                          }`}
                        >
                          {variant.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-right">
                        <button
                          type="button"
                          onClick={() => openEditForm(variant)}
                          className="inline-flex items-center gap-1 rounded-lg border border-neutral-300 px-3 py-2 text-xs font-bold text-neutral-700 hover:bg-neutral-100"
                        >
                          <Pencil className="size-3.5" />
                          Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default StaffProductVariantManager;
