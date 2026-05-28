# Silver Screen

Cinema Booking & Operational System built with Django.

> Maintenance note: every commit or code change should update the relevant parts of this README when behavior, routes, setup, tests, architecture, or SDS coverage changes.

This repository implements the Silver Screen MVP based on the SDS and the `silverscreen-claude-design/` UI reference. The app uses Django class-based views, a service-layer pattern for business rules, Django templates, and raw CSS only.

## Product Scope

Silver Screen supports four operating roles:

- Customer: browse active movies, select showtimes, book tickets online, pay through the payment gateway stub, view their own orders, print tickets, and cancel eligible orders.
- Staff Counter: create onsite/counter orders after payment, print tickets immediately, view all orders, and complete refund queue items.
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

- `Order` assigned to the requesting customer with `channel=ONLINE` and `status=PENDING`
- `Ticket` records with `status=HELD`
- `Payment` with `status=UNPAID`
- optional `OrderAddon` records
- service charge via `OrderCharge`
- a provider-side payment in the stub payment gateway with a unique VA account

Payment success is not triggered from the Silver Screen order page. The customer must open the stub gateway page, where success or expiration dispatches the callback behavior.

### Payment Gateway Stub

The payment gateway is implemented as a separate Django app: `stub_payment_gateway`.

The main app owns the internal `Payment` model. The stub gateway owns the separate provider-side `GatewayPayment` model.

Implemented endpoints:

- `POST /stub/payment-gateway/issue-payment/`
- `GET /stub/payment-gateway/`
- `GET /stub/payment-gateway/pay/<gateway_payment_id>/`
- `POST /stub/payment-gateway/pay/<gateway_payment_id>/success/`
- `POST /stub/payment-gateway/pay/<gateway_payment_id>/expire/`
- `POST /payments/callback/`

Issuing a payment creates a separate `GatewayPayment`, assigns a unique VA account, and returns gateway ID, payment URL, `expired_in`, `expires_at`, and VA account data. Silver Screen stores those details on its internal `Payment` for display and reconciliation.

Callback behavior:

- `PAID`: payment becomes `PAID`, order becomes `CONFIRMED`, tickets become `CONFIRMED`, and each confirmed ticket receives a unique QR UUID.
- `EXPIRED`: payment becomes `EXPIRED`, order becomes `EXPIRED`, held tickets become `EXPIRED`, and those seats become bookable again.

Payment and order final states are sourced only from the gateway callback. Countdown displays in Silver Screen and the gateway are visual only.

No real gateway integration is included.

Stub worker commands:

```powershell
python -m django expire_gateway_payments --settings=silverscreen.settings
python -m django expire_gateway_payments --watch --interval 5 --settings=silverscreen.settings
```

`expire_gateway_payments` is the authoritative gateway-side expiry worker and sends callbacks to `STUB_GATEWAY_CALLBACK_URL`. Silver Screen does not run a payment status worker; its countdown display is JavaScript-only and compares the browser's current time with the payment expiration time.

### Cancellation and Refund

Online cancellation rules:

- Unpaid order: gateway payment becomes `CANCELLED`, making the VA invalid/stale; order becomes `CANCELED`, tickets become `CANCELED`, payment becomes `CANCELED_BEFORE_PAID`.
- Paid confirmed order: order becomes `CANCELED`, tickets become `CANCELED`, payment becomes `REFUND_PENDING`.
- Used ticket: cancellation is blocked with `Tiket sudah digunakan, pesanan tidak dapat dibatalkan.`

Staff can complete refunds manually from the refund queue. Refund automation is intentionally not implemented.

### Onsite Counter Orders

Onsite/counter orders do not create pending records.

The staff POS flow creates records only after the customer pays. The `Buat Order & Buka Tiket` action atomically creates:

- `Order` with optional customer assignment, `channel=ONSITE`, and `status=CONFIRMED`
- `Payment` with `status=PAID`
- `Ticket` records with `status=CONFIRMED`
- a unique QR UUID for each ticket
- add-ons and charges

No onsite `PENDING` or `HELD` lifecycle is used.

The POS customer selector is optional and searchable by username or email. Staff can attach an onsite order to an existing customer account, including one the customer just registered from their own device, or leave it as walk-in/no account.

Printing tickets is not a status transition. It only creates a physical copy of the digital ticket; ticket status remains `CONFIRMED`.

### Ticket QR and Admission Scan

Each ticket receives a hard-to-guess UUID QR identifier when it becomes `CONFIRMED`. The identifier stays attached to the ticket after it becomes `USED`.

