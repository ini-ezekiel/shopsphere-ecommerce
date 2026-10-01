import { useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";

import { changePassword, setGooglePassword } from "../../api/auth";
import GoogleAuthButton from "../../components/auth/GoogleAuthButton";
import { useAuth } from "../../features/auth/AuthContext";
import { getApiError } from "../../lib/errors";

function SecurityPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSigningOut, setIsSigningOut] = useState(false);
  const [googlePassword, setGooglePasswordValue] = useState("");
  const [googlePasswordConfirmation, setGooglePasswordConfirmation] =
    useState("");

  const isGoogleOnlyAccount =
    user?.google_linked === true && user?.has_password === false;

  async function finishSecurityUpdate(message) {
    await logout().catch(() => undefined);

    toast.success(message);
    navigate("/login", { replace: true });
  }

  async function handlePasswordChange(event) {
    event.preventDefault();
    setIsSubmitting(true);

    const formData = new FormData(event.currentTarget);

    try {
      await changePassword({
        old_password: String(formData.get("old_password") || ""),
        new_password: String(formData.get("new_password") || ""),
        new_password2: String(formData.get("new_password2") || ""),
      });

      await finishSecurityUpdate("Password changed. Sign in again.");
    } catch (error) {
      toast.error(getApiError(error, "Unable to change your password."));

      setIsSubmitting(false);
    }
  }

  async function handleGoogleCredential(credential) {
    if (!googlePassword || !googlePasswordConfirmation) {
      toast.error("Enter and confirm your new password first.");
      return;
    }

    if (googlePassword !== googlePasswordConfirmation) {
      toast.error("The passwords do not match.");
      return;
    }

    setIsSubmitting(true);

    try {
      await setGooglePassword({
        credential,
        password: googlePassword,
        password2: googlePasswordConfirmation,
      });

      await finishSecurityUpdate(
        "Password created. You can now sign in with Google or your password.",
      );
    } catch (error) {
      toast.error(getApiError(error, "Unable to create your password."));

      setIsSubmitting(false);
    }
  }

  async function handleSignOut() {
    setIsSigningOut(true);

    await logout().catch(() => undefined);

    toast.success("You have been signed out.");
    navigate("/", { replace: true });
  }

  return (
    <div className="max-w-xl">
      <h2 className="text-2xl font-bold">Account security</h2>

      {isGoogleOnlyAccount ? (
        <section className="mt-6 space-y-5 rounded-2xl border border-neutral-200 p-6">
          <div>
            <h3 className="text-lg font-bold text-neutral-950">
              Create a password
            </h3>

            <p className="mt-2 text-sm leading-6 text-neutral-600">
              You registered with Google and do not have a ShopShere password
              yet. Enter a new password, then verify with the same Google
              account.
            </p>
          </div>

          <label className="form-label">
            New password
            <input
              type="password"
              value={googlePassword}
              onChange={(event) => setGooglePasswordValue(event.target.value)}
              autoComplete="new-password"
              required
              className="field"
            />
          </label>

          <label className="form-label">
            Confirm new password
            <input
              type="password"
              value={googlePasswordConfirmation}
              onChange={(event) =>
                setGooglePasswordConfirmation(event.target.value)
              }
              autoComplete="new-password"
              required
              className="field"
            />
          </label>

          <div>
            <p className="mb-3 text-sm font-semibold text-neutral-800">
              Verify your Google account to create the password
            </p>

            <GoogleAuthButton
              onCredential={handleGoogleCredential}
              disabled={isSubmitting}
            />
          </div>
        </section>
      ) : (
        <form
          onSubmit={handlePasswordChange}
          className="mt-6 space-y-5 rounded-2xl border border-neutral-200 p-6"
        >
          <label className="form-label">
            Current password
            <input
              name="old_password"
              type="password"
              autoComplete="current-password"
              required
              className="field"
            />
          </label>

          <label className="form-label">
            New password
            <input
              name="new_password"
              type="password"
              autoComplete="new-password"
              required
              className="field"
            />
          </label>

          <label className="form-label">
            Confirm new password
            <input
              name="new_password2"
              type="password"
              autoComplete="new-password"
              required
              className="field"
            />
          </label>

          <button disabled={isSubmitting} className="button-primary">
            {isSubmitting ? "Updating…" : "Change password"}
          </button>
        </form>
      )}

      <section className="mt-6 rounded-2xl border border-neutral-200 p-6">
        <h3 className="text-lg font-bold text-neutral-950">Sign out</h3>

        <p className="mt-2 text-sm leading-6 text-neutral-600">
          Sign out of your account on this device.
        </p>

        <button
          type="button"
          onClick={handleSignOut}
          disabled={isSigningOut}
          className="button-secondary mt-5"
        >
          {isSigningOut ? "Signing out…" : "Sign out"}
        </button>
      </section>
    </div>
  );
}

export default SecurityPage;
