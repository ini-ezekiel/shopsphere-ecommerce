import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import {
  createStaffBrand,
  getStaffBrands,
  updateStaffBrand,
} from "../../api/staff";
import { getApiError } from "../../lib/errors";

const initialForm = {
  name: "",
  slug: "",
  is_active: true,
};

function getResults(data) {
  return Array.isArray(data) ? data : data?.results || [];
}

function createSlug(value) {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");
}

function StaffBrandManager({ onClose }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState(initialForm);
  const [slugEdited, setSlugEdited] = useState(false);

  const { data, isPending, isError, error } = useQuery({
    queryKey: ["staff-brands"],
    queryFn: () =>
      getStaffBrands({
        ordering: "name",
        page_size: 100,
      }),
  });

  const createMutation = useMutation({
    mutationFn: createStaffBrand,

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["staff-brands"],
      });

      queryClient.invalidateQueries({
        queryKey: ["staff-products"],
      });

      setForm(initialForm);
      setSlugEdited(false);
      toast.success("Brand created successfully.");
    },

    onError: (mutationError) => {
      toast.error(getApiError(mutationError, "Unable to create brand."));
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ brandId, isActive }) =>
      updateStaffBrand(brandId, {
        is_active: isActive,
      }),

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["staff-brands"],
      });

      queryClient.invalidateQueries({
        queryKey: ["staff-products"],
      });

      toast.success("Brand status updated.");
    },

    onError: (mutationError) => {
      toast.error(getApiError(mutationError, "Unable to update brand."));
    },
  });

  const brands = getResults(data);

  function handleSubmit(event) {
    event.preventDefault();

    createMutation.mutate({
      name: form.name.trim(),
      slug: form.slug.trim(),
      is_active: form.is_active,
    });
  }

  return (
    <div className="fixed inset-0 z-100 flex items-center justify-center bg-black/50 p-4">
      <section className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white shadow-2xl">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-neutral-200 bg-white px-5 py-4">
          <div>
            <h2 className="text-xl font-bold">Product brands</h2>

            <p className="mt-1 text-sm text-neutral-500">
              Create and manage brands available to products.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close brand manager"
            className="flex size-10 items-center justify-center rounded-full hover:bg-neutral-100"
          >
            <X className="size-5" />
          </button>
        </header>

        <div className="grid gap-6 p-5 lg:grid-cols-[1fr_1.2fr]">
          <form
            onSubmit={handleSubmit}
            className="space-y-4 rounded-2xl bg-neutral-50 p-5"
          >
            <h3 className="font-bold">Add brand</h3>

            <div>
              <label htmlFor="brand-name" className="text-sm font-semibold">
                Name
              </label>

              <input
                id="brand-name"
                value={form.name}
                onChange={(event) => {
                  const name = event.target.value;

                  setForm((current) => ({
                    ...current,
                    name,
                    slug: slugEdited ? current.slug : createSlug(name),
                  }));
                }}
                required
                maxLength={255}
                className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-4 text-sm outline-none focus:border-black"
              />
            </div>

            <div>
              <label htmlFor="brand-slug" className="text-sm font-semibold">
                Slug
              </label>

              <input
                id="brand-slug"
                value={form.slug}
                onChange={(event) => {
                  setSlugEdited(true);

                  setForm((current) => ({
                    ...current,
                    slug: createSlug(event.target.value),
                  }));
                }}
                required
                className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-4 text-sm outline-none focus:border-black"
              />
            </div>

            <label className="flex items-center gap-3 text-sm font-semibold">
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
              Brand is active
            </label>

            <button
              type="submit"
              disabled={createMutation.isPending}
              className="inline-flex items-center gap-2 rounded-xl bg-black px-5 py-3 text-sm font-bold text-white disabled:opacity-60"
            >
              <Plus className="size-4" />

              {createMutation.isPending ? "Creating…" : "Create brand"}
            </button>
          </form>

          <div>
            <h3 className="font-bold">Existing brands</h3>

            {isPending ? (
              <p className="mt-4 text-sm text-neutral-500">Loading brands…</p>
            ) : isError ? (
              <p className="mt-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">
                {getApiError(error, "Unable to load brands.")}
              </p>
            ) : brands.length === 0 ? (
              <p className="mt-4 text-sm text-neutral-500">
                No brands have been created.
              </p>
            ) : (
              <div className="mt-4 divide-y divide-neutral-200 rounded-2xl border border-neutral-200">
                {brands.map((brand) => (
                  <article
                    key={brand.id}
                    className="flex items-center justify-between gap-4 p-4"
                  >
                    <div>
                      <p className="font-semibold">{brand.name}</p>

                      <p className="mt-1 text-xs text-neutral-500">
                        {brand.slug}
                      </p>
                    </div>

                    <button
                      type="button"
                      disabled={statusMutation.isPending}
                      onClick={() =>
                        statusMutation.mutate({
                          brandId: brand.id,
                          isActive: !brand.is_active,
                        })
                      }
                      className={`rounded-lg px-3 py-2 text-xs font-bold ${
                        brand.is_active
                          ? "bg-red-50 text-red-700"
                          : "bg-green-50 text-green-700"
                      }`}
                    >
                      {brand.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </article>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

export default StaffBrandManager;
