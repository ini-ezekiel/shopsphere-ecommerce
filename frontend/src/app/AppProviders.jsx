import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router";
import { Toaster } from "sonner";

import { AuthProvider } from "../features/auth/AuthContext";
import { NotificationProvider } from "../features/notifications/NotificationContext";
import { WishlistProvider } from "../features/wishlist/WishlistContext";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});

function AppProviders({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <WishlistProvider>
            <NotificationProvider>
              {children}

              <Toaster position="top-right" richColors closeButton />
            </NotificationProvider>
          </WishlistProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default AppProviders;
