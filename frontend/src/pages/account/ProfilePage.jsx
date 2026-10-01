import { useState } from "react";
import { toast } from "sonner";

import { updateProfile } from "../../api/auth";
import { useAuth } from "../../features/auth/AuthContext";
import { getApiError } from "../../lib/errors";

function ProfilePage() {
  const { user, refreshProfile } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setIsSubmitting(true);
    const formData = new FormData(event.currentTarget);

    try {
      await updateProfile({
        first_name: String(formData.get("first_name") || "").trim(),
        last_name: String(formData.get("last_name") || "").trim(),
      });
      await refreshProfile();
      toast.success("Profile updated.");
    } catch (error) {
      toast.error(getApiError(error, "Unable to update your profile."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="max-w-xl">
      <h2 className="text-2xl font-bold">Profile details</h2>
      <form onSubmit={handleSubmit} className="mt-6 space-y-5 rounded-2xl border border-neutral-200 p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="form-label">First name<input name="first_name" defaultValue={user?.first_name} required className="field" /></label>
          <label className="form-label">Last name<input name="last_name" defaultValue={user?.last_name} required className="field" /></label>
        </div>
        <label className="form-label">Username<input value={user?.username || ""} disabled className="field bg-neutral-100 text-neutral-500" /></label>
        <label className="form-label">Email address<input value={user?.email || ""} disabled className="field bg-neutral-100 text-neutral-500" /></label>
        <button disabled={isSubmitting} className="button-primary">{isSubmitting ? "Saving…" : "Save changes"}</button>
      </form>
    </div>
  );
}

export default ProfilePage;
