import { useState } from "react";

import { requestPasswordReset } from "../../api/auth";
import AuthShell from "../../components/ui/AuthShell";
import { getApiError } from "../../lib/errors";

function ForgotPasswordPage() {
  const [message, setMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage("");

    try {
      const email = String(new FormData(event.currentTarget).get("email") || "").trim();
      const result = await requestPasswordReset(email);
      setMessage(result.detail);
    } catch (error) {
      setErrorMessage(getApiError(error, "Unable to request a password reset."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthShell eyebrow="Account recovery" title="Reset your password" description="We’ll email a secure reset link if the account exists.">
      {message ? (
        <p className="rounded-xl bg-green-50 p-4 text-sm leading-6 text-green-800">{message}</p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-5">
          {errorMessage && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{errorMessage}</p>}
          <label className="block text-sm font-semibold text-neutral-800">
            Email address
            <input name="email" type="email" autoComplete="email" required className="field" />
          </label>
          <button disabled={isSubmitting} className="button-primary w-full">
            {isSubmitting ? "Sending…" : "Send reset link"}
          </button>
        </form>
      )}
    </AuthShell>
  );
}

export default ForgotPasswordPage;