The scanner/gate application is outside this Django app. It is expected to share the same database, read the QR UUID, locate the matching ticket, and mark it `USED`. If a QR is scanned again after the ticket is already `USED`, the external scanner should reject entry.

### Showtime Management

Scheduler can create showtimes. `duration_minutes` and `end_at` are derived from the selected movie runtime.

Showtime disable is blocked if active tickets exist with status:

- `HELD`
- `CONFIRMED`
- `USED`

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

Payment records on both sides store a VA account for the stub transfer flow.

Important enums:

- `AgeRating`: `ALL_AGE`, `R7`, `R13`, `R17`, `R21`
- `ProductCategory`: `FOOD`, `DRINK`, `COMBO`, `MERCHANDISE`, `OTHER`
- `OrderChannel`: `ONLINE`, `ONSITE`
- `OrderStatus`: `PENDING`, `CONFIRMED`, `EXPIRED`, `CANCELED`
- `TicketStatus`: `HELD`, `CONFIRMED`, `USED`, `EXPIRED`, `CANCELED`
- `PaymentStatus`: `UNPAID`, `PAID`, `EXPIRED`, `REFUND_PENDING`, `REFUNDED`, `CANCELED_BEFORE_PAID`
- `GatewayPaymentStatus`: `WAITING_PAYMENT`, `PAID`, `EXPIRED`, `CANCELLED`

Seat protection is enforced with a conditional unique constraint so a showtime/seat cannot have more than one active ticket in `HELD`, `CONFIRMED`, or `USED`.

## Main Routes

Customer:

- `/` (role-based redirect)
- `/movies/`
- `/movies/<id>/`
- `/booking/<showtime_id>/`
- `/booking/<showtime_id>/addons/`
- `/booking/<showtime_id>/review/`
- `/booking/orders/<order_number>/payment/`
- `/orders/`
- `/orders/table/` (HTMX order list partial)
- `/orders/<order_number>/`

Staff:

- `/staff/pos/`
- `/staff/refunds/`
- `/orders/`
- `/staff/orders/` (redirects to `/orders/`)

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

Temporary stub navigation:

- `/stub/payment-gateway/` is linked from every authenticated role navigation for demo access.

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
- Staff POS starts with an unselected horizontal showtime carousel limited to active movies with active showtimes today whose `end_at` is still in the future. Choosing a showtime fetches only the seat-map form partial with HTMX; seat selection is capped by `Order.MAX_TICKETS`, the summary stays on the right, add-ons sit below the seat/summary area, and the submit action stays fixed at the viewport bottom.
- Staff POS includes an optional searchable customer selector so onsite orders can be attached to a customer account or left as walk-in orders.
- The shared order list shell at `/orders/` uses a directly rendered HTMX filter for order ID, movie name, and showtime date. The order list itself is loaded and replaced from `/orders/table/`; customers see only orders assigned to their account, while staff see all orders. `/staff/orders/` redirects to this shared endpoint.
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
- Customer order list shell renders the static HTMX filter and loads the order table partial
- Order table partial renders full-width linked order cards with `Metode Pemesanan`, movie poster, ticket count, and showtime start
- Order table partial filters by order ID, movie name, and showtime date
- Customer order list queryset is limited to orders assigned to the requesting customer
- Held ticket creation
- Unpaid payment creation
- Gateway VA assignment and issue-payment response data
- Seat unavailability prevention
- Paid callback
- Expired callback
- Gateway paid and expired simulation callback payloads
- Gateway expiration worker behavior
- Held seat release after expiration
- Unknown payment rejection
- Invalid callback status rejection
- Unpaid cancellation
- Unpaid cancellation cancels the provider-side gateway payment
- Paid confirmed cancellation and refund queue transition
- Used ticket cancellation block
- Used ticket seat and showtime protection
- QR UUID assignment for confirmed tickets
- Printing tickets without changing ticket status
- Atomic onsite order creation
- Optional customer assignment for onsite POS orders
- POS showtime carousel starts unselected, HTMX showtime changes return only the seat-map partial, and POS seat selection uses the `Order.MAX_TICKETS` cap
- POS showtime carousel only lists today's showtimes that have not ended
- Staff order list uses the shared `/orders/` endpoint and renders all orders as linked order cards
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
- No scanner/gate UI or API is implemented; an external scanner sharing the same DB marks tickets as `USED`.
- No automated refund processing exists.
- Online expiration is callback-driven through the stub gateway worker or simulate-expire action.
