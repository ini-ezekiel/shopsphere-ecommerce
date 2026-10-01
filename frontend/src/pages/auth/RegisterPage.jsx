import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { toast } from "sonner";

import { startRegistration, verifyRegistration } from "../../api/auth";
import GoogleAuthButton from "../../components/auth/GoogleAuthButton";
import AuthShell from "../../components/ui/AuthShell";
import { useAuth } from "../../features/auth/AuthContext";
import { getApiError } from "../../lib/errors";

function RegisterPage() {
  const navigate = useNavigate();
  const { authenticateWithGoogle, finishRegistration } = useAuth();
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState("");
  const [registrationId, setRegistrationId] = useState("");
  const [registrationToken, setRegistrationToken] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGoogleSubmitting, setIsGoogleSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  async function submitEmail(event) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage("");
    const value = String(new FormData(event.currentTarget).get("email") || "")
      .trim()
      .toLowerCase();

    try {
      const result = await startRegistration(value);
      setEmail(value);
      setRegistrationId(result.registration_id);
      setStep(2);
    } catch (error) {
      setErrorMessage(getApiError(error, "Unable to start registration."));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function submitCode(event) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage("");

    try {
      const result = await verifyRegistration({
        registration_id: registrationId,
        otp: String(new FormData(event.currentTarget).get("otp") || "").trim(),
      });
      setRegistrationToken(result.registration_token);
      setStep(3);
    } catch (error) {
      setErrorMessage(getApiError(error, "That code is invalid or expired."));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function submitAccount(event) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage("");
    const formData = new FormData(event.currentTarget);

    try {
      await finishRegistration({
        registration_id: registrationId,
        registration_token: registrationToken,
        first_name: String(formData.get("first_name") || "").trim(),
        last_name: String(formData.get("last_name") || "").trim(),
        username: String(formData.get("username") || "")
          .trim()
          .toLowerCase(),
        password: String(formData.get("password") || ""),
        password2: String(formData.get("password2") || ""),
      });
      toast.success("Your account is ready.");
      navigate("/account", { replace: true });
    } catch (error) {
      setErrorMessage(getApiError(error, "Unable to complete registration."));
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
      navigate("/account", { replace: true });
    } catch (error) {
      setErrorMessage(getApiError(error, "Unable to continue with Google."));
    } finally {
      setIsGoogleSubmitting(false);
    }
  }

  const stepTitle = [
    "Create your account",
    "Verify your email",
    "Complete your profile",
  ][step - 1];

  return (
    <AuthShell
      eyebrow={`Step ${step} of 3`}
      title={stepTitle}
      description={
        step === 2 ? `Enter the six-digit code sent to ${email}.` : undefined
      }
      footer={
        <>
          Already registered?{" "}
          <Link
            to="/login"
            className="font-semibold text-neutral-950 hover:underline"
          >
            Sign in
          </Link>
        </>
      }
    >
      {errorMessage && (
        <p
          role="alert"
          className="mb-5 rounded-xl bg-red-50 p-3 text-sm text-red-700"
        >
          {errorMessage}
        </p>
      )}

      {step === 1 && (
        <>
          <GoogleAuthButton
            onCredential={handleGoogleCredential}
            text="signup_with"
            disabled={isGoogleSubmitting || isSubmitting}
          />

          <div className="my-6 flex items-center gap-3" aria-hidden="true">
            <span className="h-px flex-1 bg-neutral-200" />
            <span className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
              Or register with email
            </span>
            <span className="h-px flex-1 bg-neutral-200" />
          </div>

          <form onSubmit={submitEmail} className="space-y-5">
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
            <button
              disabled={isSubmitting || isGoogleSubmitting}
              className="button-primary w-full"
            >
              {isSubmitting ? "Sending code…" : "Continue"}
            </button>
          </form>
        </>
      )}

      {step === 2 && (
        <form onSubmit={submitCode} className="space-y-5">
          <label className="block text-sm font-semibold text-neutral-800">
            Verification code
            <input
              name="otp"
              inputMode="numeric"
              pattern="[0-9]{6}"
              maxLength="6"
              autoComplete="one-time-code"
              required
              className="field text-center text-xl tracking-[0.35em]"
            />
          </label>
          <button disabled={isSubmitting} className="button-primary w-full">
            {isSubmitting ? "Verifying…" : "Verify email"}
          </button>
        </form>
      )}

      {step === 3 && (
        <form onSubmit={submitAccount} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm font-semibold text-neutral-800">
              First name
              <input
                name="first_name"
                autoComplete="given-name"
                required
                className="field"
              />
            </label>
            <label className="block text-sm font-semibold text-neutral-800">
              Last name
              <input
                name="last_name"
                autoComplete="family-name"
                required
                className="field"
              />
            </label>
          </div>
          <label className="block text-sm font-semibold text-neutral-800">
            Username
            <input
              name="username"
              pattern="[a-z0-9_]{3,30}"
              required
              className="field"
            />
          </label>
          <label className="block text-sm font-semibold text-neutral-800">
            Password
            <input
              name="password"
              type="password"
              autoComplete="new-password"
              required
              className="field"
            />
          </label>
          <label className="block text-sm font-semibold text-neutral-800">
            Confirm password
            <input
              name="password2"
              type="password"
              autoComplete="new-password"
              required
              className="field"
            />
          </label>
          <button disabled={isSubmitting} className="button-primary w-full">
            {isSubmitting ? "Creating account…" : "Create account"}
          </button>
        </form>
      )}
    </AuthShell>
  );
}

export default RegisterPage;
