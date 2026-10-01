import { Route, Routes } from "react-router";

import ProtectedRoute from "../features/auth/ProtectedRoute";
import StaffRoute from "../features/auth/StaffRoute";

import AccountLayout from "../layouts/AccountLayout";
import StaffLayout from "../layouts/StaffLayout";
import StorefrontLayout from "../layouts/StorefrontLayout";

import AccountOverviewPage from "../pages/account/AccountOverviewPage";
import NotificationsPage from "../pages/account/NotificationsPage";
import OrderDetailPage from "../pages/account/OrderDetailPage";
import OrderListPage from "../pages/account/OrderListPage";
import ProfilePage from "../pages/account/ProfilePage";
import RefundDetailPage from "../pages/account/RefundDetailPage";
import RefundListPage from "../pages/account/RefundListPage";
import SecurityPage from "../pages/account/SecurityPage";
import WishlistPage from "../pages/account/WishlistPage";

import ForgotPasswordPage from "../pages/auth/ForgotPasswordPage";
import LoginPage from "../pages/auth/LoginPage";
import RegisterPage from "../pages/auth/RegisterPage";
import ResetPasswordPage from "../pages/auth/ResetPasswordPage";

import CheckoutPage from "../pages/checkout/CheckoutPage";
import PaymentCallbackPage from "../pages/checkout/PaymentCallbackPage";

import NotFoundPage from "../pages/errors/NotFoundPage";

import StaffDashboardPage from "../pages/staff/StaffDashboardPage";
import StaffOrderDetailPage from "../pages/staff/StaffOrderDetailPage";
import StaffOrderListPage from "../pages/staff/StaffOrderListPage";

import CartPage from "../pages/storefront/CartPage";
import HomePage from "../pages/storefront/HomePage";
import ProductDetailPage from "../pages/storefront/ProductDetailPage";
import ProductListPage from "../pages/storefront/ProductListPage";
import StaffProductListPage from "../pages/staff/StaffProductListPage";
import StaffInventoryPage from "../pages/staff/StaffInventoryPage";
import StaffReviewsPage from "../pages/staff/StaffReviewsPage";

function AppRoutes() {
  return (
    <Routes>
      {/* Authentication pages without navbar or footer */}
      <Route path="login" element={<LoginPage />} />

      <Route path="register" element={<RegisterPage />} />

      <Route path="forgot-password" element={<ForgotPasswordPage />} />

      <Route path="reset-password" element={<ResetPasswordPage />} />

      {/* Staff-only dashboard */}
      <Route element={<StaffRoute />}>
        <Route path="staff" element={<StaffLayout />}>
          <Route index element={<StaffDashboardPage />} />

          <Route path="orders" element={<StaffOrderListPage />} />

          <Route
            path="orders/:orderNumber"
            element={<StaffOrderDetailPage />}
          />

          <Route path="products" element={<StaffProductListPage />} />

          <Route path="inventory" element={<StaffInventoryPage />} />
          <Route path="reviews" element={<StaffReviewsPage />} />
        </Route>
      </Route>

      {/* Customer storefront */}
      <Route element={<StorefrontLayout />}>
        <Route index element={<HomePage />} />

        <Route path="products" element={<ProductListPage />} />

        <Route path="products/:slug" element={<ProductDetailPage />} />

        <Route path="payment/callback" element={<PaymentCallbackPage />} />

        {/* Authenticated customer pages */}
        <Route element={<ProtectedRoute />}>
          <Route path="cart" element={<CartPage />} />

          <Route path="checkout" element={<CheckoutPage />} />

          <Route path="account" element={<AccountLayout />}>
            <Route index element={<AccountOverviewPage />} />

            <Route path="orders" element={<OrderListPage />} />

            <Route path="orders/:orderNumber" element={<OrderDetailPage />} />

            <Route path="refunds" element={<RefundListPage />} />

            <Route path="refunds/:reference" element={<RefundDetailPage />} />

            <Route path="wishlist" element={<WishlistPage />} />

            <Route path="notifications" element={<NotificationsPage />} />

            <Route path="profile" element={<ProfilePage />} />

            <Route path="security" element={<SecurityPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

export default AppRoutes;
