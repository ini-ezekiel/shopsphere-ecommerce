import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ImagePlus, Star, Trash2, X } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import {
  createStaffProductImage,
  deleteStaffProductImage,
  getStaffProductImages,
  updateStaffProductImage,
} from "../../api/staff";
import { getApiError } from "../../lib/errors";

function getResults(data) {
  return Array.isArray(data) ? data : data?.results || [];
}

function StaffProductImageManager({ product, onClose }) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef(null);

  const [imageFile, setImageFile] = useState(null);
  const [altText, setAltText] = useState("");
  const [position, setPosition] = useState("0");
  const [isPrimary, setIsPrimary] = useState(false);

  const { data, isPending, isError, error } = useQuery({
    queryKey: ["staff-product-images", product.id],
    queryFn: () => getStaffProductImages(product.id),
  });

  function refreshImages() {
    queryClient.invalidateQueries({
      queryKey: ["staff-product-images", product.id],
    });

    queryClient.invalidateQueries({
      queryKey: ["staff-products"],
    });

    queryClient.invalidateQueries({
      queryKey: ["products"],
    });
  }

  const uploadMutation = useMutation({
    mutationFn: (formData) => createStaffProductImage(product.id, formData),

    onSuccess: () => {
      refreshImages();

      setImageFile(null);
      setAltText("");
      setPosition("0");
      setIsPrimary(false);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      toast.success("Product image uploaded.");
    },

    onError: (mutationError) => {
      toast.error(
        getApiError(mutationError, "Unable to upload product image."),
      );
    },
  });

  const primaryMutation = useMutation({
    mutationFn: (imageId) => {
      const formData = new FormData();
      formData.append("is_primary", "true");

      return updateStaffProductImage(imageId, formData);
    },

    onSuccess: () => {
      refreshImages();
      toast.success("Primary image updated.");
    },

    onError: (mutationError) => {
      toast.error(
        getApiError(mutationError, "Unable to update the primary image."),
      );
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteStaffProductImage,

    onSuccess: () => {
      refreshImages();
      toast.success("Product image deleted.");
    },

    onError: (mutationError) => {
      toast.error(
        getApiError(mutationError, "Unable to delete product image."),
      );
    },
  });

  const images = getResults(data);

  function handleFileChange(event) {
    const file = event.target.files?.[0];

    if (!file) {
      setImageFile(null);
      return;
    }

    if (!file.type.startsWith("image/")) {
      toast.error("Select a valid image file.");
      event.target.value = "";
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      toast.error("The image cannot exceed 5MB.");
      event.target.value = "";
      return;
    }

    setImageFile(file);
  }

  function handleUpload(event) {
    event.preventDefault();

    if (!imageFile) {
      toast.error("Select an image to upload.");
      return;
    }

    const formData = new FormData();

    formData.append("image", imageFile);
    formData.append("alt_text", altText.trim());
    formData.append("position", String(Math.max(0, Number(position) || 0)));
    formData.append("is_primary", isPrimary ? "true" : "false");

    uploadMutation.mutate(formData);
  }

  function handleDelete(image) {
    const confirmed = window.confirm(`Delete this image from ${product.name}?`);

    if (confirmed) {
      deleteMutation.mutate(image.id);
    }
  }

  return (
    <div className="fixed inset-0 z-100 flex items-center justify-center bg-black/50 p-4">
      <section className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl bg-white shadow-2xl">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-neutral-200 bg-white px-5 py-4">
          <div>
            <h2 className="text-xl font-bold">Product images</h2>

            <p className="mt-1 text-sm text-neutral-500">{product.name}</p>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close image manager"
            className="flex size-10 items-center justify-center rounded-full hover:bg-neutral-100"
          >
            <X className="size-5" />
          </button>
        </header>

        <div className="p-5">
          <form
            onSubmit={handleUpload}
            className="grid gap-4 rounded-2xl bg-neutral-50 p-5 md:grid-cols-2"
          >
            <div className="md:col-span-2">
              <label
                htmlFor="product-image-file"
                className="text-sm font-semibold"
              >
                Image file
              </label>

              <input
                ref={fileInputRef}
                id="product-image-file"
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                required
                className="mt-2 block w-full rounded-xl border border-neutral-300 bg-white px-4 py-3 text-sm"
              />

              <p className="mt-1 text-xs text-neutral-500">
                Maximum file size: 5MB.
              </p>
            </div>

            <div>
              <label
                htmlFor="product-image-alt"
                className="text-sm font-semibold"
              >
                Alternative text
              </label>

              <input
                id="product-image-alt"
                value={altText}
                onChange={(event) => setAltText(event.target.value)}
                placeholder={`Image of ${product.name}`}
                className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-4 text-sm outline-none focus:border-black"
              />
            </div>

            <div>
              <label
                htmlFor="product-image-position"
                className="text-sm font-semibold"
              >
                Display position
              </label>

              <input
                id="product-image-position"
                type="number"
                min="0"
                step="1"
                value={position}
                onChange={(event) => setPosition(event.target.value)}
                className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-4 text-sm outline-none focus:border-black"
              />
            </div>

            <label className="flex items-center gap-3 text-sm font-semibold md:col-span-2">
              <input
                type="checkbox"
                checked={isPrimary}
                onChange={(event) => setIsPrimary(event.target.checked)}
                className="size-4 accent-black"
              />
              Use as the primary product image
            </label>

            <div className="md:col-span-2">
              <button
                type="submit"
                disabled={uploadMutation.isPending}
                className="inline-flex items-center gap-2 rounded-xl bg-black px-5 py-3 text-sm font-bold text-white disabled:opacity-60"
              >
                <ImagePlus className="size-4" />

                {uploadMutation.isPending ? "Uploading…" : "Upload image"}
              </button>
            </div>
          </form>

          <div className="mt-7">
            <h3 className="font-bold">Uploaded images</h3>

            {isPending ? (
              <p className="mt-4 text-sm text-neutral-500">Loading images…</p>
            ) : isError ? (
              <p className="mt-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">
                {getApiError(error, "Unable to load product images.")}
              </p>
            ) : images.length === 0 ? (
              <p className="mt-4 text-sm text-neutral-500">
                No images have been uploaded for this product.
              </p>
            ) : (
              <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {images.map((image) => (
                  <article
                    key={image.id}
                    className="overflow-hidden rounded-2xl border border-neutral-200"
                  >
                    <div className="aspect-4/3 bg-neutral-100 p-3">
                      <img
                        src={image.image}
                        alt={image.alt_text || product.name}
                        className="h-full w-full object-contain"
                      />
                    </div>

                    <div className="p-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-semibold">
                          Position {image.position}
                        </p>

                        {image.is_primary && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-1 text-xs font-bold text-amber-800">
                            <Star className="size-3 fill-current" />
                            Primary
                          </span>
                        )}
                      </div>

                      <p className="mt-2 line-clamp-2 text-xs text-neutral-500">
                        {image.alt_text || "No alternative text"}
                      </p>

                      <div className="mt-4 flex gap-2">
                        {!image.is_primary && (
                          <button
                            type="button"
                            disabled={primaryMutation.isPending}
                            onClick={() => primaryMutation.mutate(image.id)}
                            className="rounded-lg bg-neutral-100 px-3 py-2 text-xs font-bold hover:bg-neutral-200"
                          >
                            Make primary
                          </button>
                        )}

                        <button
                          type="button"
                          disabled={deleteMutation.isPending}
                          onClick={() => handleDelete(image)}
                          aria-label="Delete product image"
                          className="flex size-9 items-center justify-center rounded-lg bg-red-50 text-red-700 hover:bg-red-100"
                        >
                          <Trash2 className="size-4" />
                        </button>
                      </div>
                    </div>
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

export default StaffProductImageManager;
