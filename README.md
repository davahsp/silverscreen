# Silver Screen

Cinema Booking & Operational System built with Django.

> Maintenance note: every commit or code change should update the relevant parts of this README when behavior, routes, setup, tests, architecture, or SDS coverage changes.

This repository implements the Silver Screen MVP based on the SDS and the `silverscreen-claude-design/` UI reference. The app uses Django class-based views, a service-layer pattern for business rules, Django templates, and raw CSS only.

## Product Scope

Silver Screen supports four operating roles:

- Customer: browse active movies, select showtimes, book tickets online, pay through the payment gateway stub, print tickets, and cancel eligible orders.
- Staff Counter: create onsite/counter orders after payment, print tickets immediately, search orders, and complete refund queue items.
- Scheduler: create and disable showtimes.
- Manajer Bioskop: manage movies, products, studios, and studio seat layouts.

Authentication uses Django's built-in `User` and `Group` models. Each user belongs to one role group (`customer`, `staff`, `scheduler`, or `manager`). Customers can self-register; staff, scheduler, and manager accounts are provisioned via the seed command or Django admin. Superusers are treated as managers.

## SDS Rules Implemented

### Online Customer Booking

The online booking flow is multi-phase and follows the design reference stepper. Ticket count is inferred from the number of selected seats and capped by `Order.MAX_TICKETS`:

1. `Pilih Kursi`
2. `Add-ons`
3. `Review`
4. `Pembayaran`

The booking draft is stored in the session until the customer confirms the review step.

On order creation, the system creates:

- `Order` with `source=ONLINE` and `status=PENDING`
- `Ticket` records with `status=HELD`
- `Payment` with `status=UNPAID`
- optional `OrderAddon` records
- service charge via `OrderCharge`
- a provider-side payment in the stub payment gateway

Payment success is not triggered from the Silver Screen order page. The customer must open the stub gateway page, where success or expiration dispatches the callback behavior.

### Payment Gateway Stub

The payment gateway is implemented as a separate Django app: `stub_payment_gateway`.

The main app owns the internal `Payment` model. The stub gateway owns the separate provider-side `GatewayPayment` model.

Implemented endpoints:

- `POST /stub/payment-gateway/issue-payment/`
- `GET /stub/payment-gateway/pay/<gateway_payment_id>/`
- `POST /stub/payment-gateway/pay/<gateway_payment_id>/success/`
- `POST /stub/payment-gateway/pay/<gateway_payment_id>/expire/`
- `POST /payments/callback/`

Callback behavior:

- `PAID`: payment becomes `PAID`, order becomes `CONFIRMED`, tickets become `CONFIRMED`.
- `EXPIRED`: payment becomes `EXPIRED`, order becomes `EXPIRED`, held tickets become `EXPIRED`, and those seats become bookable again.

No real gateway integration is included.

### Cancellation and Refund

Online cancellation rules:

- Unpaid order: order becomes `CANCELED`, tickets become `CANCELED`, payment becomes `CANCELED_BEFORE_PAID`.
- Paid and unprinted order: order becomes `CANCELED`, tickets become `CANCELED`, payment becomes `REFUND_PENDING`.
- Printed ticket: cancellation is blocked with `Tiket sudah dicetak, pesanan tidak dapat dibatalkan.`

Staff can complete refunds manually from the refund queue. Refund automation is intentionally not implemented.

### Onsite Counter Orders

Onsite/counter orders do not create pending records.

The staff POS flow creates records only after the customer pays. The `Buat & Cetak Tiket` action atomically creates:

- `Order` with `source=ONSITE` and `status=CONFIRMED`
- `Payment` with `status=PAID`
- `Ticket` records with `status=PRINTED`
- `printed_at`
- add-ons and charges

No onsite `PENDING` or `HELD` lifecycle is used.

### Showtime Management

Scheduler can create showtimes. `duration_minutes` and `end_at` are derived from the selected movie runtime.

Showtime disable is blocked if active tickets exist with status:

- `HELD`
- `CONFIRMED`
- `PRINTED`

Blocked disable message:

`Showtime tidak dapat dinonaktifkan karena sudah memiliki tiket aktif.`

### Manager Operations

Manager pages support:

- Movie list, create, edit, active/inactive toggle
- Product list, create, edit, active/inactive toggle
- Studio list, create, edit, active/inactive toggle
- Studio layout creation with generated seat numbers
- Studio capacity derived from active seats

Inactive movies are hidden from customer movie selection. Inactive products are hidden from booking and POS add-ons.

Customer movie browsing is limited to movies with active showtimes in the booking window. The booking window is a shared 14-day constant starting from the current local date.

## Architecture

### Apps

`cinema`

- Core domain models
- CBV routes and templates
- Forms
- Business services
- Admin registration
- Raw CSS
- Tests
- Demo seed command

`stub_payment_gateway`

- Provider-side dummy gateway model
- Gateway issue/payment/success/expiration views
- Gateway payment page template
- Gateway CSS

### Pattern

The implementation uses CBVs plus services.

Models are intentionally kept mostly as data definitions with constraints and lightweight derived properties. Business rules live in services:

- `cinema/services/booking.py`
- `cinema/services/payments.py`
- `cinema/services/cancellation.py`
- `cinema/services/scheduling.py`
- `cinema/services/studios.py`
- `cinema/services/ids.py`
- `stub_payment_gateway/services.py`

This keeps workflows such as online order creation, payment callbacks, cancellation, onsite POS creation, showtime disable, and studio layout generation out of fat models.

## Domain Model

Main models:

