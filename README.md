# ShopSphere

ShopSphere is a Django REST Framework and React e-commerce application. The customer storefront uses a white primary palette, black secondary palette, and neutral grey supporting colours.

## Requirements

- Python 3.12 or newer
- Node.js 20 or newer
- PostgreSQL for production; SQLite is used automatically for local development when `DB_NAME` is empty

## Windows setup

Run:

```bat
setup.bat
start-dev.bat
```

The storefront opens at `http://127.0.0.1:5173`. Django runs at `http://127.0.0.1:8000`.

To create an administrator:

```bat
backend\.myenv\Scripts\python.exe backend\manage.py createsuperuser
```

Then use `http://127.0.0.1:8000/admin/` to add delivery locations, categories, brands, products, variants, inventory, and product images.

## Environment configuration

`setup.bat` creates `backend\.env` and `frontend\.env` from their example files when they do not exist.

For production, set at minimum:

- `SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- PostgreSQL `DB_*` values
- `FRONTEND_URL`
- `PAYSTACK_SECRET_KEY`
- `PAYSTACK_PUBLIC_KEY`
- `PAYSTACK_CALLBACK_URL`
- Production SMTP `EMAIL_*` values

Never commit either `.env` file.

## Verification

Run:

```bat
verify.bat
```

This runs Django checks, migration validation, all backend tests, frontend linting, and the production frontend build.

## Implemented customer flow

- Catalogue search, category, brand, stock, price, sorting, and pagination
- Product variants, inventory status, image gallery, and verified-purchase reviews
- Three-step email registration, login, password reset, and profile management
- Authenticated cart with server-validated quantities and totals
- Delivery addresses, checkout, Paystack payment initialization and callback verification
- Customer order history, order detail, status, and eligible cancellation

Staff catalogue, inventory, order, payment, review, and dashboard operations remain protected backend endpoints and Django Admin workflows.
