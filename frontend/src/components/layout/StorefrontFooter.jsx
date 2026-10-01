import { Link } from "react-router";

import BrandLogo from "../ui/BrandLogo";

function StorefrontFooter() {
  return (
    <footer className="mt-auto border-t border-neutral-200 bg-white">
      <div className="page-container grid gap-8 py-10 sm:grid-cols-2 lg:grid-cols-[1fr_auto_auto]">
        <div>
          <BrandLogo />
          <p className="mt-3 max-w-sm text-sm leading-6 text-neutral-600">A straightforward shopping experience for everyday products.</p>
        </div>
        <div><h2 className="text-sm font-bold">Shop</h2><div className="mt-3 grid gap-2 text-sm text-neutral-600"><Link to="/products" className="hover:text-black">All products</Link><Link to="/cart" className="hover:text-black">Cart</Link></div></div>
        <div><h2 className="text-sm font-bold">Account</h2><div className="mt-3 grid gap-2 text-sm text-neutral-600"><Link to="/account" className="hover:text-black">My account</Link><Link to="/account/orders" className="hover:text-black">Orders</Link></div></div>
      </div>
      <div className="border-t border-neutral-200"><div className="page-container py-5 text-xs text-neutral-500">© {new Date().getFullYear()} ShopSphere. All rights reserved.</div></div>
    </footer>
  );
}

export default StorefrontFooter;