- `MovieTheme`
- `Movie`
- `StudioType`
- `Studio`
- `Seat`
- `ShowTime`
- `Product`
- `Order`
- `Ticket`
- `Payment`
- `OrderAddon`
- `OrderCharge`

Stub gateway model:

- `GatewayPayment`

Important enums:

- `AgeRating`: `ALL_AGE`, `R7`, `R13`, `R17`, `R21`
- `ProductCategory`: `FOOD`, `DRINK`, `COMBO`, `MERCHANDISE`, `OTHER`
- `OrderSource`: `ONLINE`, `ONSITE`
- `OrderStatus`: `PENDING`, `CONFIRMED`, `EXPIRED`, `CANCELED`
- `TicketStatus`: `HELD`, `CONFIRMED`, `EXPIRED`, `CANCELED`, `PRINTED`
- `PaymentStatus`: `UNPAID`, `PAID`, `EXPIRED`, `REFUND_PENDING`, `REFUNDED`, `CANCELED_BEFORE_PAID`
- `GatewayPaymentStatus`: `WAITING_PAYMENT`, `PAID`, `EXPIRED`

Seat protection is enforced with a conditional unique constraint so a showtime/seat cannot have more than one active ticket in `HELD`, `CONFIRMED`, or `PRINTED`.

## Main Routes

Customer:

- `/`
- `/movies/<id>/`
- `/booking/<showtime_id>/`
- `/booking/<showtime_id>/addons/`
- `/booking/<showtime_id>/review/`
- `/booking/orders/<order_number>/payment/`
- `/orders/`
- `/orders/<order_number>/`

Staff:

- `/staff/pos/`
- `/staff/refunds/`
- `/staff/orders/`

Scheduler:

- `/scheduler/showtimes/`
- `/scheduler/showtimes/new/`
- `/scheduler/showtimes/<id>/edit/`

Manager:

- `/manager/`
- `/manager/movies/`
- `/manager/products/`
- `/manager/studios/`

Authentication:

- `/login/`
- `/logout/`
- `/register/` (customer self-signup)

## UI Implementation

The UI follows `silverscreen-claude-design/`:

- Light mode by default
- Raw CSS only
- No Tailwind
- No Bootstrap
- No shadcn/ui
- No external UI component library
- HTMX progressively enhances date-based jam tayang pagination on movie detail pages
- Topbar with role switcher and reusable movie-ticket SVG mark
- Role-aware horizontal navigation with centralized active-state inference
- Customer movie cards use full-card navigation with hover/focus ticket call-to-action footers
- Movie detail jam tayang is paginated by date across the shared 14-day booking window; the date filter stays statically rendered and HTMX uses `hx-include` to refresh only the list area
- Mobile bottom navigation behavior
- Cards, tables, forms, status badges, seat grid with state legend, POS layout, ticket preview, and gateway page styling
- Booking summary cards update ticket/add-on quantities, unit prices, subtotals, and grand totals before review

CSS files:

- `cinema/static/cinema/css/base.css`
- `stub_payment_gateway/static/stub_payment_gateway/css/payment-gateway.css`

JavaScript:

- `cinema/static/cinema/js/toasts.js`
- HTMX is loaded on the base template for progressive fragment swaps

## Setup

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Apply migrations:

```powershell
python -m django migrate --settings=silverscreen.settings
```

Seed demo data:

```powershell
python -m django seed_demo --settings=silverscreen.settings
```

Run the development server:

```powershell
python -m django runserver 127.0.0.1:8000 --settings=silverscreen.settings
```

Open:

```text
http://127.0.0.1:8000/
```

Demo accounts created by `seed_demo`:

| Username   | Password       | Role      |
|------------|----------------|-----------|
| customer   | customer123    | customer  |
| staff      | staff123       | staff     |
| scheduler  | scheduler123   | scheduler |
| manager    | manager123     | manager   |

## Verification

Run Django system checks:

```powershell
python -m django check --settings=silverscreen.settings
```

Run tests:

```powershell
python -m django test --settings=silverscreen.settings
```

Current test coverage includes:

- Online order creation
- Held ticket creation
- Unpaid payment creation
- Seat unavailability prevention
- Paid callback
- Expired callback
- Held seat release after expiration
- Unknown payment rejection
- Invalid callback status rejection
- Unpaid cancellation
- Paid unprinted cancellation and refund queue transition
- Printed ticket cancellation block
- Atomic onsite order creation
- Showtime derived `end_at`
- Showtime disable blocking
- Studio capacity derivation
- Zero-seat studio validation
- Inactive movie/product filtering
- Customer movie filtering by active showtimes in the 14-day booking window
- Movie detail day-based showtime pagination
- HTMX movie detail jam tayang list replacement
- Multi-phase booking with ticket count inferred from selected seats
- Order max-ticket enforcement in seat selection, limit toasts, and booking service validation
- Booking add-ons visibility
- Public movies/movie-detail browsing
- Login required for booking
- Role-aware login redirect (customer/staff/scheduler/manager)
- Cross-role access is redirected to the user's home
- Customer self-signup creates a user in the `customer` group and redirects to the login page
- Logout returns to the login page

## Current Limitations

- Authentication uses Django auth + Groups; customer pages (movies list and detail) are public, booking and role pages require login.
- Image fields are stored as text paths/URLs for MVP.
- The studio layout builder is intentionally simple.
- SQLite is used by default.
- No real payment gateway integration exists.
- No automated refund processing exists.
- No manual online expiration handler exists; online expiration is callback-driven through the stub gateway.
