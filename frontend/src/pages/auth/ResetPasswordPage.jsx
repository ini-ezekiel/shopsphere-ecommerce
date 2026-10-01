import { useState } from "react";
import { Link, useSearchParams } from "react-router";

import { confirmPasswordReset } from "../../api/auth";
import AuthShell from "../../components/ui/AuthShell";
import { getApiError } from "../../lib/errors";

function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const [message, setMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const uid = searchParams.get("uid") || "";
  const token = searchParams.get("token") || "";

  async function handleSubmit(event) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage("");
    const formData = new FormData(event.currentTarget);

    try {
      const result = await confirmPasswordReset({
        uid,
        token,
        new_password: String(formData.get("new_password") || ""),
        new_password2: String(formData.get("new_password2") || ""),
      });
      setMessage(result.detail);
    } catch (error) {
      setErrorMessage(getApiError(error, "The reset link is invalid or expired."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthShell eyebrow="Account recovery" title="Choose a new password">
      {!uid || !token ? (
        <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">This reset link is incomplete.</p>
      ) : message ? (
        <div className="space-y-5 text-center">
          <p className="rounded-xl bg-green-50 p-4 text-sm text-green-800">{message}</p>
          <Link to="/login" className="button-primary w-full">Sign in</Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-5">
          {errorMessage && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{errorMessage}</p>}
          <label className="block text-sm font-semibold text-neutral-800">
            New password
            <input name="new_password" type="password" autoComplete="new-password" required className="field" />
          </label>
          <label className="block text-sm font-semibold text-neutral-800">
            Confirm new password
            <input name="new_password2" type="password" autoComplete="new-password" required className="field" />
          </label>
          <button disabled={isSubmitting} className="button-primary w-full">
            {isSubmitting ? "Saving…" : "Save new password"}
          </button>
        </form>
      )}
    </AuthShell>
  );
}

export default ResetPasswordPage;
