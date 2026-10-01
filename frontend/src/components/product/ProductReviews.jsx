import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Star } from "lucide-react";
import { toast } from "sonner";

import { createProductReview, getProductReviews } from "../../api/reviews";
import { useAuth } from "../../features/auth/AuthContext";
import { getApiError } from "../../lib/errors";
import { formatDate } from "../../lib/format";

function Stars({ rating }) {
  return (
    <span className="flex gap-0.5" aria-label={`${rating} out of 5 stars`}>
      {[1, 2, 3, 4, 5].map((value) => (
        <Star key={value} className={`size-4 ${value <= rating ? "fill-black text-black" : "text-neutral-300"}`} aria-hidden="true" />
      ))}
    </span>
  );
}

function ProductReviews({ productSlug, reviewCount }) {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const { data, isPending } = useQuery({
    queryKey: ["reviews", productSlug],
    queryFn: () => getProductReviews(productSlug),
  });
  const reviews = Array.isArray(data) ? data : (data?.results ?? []);

  const mutation = useMutation({
    mutationFn: (payload) => createProductReview(productSlug, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews", productSlug] });
      queryClient.invalidateQueries({ queryKey: ["product", productSlug] });
      toast.success("Review submitted.");
    },
    onError: (error) => toast.error(getApiError(error, "Unable to submit your review.")),
  });

  function handleSubmit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    mutation.mutate({
        rating: Number(formData.get("rating")),
        title: String(formData.get("title") || "").trim(),
        comment: String(formData.get("comment") || "").trim(),
      }, { onSuccess: () => form.reset() });
  }

  return (
    <section className="mt-16 border-t border-neutral-200 pt-12">
      <div className="grid gap-10 lg:grid-cols-[300px_1fr]">
        <div>
          <p className="eyebrow">Customer feedback</p>
          <h2 className="mt-2 text-3xl font-bold">Reviews ({reviewCount})</h2>
          {isAuthenticated && (
            <form onSubmit={handleSubmit} className="mt-7 space-y-4 rounded-2xl bg-neutral-100 p-5">
              <h3 className="font-bold">Write a review</h3>
              <label className="form-label">Rating<select name="rating" required className="field"><option value="">Select</option>{[5, 4, 3, 2, 1].map((value) => <option key={value} value={value}>{value} stars</option>)}</select></label>
              <label className="form-label">Title<input name="title" maxLength="120" className="field" /></label>
              <label className="form-label">Comment<textarea name="comment" rows="4" required className="field resize-y" /></label>
              <button disabled={mutation.isPending} className="button-primary w-full">{mutation.isPending ? "Submitting…" : "Submit review"}</button>
              <p className="text-xs leading-5 text-neutral-500">Only customers with a delivered order can review this product.</p>
            </form>
          )}
        </div>
        <div className="divide-y divide-neutral-200">
          {isPending && <p className="py-6 text-neutral-600">Loading reviews…</p>}
          {!isPending && reviews.length === 0 && <p className="py-6 text-neutral-600">No reviews yet.</p>}
          {reviews.map((review) => (
            <article key={review.id} className="py-6 first:pt-0">
              <div className="flex flex-wrap items-center justify-between gap-3"><Stars rating={review.rating} /><time className="text-sm text-neutral-500">{formatDate(review.created_at)}</time></div>
              {review.title && <h3 className="mt-3 font-bold">{review.title}</h3>}
              <p className="mt-2 leading-7 text-neutral-600">{review.comment}</p>
              <p className="mt-3 text-sm font-semibold">{review.reviewer_username} <span className="font-normal text-neutral-500">· Verified purchase</span></p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

export default ProductReviews;
