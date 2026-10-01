import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import { toast } from "sonner";

import GoogleAuthButton from "../../components/auth/GoogleAuthButton";
import AuthShell from "../../components/ui/AuthShell";
import { useAuth } from "../../features/auth/AuthContext";
import { getApiError } from "../../lib/errors";

function LoginPage() {
  const { authenticateWithGoogle, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGoogleSubmitting, setIsGoogleSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage("");

    const formData = new FormData(event.currentTarget);

    try {
      await login({
        email: String(formData.get("email") || "")
          .trim()
          .toLowerCase(),
        password: String(formData.get("password") || ""),
      });
      toast.success("Welcome back.");
      navigate(location.state?.from?.pathname || "/account", { replace: true });
    } catch (error) {
      setErrorMessage(getApiError(error, "Unable to sign in."));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleGoogleCredential(credential) {
    setIsGoogleSubmitting(true);
    setErrorMessage("");

    try {
      const result = await authenticateWithGoogle(credential);
      toast.success(
        result.is_new_user ? "Your account is ready." : "Welcome back.",
      );
      navigate(location.state?.from?.pathname || "/account", { replace: true });
    } catch (error) {
      setErrorMessage(getApiError(error, "Unable to continue with Google."));
    } finally {
      setIsGoogleSubmitting(false);
    }
  }

  return (
    <AuthShell
      eyebrow="Welcome back"
      title="Sign in to your account"
      footer={
        <>
          New to ShopShere?{" "}
          <Link
            to="/register"
            className="font-semibold text-neutral-950 hover:underline"
          >
            Create an account
          </Link>
        </>
      }
    >
      <GoogleAuthButton
        onCredential={handleGoogleCredential}
        disabled={isGoogleSubmitting || isSubmitting}
      />

      <div className="my-6 flex items-center gap-3" aria-hidden="true">
        <span className="h-px flex-1 bg-neutral-200" />
        <span className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
          Or continue with email
        </span>
        <span className="h-px flex-1 bg-neutral-200" />
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {errorMessage && (
          <p
            role="alert"
            className="rounded-xl bg-red-50 p-3 text-sm text-red-700"
          >
            {errorMessage}
          </p>
        )}

        <label className="block text-sm font-semibold text-neutral-800">
          Email address
          <input
            name="email"
            type="email"
            autoComplete="email"
            required
            className="field"
          />
        </label>

        <label className="block text-sm font-semibold text-neutral-800">
          Password
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
            className="field"
          />
        </label>

        <div className="text-right">
          <Link
            to="/forgot-password"
            className="text-sm font-semibold text-neutral-700 hover:text-black hover:underline"
          >
            Forgot password?
          </Link>
        </div>

        <button
          type="submit"
          disabled={isSubmitting || isGoogleSubmitting}
          className="button-primary w-full"
        >
          {isSubmitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </AuthShell>
  );
}

export default LoginPage;
