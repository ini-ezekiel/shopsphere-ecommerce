import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  AlertTriangle,
  Check,
  Pencil,
  Search,
  X,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import {
  getStaffInventory,
  updateStaffInventory,
} from "../../api/staff";
import { getApiError } from "../../lib/errors";

function getResults(data) {
  if (Array.isArray(data)) {
    return data;
  }

  return data?.results || [];
}

function formatDateTime(value) {
  if (!value) {
    return "Not available";
  }

  return new Intl.DateTimeFormat("en-NG", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function getStockDetails(availableQuantity) {
  const quantity = Number(availableQuantity || 0);

  if (quantity <= 0) {
    return {
      label: "Out of stock",
      classes: "bg-red-100 text-red-800",
    };
  }

  if (quantity <= 5) {
    return {
      label: "Low stock",
      classes: "bg-amber-100 text-amber-800",
    };
  }

  return {
    label: "In stock",
    classes: "bg-green-100 text-green-800",
  };
}

function StaffInventoryPage() {
  const queryClient = useQueryClient();

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [stockStatus, setStockStatus] = useState("");
  const [ordering, setOrdering] = useState(
    "variant__product__name",
  );
  const [page, setPage] = useState(1);

  const [editingInventoryId, setEditingInventoryId] =
    useState(null);
  const [quantity, setQuantity] = useState("");

  const params = {
    page,
    ordering,
  };

  if (search) {
    params.search = search;
  }

  if (stockStatus) {
    params.stock_status = stockStatus;
  }

  const {
    data,
    isPending,
    isError,
    error,
  } = useQuery({
    queryKey: [
      "staff-inventory",
      search,
      stockStatus,
      ordering,
      page,
    ],
    queryFn: () => getStaffInventory(params),
  });

  const updateMutation = useMutation({
    mutationFn: ({ inventoryId, newQuantity }) =>
      updateStaffInventory(inventoryId, {
        quantity: newQuantity,
      }),

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["staff-inventory"],
      });

      queryClient.invalidateQueries({
        queryKey: ["staff-products"],
      });

      queryClient.invalidateQueries({
        queryKey: ["staff-dashboard"],
      });

      setEditingInventoryId(null);
      setQuantity("");

      toast.success("Inventory quantity updated.");
    },

    onError: (mutationError) => {
      toast.error(
        getApiError(
          mutationError,
          "Unable to update inventory.",
        ),
      );
    },
  });

  const inventoryItems = getResults(data);

  function handleSearch(event) {
    event.preventDefault();
    setSearch(searchInput.trim());
    setPage(1);
  }

  function beginEditing(inventory) {
    setEditingInventoryId(inventory.id);
    setQuantity(String(inventory.quantity));
  }

  function cancelEditing() {
    setEditingInventoryId(null);
    setQuantity("");
  }

  function saveQuantity(inventory) {
    const newQuantity = Number(quantity);

    if (!Number.isInteger(newQuantity) || newQuantity < 0) {
      toast.error(
        "Inventory quantity must be a whole number of zero or more.",
      );
      return;
    }

    if (newQuantity < inventory.reserved_quantity) {
      toast.error(
        `Quantity cannot be lower than the reserved quantity of ${inventory.reserved_quantity}.`,
      );
      return;
    }

    updateMutation.mutate({
      inventoryId: inventory.id,
      newQuantity,
    });
  }

  const totalAvailable = inventoryItems.reduce(
    (total, inventory) =>
      total + Number(inventory.available_quantity || 0),
    0,
  );

  const visibleLowStock = inventoryItems.filter(
    (inventory) => {
      const available = Number(
        inventory.available_quantity || 0,
      );

      return available > 0 && available <= 5;
    },
  ).length;

  const visibleOutOfStock = inventoryItems.filter(
    (inventory) =>
      Number(inventory.available_quantity || 0) <= 0,
  ).length;

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
          Catalog management
        </p>

        <h1 className="mt-2 text-3xl font-bold tracking-tight text-neutral-950">
          Inventory
        </h1>

        <p className="mt-2 text-sm text-neutral-500">
          Monitor available stock, reserved units, and product
          quantities.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <article className="rounded-2xl border border-neutral-200 bg-white p-5">
          <p className="text-sm font-semibold text-neutral-500">
            Available units
          </p>

          <p className="mt-3 text-3xl font-bold text-neutral-950">
            {totalAvailable}
          </p>

          <p className="mt-1 text-xs text-neutral-500">
            On the current page
          </p>
        </article>

        <article className="rounded-2xl border border-neutral-200 bg-white p-5">
          <p className="text-sm font-semibold text-neutral-500">
            Low-stock variants
          </p>

          <p className="mt-3 text-3xl font-bold text-amber-700">
            {visibleLowStock}
          </p>

          <p className="mt-1 text-xs text-neutral-500">
            Five or fewer available units
          </p>
        </article>

        <article className="rounded-2xl border border-neutral-200 bg-white p-5">
          <p className="text-sm font-semibold text-neutral-500">
            Out-of-stock variants
          </p>

          <p className="mt-3 text-3xl font-bold text-red-700">
            {visibleOutOfStock}
          </p>

          <p className="mt-1 text-xs text-neutral-500">
            No available units
          </p>
        </article>
      </section>

      <section className="rounded-2xl border border-neutral-200 bg-white p-4">
        <div className="grid gap-3 lg:grid-cols-[minmax(260px,1fr)_200px_220px]">
          <form
            onSubmit={handleSearch}
            className="relative"
          >
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-neutral-500"
            />

            <input
              type="search"
              value={searchInput}
              onChange={(event) =>
                setSearchInput(event.target.value)
              }
              placeholder="Search product, variant or SKU"
              className="min-h-11 w-full rounded-xl border border-neutral-300 pl-11 pr-4 text-sm outline-none focus:border-black"
            />
          </form>

          <select
            value={stockStatus}
            onChange={(event) => {
              setStockStatus(event.target.value);
              setPage(1);
            }}
            className="min-h-11 rounded-xl border border-neutral-300 bg-white px-3 text-sm outline-none focus:border-black"
          >
            <option value="">All stock levels</option>
            <option value="in_stock">In stock</option>
            <option value="low_stock">Low stock</option>
            <option value="out_of_stock">Out of stock</option>
          </select>

          <select
            value={ordering}
            onChange={(event) => {
              setOrdering(event.target.value);
              setPage(1);
            }}
            className="min-h-11 rounded-xl border border-neutral-300 bg-white px-3 text-sm outline-none focus:border-black"
          >
            <option value="variant__product__name">
              Product name
            </option>

            <option value="quantity">
              Lowest quantity
            </option>

            <option value="-quantity">
              Highest quantity
            </option>

            <option value="available_quantity_value">
              Lowest available
            </option>

            <option value="-available_quantity_value">
              Highest available
            </option>

            <option value="-updated_at">
              Recently updated
            </option>
          </select>
        </div>
      </section>

      <section className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
        {isPending ? (
          <p className="p-6 text-neutral-600">
            Loading inventory…
          </p>
        ) : isError ? (
          <p className="m-5 rounded-xl bg-red-50 p-4 text-red-700">
            {getApiError(
              error,
              "Unable to load inventory.",
            )}
          </p>
        ) : inventoryItems.length === 0 ? (
          <div className="p-8 text-center">
            <p className="font-semibold text-neutral-800">
              No inventory records found
            </p>

            <p className="mt-1 text-sm text-neutral-500">
              Change your search or stock filter.
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
                    SKU
                  </th>

                  <th className="px-5 py-4 text-center text-xs font-bold uppercase tracking-wide text-neutral-500">
                    Total
                  </th>

                  <th className="px-5 py-4 text-center text-xs font-bold uppercase tracking-wide text-neutral-500">
                    Reserved
                  </th>

                  <th className="px-5 py-4 text-center text-xs font-bold uppercase tracking-wide text-neutral-500">
                    Available
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
                {inventoryItems.map((inventory) => {
                  const stock = getStockDetails(
                    inventory.available_quantity,
                  );

                  const isEditing =
                    editingInventoryId === inventory.id;

                  return (
                    <tr
                      key={inventory.id}
                      className="hover:bg-neutral-50"
                    >
                      <td className="px-5 py-4">
                        <div className="min-w-52">
                          <p className="font-bold text-neutral-950">
                            {inventory.product_name}
                          </p>

                          <p className="mt-1 text-sm text-neutral-500">
                            {inventory.variant_name}
                          </p>

                          <p className="mt-1 text-xs text-neutral-400">
                            Updated{" "}
                            {formatDateTime(
                              inventory.updated_at,
                            )}
                          </p>
                        </div>
                      </td>

                      <td className="px-5 py-4 text-sm font-semibold text-neutral-700">
                        {inventory.sku}
                      </td>

                      <td className="px-5 py-4 text-center">
                        {isEditing ? (
                          <input
                            type="number"
                            min={inventory.reserved_quantity}
                            step="1"
                            value={quantity}
                            onChange={(event) =>
                              setQuantity(
                                event.target.value,
                              )
                            }
                            aria-label={`Quantity for ${inventory.product_name}`}
                            className="min-h-10 w-24 rounded-lg border border-neutral-300 px-3 text-center text-sm font-semibold outline-none focus:border-black"
                          />
                        ) : (
                          <span className="font-bold text-neutral-950">
                            {inventory.quantity}
                          </span>
                        )}
                      </td>

                      <td className="px-5 py-4 text-center text-sm text-neutral-700">
                        {inventory.reserved_quantity}
                      </td>

                      <td className="px-5 py-4 text-center">
                        <span
                          className={`font-bold ${
                            Number(
                              inventory.available_quantity,
                            ) <= 0
                              ? "text-red-700"
                              : Number(
                                    inventory.available_quantity,
                                  ) <= 5
                                ? "text-amber-700"
                                : "text-green-700"
                          }`}
                        >
                          {inventory.available_quantity}
                        </span>
                      </td>

                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-bold ${stock.classes}`}
                        >
                          {stock.label !== "In stock" && (
                            <AlertTriangle className="size-3" />
                          )}

                          {stock.label}
                        </span>
                      </td>

                      <td className="px-5 py-4">
                        <div className="flex justify-end gap-2">
                          {isEditing ? (
                            <>
                              <button
                                type="button"
                                disabled={
                                  updateMutation.isPending
                                }
                                onClick={() =>
                                  saveQuantity(inventory)
                                }
                                aria-label="Save inventory quantity"
                                className="flex size-9 items-center justify-center rounded-lg bg-black text-white hover:bg-neutral-800 disabled:opacity-60"
                              >
                                <Check className="size-4" />
                              </button>

                              <button
                                type="button"
                                disabled={
                                  updateMutation.isPending
                                }
                                onClick={cancelEditing}
                                aria-label="Cancel inventory editing"
                                className="flex size-9 items-center justify-center rounded-lg border border-neutral-300 text-neutral-700 hover:bg-neutral-100"
                              >
                                <X className="size-4" />
                              </button>
                            </>
                          ) : (
                            <button
                              type="button"
                              onClick={() =>
                                beginEditing(inventory)
                              }
                              className="inline-flex items-center gap-1 rounded-lg border border-neutral-300 px-3 py-2 text-xs font-bold text-neutral-700 hover:bg-neutral-100"
                            >
                              <Pencil className="size-3.5" />
                              Update stock
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {!isPending && !isError && data && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-neutral-200 px-5 py-4">
            <p className="text-sm text-neutral-500">
              {data.count ?? inventoryItems.length} inventory
              records
            </p>

            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={!data.previous}
                onClick={() =>
                  setPage((current) =>
                    Math.max(1, current - 1),
                  )
                }
                className="rounded-lg border border-neutral-300 px-3 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40"
              >
                Previous
              </button>

              <span className="flex min-w-10 items-center justify-center text-sm font-semibold">
                {page}
              </span>

              <button
                type="button"
                disabled={!data.next}
                onClick={() =>
                  setPage((current) => current + 1)
                }
                className="rounded-lg border border-neutral-300 px-3 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

export default StaffInventoryPage;