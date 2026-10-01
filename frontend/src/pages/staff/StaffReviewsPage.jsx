import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  Eye,
  EyeOff,
  Search,
  ShieldCheck,
  Star,
  X,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { toast } from "sonner";

import {
  getStaffReviews,
  updateStaffReview,
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

function RatingStars({ rating }) {
  return (
    <div
      className="flex items-center gap-0.5"
      aria-label={`${rating} out of 5 stars`}
    >
      {Array.from({ length: 5 }, (_, index) => {
        const filled = index < Number(rating);

        return (
          <Star
            key={index}
            aria-hidden="true"
            className={`size-4 ${
              filled
                ? "fill-amber-400 text-amber-400"
                : "text-neutral-300"
            }`}
          />
        );
      })}
    </div>
  );
}

function StaffReviewsPage() {
  const queryClient = useQueryClient();

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [visibility, setVisibility] = useState("");
  const [rating, setRating] = useState("");
  const [ordering, setOrdering] = useState("-created_at");
  const [page, setPage] = useState(1);
  const [selectedReview, setSelectedReview] = useState(null);

  const params = {
    page,
    ordering,
  };

  if (search) {
    params.search = search;
  }

  if (visibility) {
    params.is_visible = visibility;
  }

  if (rating) {
    params.rating = rating;
  }

  const {
    data,
    isPending,
    isError,
    error,
  } = useQuery({
    queryKey: [
      "staff-reviews",
      search,
      visibility,
      rating,
      ordering,
      page,
    ],
    queryFn: () => getStaffReviews(params),
  });

  const moderationMutation = useMutation({
    mutationFn: ({ reviewId, isVisible }) =>
      updateStaffReview(reviewId, {
        is_visible: isVisible,
      }),

    onSuccess: (updatedReview) => {
      queryClient.invalidateQueries({
        queryKey: ["staff-reviews"],
      });

      queryClient.invalidateQueries({
        queryKey: ["staff-products"],
      });

      queryClient.invalidateQueries({
        queryKey: ["products"],
      });

      if (selectedReview?.id === updatedReview.id) {
        setSelectedReview(updatedReview);
      }

      toast.success(
        updatedReview.is_visible
          ? "Review is now visible."
          : "Review has been hidden.",
      );
    },

    onError: (mutationError) => {
      toast.error(
        getApiError(
          mutationError,
          "Unable to update this review.",
        ),
      );
    },
  });

  const reviews = getResults(data);

  const visibleCount = reviews.filter(
    (review) => review.is_visible,
  ).length;

  const hiddenCount = reviews.filter(
    (review) => !review.is_visible,
  ).length;

  const averageRating = reviews.length
    ? (
        reviews.reduce(
          (total, review) =>
            total + Number(review.rating || 0),
          0,
        ) / reviews.length
      ).toFixed(1)
    : "0.0";

  function handleSearch(event) {
    event.preventDefault();
    setSearch(searchInput.trim());
    setPage(1);
  }

  function moderateReview(review) {
    moderationMutation.mutate({
      reviewId: review.id,
      isVisible: !review.is_visible,
    });
  }

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
          Customer content
        </p>

        <h1 className="mt-2 text-3xl font-bold tracking-tight text-neutral-950">
          Reviews
        </h1>

        <p className="mt-2 text-sm text-neutral-500">
          Review customer feedback and control what appears on
          product pages.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <article className="rounded-2xl border border-neutral-200 bg-white p-5">
          <p className="text-sm font-semibold text-neutral-500">
            Visible reviews
          </p>

          <p className="mt-3 text-3xl font-bold text-green-700">
            {visibleCount}
          </p>

          <p className="mt-1 text-xs text-neutral-500">
            On the current page
          </p>
        </article>

        <article className="rounded-2xl border border-neutral-200 bg-white p-5">
          <p className="text-sm font-semibold text-neutral-500">
            Hidden reviews
          </p>

          <p className="mt-3 text-3xl font-bold text-red-700">
            {hiddenCount}
          </p>

          <p className="mt-1 text-xs text-neutral-500">
            On the current page
          </p>
        </article>

        <article className="rounded-2xl border border-neutral-200 bg-white p-5">
          <p className="text-sm font-semibold text-neutral-500">
            Average rating
          </p>

          <div className="mt-3 flex items-center gap-2">
            <p className="text-3xl font-bold text-neutral-950">
              {averageRating}
            </p>

            <Star className="size-6 fill-amber-400 text-amber-400" />
          </div>

          <p className="mt-1 text-xs text-neutral-500">
            On the current page
          </p>
        </article>
      </section>

      <section className="rounded-2xl border border-neutral-200 bg-white p-4">
        <div className="grid gap-3 lg:grid-cols-[minmax(260px,1fr)_180px_160px_190px]">
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
              placeholder="Search reviewer, product or comment"
              className="min-h-11 w-full rounded-xl border border-neutral-300 pl-11 pr-4 text-sm outline-none focus:border-black"
            />
          </form>

          <select
            value={visibility}
            onChange={(event) => {
              setVisibility(event.target.value);
              setPage(1);
            }}
            className="min-h-11 rounded-xl border border-neutral-300 bg-white px-3 text-sm outline-none focus:border-black"
          >
            <option value="">All visibility</option>
            <option value="true">Visible</option>
            <option value="false">Hidden</option>
          </select>

          <select
            value={rating}
            onChange={(event) => {
              setRating(event.target.value);
              setPage(1);
            }}
            className="min-h-11 rounded-xl border border-neutral-300 bg-white px-3 text-sm outline-none focus:border-black"
          >
            <option value="">All ratings</option>
            <option value="5">5 stars</option>
            <option value="4">4 stars</option>
            <option value="3">3 stars</option>
            <option value="2">2 stars</option>
            <option value="1">1 star</option>
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
            <option value="-rating">Highest rating</option>
            <option value="rating">Lowest rating</option>
            <option value="-updated_at">
              Recently updated
            </option>
          </select>
        </div>
      </section>

      <section className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
        {isPending ? (
          <p className="p-6 text-neutral-600">
            Loading reviews…
          </p>
        ) : isError ? (
          <p className="m-5 rounded-xl bg-red-50 p-4 text-red-700">
            {getApiError(
              error,
              "Unable to load reviews.",
            )}
          </p>
        ) : reviews.length === 0 ? (
          <div className="p-8 text-center">
            <p className="font-semibold text-neutral-800">
              No reviews found
            </p>

            <p className="mt-1 text-sm text-neutral-500">
              Change your search or filters.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-neutral-200">
            {reviews.map((review) => (
              <article
                key={review.id}
                className="p-5 hover:bg-neutral-50"
              >
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-3">
                      <RatingStars rating={review.rating} />

                      {review.verified_purchase && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-1 text-xs font-bold text-blue-800">
                          <ShieldCheck className="size-3.5" />
                          Verified purchase
                        </span>
                      )}

                      <span
                        className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${
                          review.is_visible
                            ? "bg-green-100 text-green-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {review.is_visible
                          ? "Visible"
                          : "Hidden"}
                      </span>
                    </div>

                    <h2 className="mt-3 font-bold text-neutral-950">
                      {review.title || "Untitled review"}
                    </h2>

                    <p className="mt-2 line-clamp-2 text-sm leading-6 text-neutral-600">
                      {review.comment}
                    </p>

                    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-neutral-500">
                      <span>
                        Product: {review.product_name}
                      </span>

                      <span>
                        Reviewer:{" "}
                        {review.reviewer_username ||
                          review.reviewer_email}
                      </span>

                      <span>
                        {formatDateTime(review.created_at)}
                      </span>
                    </div>
                  </div>

                  <div className="flex shrink-0 flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() =>
                        setSelectedReview(review)
                      }
                      className="inline-flex items-center gap-1 rounded-lg border border-neutral-300 px-3 py-2 text-xs font-bold text-neutral-700 hover:bg-neutral-100"
                    >
                      <Eye className="size-3.5" />
                      View
                    </button>

                    <button
                      type="button"
                      disabled={
                        moderationMutation.isPending
                      }
                      onClick={() =>
                        moderateReview(review)
                      }
                      className={`inline-flex items-center gap-1 rounded-lg px-3 py-2 text-xs font-bold disabled:cursor-not-allowed disabled:opacity-60 ${
                        review.is_visible
                          ? "bg-red-50 text-red-700 hover:bg-red-100"
                          : "bg-green-50 text-green-700 hover:bg-green-100"
                      }`}
                    >
                      {review.is_visible ? (
                        <>
                          <EyeOff className="size-3.5" />
                          Hide
                        </>
                      ) : (
                        <>
                          <Eye className="size-3.5" />
                          Show
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}

        {!isPending && !isError && data && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-neutral-200 px-5 py-4">
            <p className="text-sm text-neutral-500">
              {data.count ?? reviews.length} reviews
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

      {selectedReview && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="review-dialog-title"
          className="fixed inset-0 z-100 flex items-center justify-center bg-black/50 p-4"
        >
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-2xl">
            <div className="sticky top-0 flex items-center justify-between border-b border-neutral-200 bg-white px-5 py-4">
              <h2
                id="review-dialog-title"
                className="text-xl font-bold text-neutral-950"
              >
                Review details
              </h2>

              <button
                type="button"
                onClick={() => setSelectedReview(null)}
                aria-label="Close review details"
                className="flex size-10 items-center justify-center rounded-full hover:bg-neutral-100"
              >
                <X className="size-5" />
              </button>
            </div>

            <div className="space-y-6 p-5 sm:p-6">
              <div className="flex flex-wrap items-center gap-3">
                <RatingStars
                  rating={selectedReview.rating}
                />

                <span
                  className={`inline-flex rounded-full px-3 py-1 text-xs font-bold ${
                    selectedReview.is_visible
                      ? "bg-green-100 text-green-800"
                      : "bg-red-100 text-red-800"
                  }`}
                >
                  {selectedReview.is_visible
                    ? "Visible"
                    : "Hidden"}
                </span>

                {selectedReview.verified_purchase && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-3 py-1 text-xs font-bold text-blue-800">
                    <ShieldCheck className="size-3.5" />
                    Verified purchase
                  </span>
                )}
              </div>

              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-neutral-500">
                  Title
                </p>

                <p className="mt-2 font-bold text-neutral-950">
                  {selectedReview.title ||
                    "Untitled review"}
                </p>
              </div>

              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-neutral-500">
                  Comment
                </p>

                <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-neutral-700">
                  {selectedReview.comment}
                </p>
              </div>

              <div className="grid gap-4 rounded-xl bg-neutral-50 p-4 sm:grid-cols-2">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wide text-neutral-500">
                    Reviewer
                  </p>

                  <p className="mt-1 break-all text-sm font-semibold text-neutral-900">
                    {selectedReview.reviewer_username ||
                      "No username"}
                  </p>

                  <p className="mt-1 break-all text-sm text-neutral-600">
                    {selectedReview.reviewer_email}
                  </p>
                </div>

                <div>
                  <p className="text-xs font-bold uppercase tracking-wide text-neutral-500">
                    Product
                  </p>

                  <Link
                    to={`/products/${selectedReview.product_slug}`}
                    className="mt-1 inline-block text-sm font-semibold text-neutral-900 hover:underline"
                  >
                    {selectedReview.product_name}
                  </Link>
                </div>

                <div>
                  <p className="text-xs font-bold uppercase tracking-wide text-neutral-500">
                    Order
                  </p>

                  <Link
                    to={`/staff/orders/${selectedReview.order_number}`}
                    className="mt-1 inline-block break-all text-sm font-semibold text-neutral-900 hover:underline"
                  >
                    {selectedReview.order_number}
                  </Link>
                </div>

                <div>
                  <p className="text-xs font-bold uppercase tracking-wide text-neutral-500">
                    Submitted
                  </p>

                  <p className="mt-1 text-sm text-neutral-700">
                    {formatDateTime(
                      selectedReview.created_at,
                    )}
                  </p>
                </div>
              </div>

              <button
                type="button"
                disabled={moderationMutation.isPending}
                onClick={() =>
                  moderateReview(selectedReview)
                }
                className={`inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-60 ${
                  selectedReview.is_visible
                    ? "bg-red-700 text-white hover:bg-red-800"
                    : "bg-green-700 text-white hover:bg-green-800"
                }`}
              >
                {selectedReview.is_visible ? (
                  <>
                    <EyeOff className="size-4" />
                    Hide this review
                  </>
                ) : (
                  <>
                    <Eye className="size-4" />
                    Make review visible
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default StaffReviewsPage;