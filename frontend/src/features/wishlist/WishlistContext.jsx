/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  addToWishlist,
  getWishlist,
  removeFromWishlist,
} from "../../api/wishlist";
import { useAuth } from "../auth/AuthContext";

const WishlistContext = createContext(null);

export function WishlistProvider({ children }) {
  const { isAuthenticated, isAuthLoading } = useAuth();

  const [items, setItems] = useState([]);
  const [isWishlistLoading, setIsWishlistLoading] = useState(false);
  const [updatingProductIds, setUpdatingProductIds] = useState([]);

  const refreshWishlist = useCallback(async () => {
    if (!isAuthenticated) {
      setItems([]);
      return [];
    }

    setIsWishlistLoading(true);

    try {
      const data = await getWishlist();
      const wishlistItems = Array.isArray(data) ? data : data.results || [];

      setItems(wishlistItems);
      return wishlistItems;
    } finally {
      setIsWishlistLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      if (isAuthLoading) {
        return;
      }

      if (!isAuthenticated) {
        setItems([]);
        return;
      }

      refreshWishlist().catch(() => {
        setItems([]);
      });
    }, 0);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [isAuthenticated, isAuthLoading, refreshWishlist]);

  const getWishlistItem = useCallback(
    (productId) =>
      items.find((item) => Number(item.product.id) === Number(productId)),
    [items],
  );

  const isWishlisted = useCallback(
    (productId) => Boolean(getWishlistItem(productId)),
    [getWishlistItem],
  );

  const isUpdating = useCallback(
    (productId) => updatingProductIds.includes(Number(productId)),
    [updatingProductIds],
  );

  const toggleWishlist = useCallback(
    async (product) => {
      const productId = Number(product.id);
      const existingItem = getWishlistItem(productId);

      setUpdatingProductIds((current) => [...current, productId]);

      try {
        if (existingItem) {
          await removeFromWishlist(existingItem.id);

          setItems((current) =>
            current.filter((item) => item.id !== existingItem.id),
          );

          return {
            added: false,
          };
        }

        const newItem = await addToWishlist(productId);

        setItems((current) => {
          const alreadyExists = current.some(
            (item) => Number(item.product.id) === productId,
          );

          if (alreadyExists) {
            return current;
          }

          return [newItem, ...current];
        });

        return {
          added: true,
        };
      } finally {
        setUpdatingProductIds((current) =>
          current.filter((id) => id !== productId),
        );
      }
    },
    [getWishlistItem],
  );

  const value = useMemo(
    () => ({
      items,
      wishlistCount: items.length,
      isWishlistLoading,
      isWishlisted,
      isUpdating,
      toggleWishlist,
      refreshWishlist,
    }),
    [
      items,
      isWishlistLoading,
      isWishlisted,
      isUpdating,
      toggleWishlist,
      refreshWishlist,
    ],
  );

  return (
    <WishlistContext.Provider value={value}>
      {children}
    </WishlistContext.Provider>
  );
}

export function useWishlist() {
  const context = useContext(WishlistContext);

  if (!context) {
    throw new Error("useWishlist must be used inside WishlistProvider.");
  }

  return context;
}
