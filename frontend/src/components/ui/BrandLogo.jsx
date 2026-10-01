import { Link } from "react-router";

function BrandLogo({ className = "" }) {
  return (
    <Link
      to="/"
      aria-label="ShopSphere home"
      className={`inline-flex items-center font-display text-2xl font-extrabold tracking-tight text-neutral-950 ${className}`}
    >
      Shop<span className="text-neutral-500">Sphere</span>
    </Link>
  );
}

export default BrandLogo;
