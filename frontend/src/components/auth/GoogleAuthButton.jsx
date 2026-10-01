import { useEffect, useRef, useState } from "react";

const GOOGLE_SCRIPT_ID = "google-identity-services";
const GOOGLE_SCRIPT_URL = "https://accounts.google.com/gsi/client";

function loadGoogleIdentityServices() {
  if (window.google?.accounts?.id) {
    return Promise.resolve();
  }

  return new Promise((resolve, reject) => {
    const existingScript = document.getElementById(GOOGLE_SCRIPT_ID);

    if (existingScript) {
      existingScript.addEventListener("load", resolve, { once: true });
      existingScript.addEventListener(
        "error",
        () => reject(new Error("Google authentication could not be loaded.")),
        { once: true },
      );
      return;
    }

    const script = document.createElement("script");
    script.id = GOOGLE_SCRIPT_ID;
    script.src = GOOGLE_SCRIPT_URL;
    script.async = true;
    script.defer = true;
    script.onload = resolve;
    script.onerror = () => {
      reject(new Error("Google authentication could not be loaded."));
    };
    document.head.appendChild(script);
  });
}

function GoogleAuthButton({
  onCredential,
  text = "continue_with",
  disabled = false,
}) {
  const buttonContainerRef = useRef(null);
  const credentialHandlerRef = useRef(onCredential);
  const [loadError, setLoadError] = useState("");
  const clientId = import.meta.env.VITE_GOOGLE_OAUTH_CLIENT_ID;

  useEffect(() => {
    credentialHandlerRef.current = onCredential;
  }, [onCredential]);

  useEffect(() => {
    let active = true;

    async function renderGoogleButton() {
      if (!clientId) {
        setLoadError("Google sign-in is not configured.");
        return;
      }

      try {
        await loadGoogleIdentityServices();

        if (!active || !buttonContainerRef.current) {
          return;
        }

        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (response) => {
            if (response.credential) {
              credentialHandlerRef.current(response.credential);
            }
          },
          ux_mode: "popup",
        });

        buttonContainerRef.current.replaceChildren();
        window.google.accounts.id.renderButton(buttonContainerRef.current, {
          type: "standard",
          theme: "outline",
          size: "large",
          text,
          shape: "pill",
          logo_alignment: "left",
          width: Math.min(buttonContainerRef.current.clientWidth, 400),
        });
      } catch {
        if (active) {
          setLoadError("Google sign-in is temporarily unavailable.");
        }
      }
    }

    renderGoogleButton();

    return () => {
      active = false;
    };
  }, [clientId, text]);

  if (loadError) {
    return <p className="text-center text-sm text-neutral-500">{loadError}</p>;
  }

  return (
    <div
      className={disabled ? "pointer-events-none opacity-60" : ""}
      aria-busy={disabled}
    >
      <div
        ref={buttonContainerRef}
        className="flex min-h-11 w-full justify-center"
      />
    </div>
  );
}

export default GoogleAuthButton;
