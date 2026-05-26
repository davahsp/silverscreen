/* ================================================
   SILVER SCREEN — Root App, Topbar, Navbar, Router
   ================================================ */

/* ── Navigation Config ───────────────────────────── */
var NAV_MAIN = {
  customer: [
    { page:'movies',          label:'Pilih Film',     icon:'film'          },
    { page:'orders',          label:'Pesanan Saya',   icon:'clipboardList' },
  ],
  staff: [
    { page:'counter-pos',     label:'Counter POS',    icon:'ticket'        },
    { page:'refund-queue',    label:'Antrian Refund', icon:'creditCard'    },
    { page:'order-lookup',    label:'Cari Pesanan',   icon:'search'        },
  ],
  scheduler: [
    { page:'showtimes',       label:'Daftar Showtime',icon:'calendar'      },
    { page:'create-showtime', label:'Jadwalkan',      icon:'plus'          },
  ],
  manager: [
    { page:'dashboard',       label:'Dashboard',      icon:'dashboard'     },
    { page:'movies-mgmt',     label:'Film',           icon:'film'          },
    { page:'products',        label:'Produk',         icon:'shoppingBag'   },
    { page:'studios',         label:'Studio',         icon:'layers'        },
    { page:'studio-builder',  label:'Layout',         icon:'grid'          },
  ],
};



var ROLE_LABELS = {
  customer:  'Pelanggan',
  staff:     'Staff Counter',
  scheduler: 'Penjadwal',
  manager:   'Manajer',
};

var DEFAULT_PAGES = {
  customer:  'movies',
  staff:     'counter-pos',
  scheduler: 'showtimes',
  manager:   'dashboard',
};

/* ── Topbar ──────────────────────────────────────── */
function Topbar() {
  var { currentRole, setCurrentRole, navigate } = useApp();

  function switchRole(role) {
    setCurrentRole(role);
    navigate(DEFAULT_PAGES[role] || 'movies');
  }

  return (
    <header className="topbar">
      <div className="topbar-logo">
        <div className="topbar-logo-mark">
          <Icon name="film" size={16} color="white" />
        </div>
        <div>
          <div className="topbar-logo-text">Silver Screen</div>
          <div className="topbar-logo-sub">Cinema System</div>
        </div>
      </div>

      <div className="topbar-spacer"></div>

      {/* Desktop: pill switcher */}
      <div className="topbar-role-switcher">
        {Object.keys(ROLE_LABELS).map(function(role) {
          return (
            <button
              key={role}
              className={'role-btn' + (currentRole === role ? ' active' : '')}
              onClick={function() { switchRole(role); }}
            >
              {ROLE_LABELS[role]}
            </button>
          );
        })}
      </div>

      {/* Mobile: select dropdown */}
      <select
        className="role-select"
        value={currentRole}
        onChange={function(e) { switchRole(e.target.value); }}
      >
        {Object.keys(ROLE_LABELS).map(function(role) {
          return <option key={role} value={role}>{ROLE_LABELS[role]}</option>;
        })}
      </select>
    </header>
  );
}

/* ── Navbar ──────────────────────────────────────── */
function Navbar() {
  var { currentRole, currentPage, navigate } = useApp();
  var mainItems = NAV_MAIN[currentRole] || [];

  var BOOKING_PAGES = ['booking-showtime','booking-seats','booking-addons','booking-review','booking-payment','order-detail'];

  function isActive(item) {
    if (currentPage === item.page) return true;
    if (item.page === 'orders' && BOOKING_PAGES.indexOf(currentPage) !== -1) return true;
    if (item.page === 'showtimes' && currentPage === 'showtime-detail') return true;
    return false;
  }

  return (
    <nav className="navbar">
      {mainItems.map(function(item) {
        return (
          <button
            key={item.page}
            className={'nav-tab' + (isActive(item) ? ' active' : '')}
            onClick={function() { navigate(item.page); }}
          >
            <Icon name={item.icon} size={15} />
            <span>{item.label}</span>
          </button>
        );
      })}


    </nav>
  );
}

/* ── Page Router ─────────────────────────────────── */
function PageRouter() {
  var { currentRole, currentPage } = useApp();

  if (currentPage === 'gateway')       return React.createElement(GatewayPage);
  if (currentPage === 'order-detail')  return React.createElement(OrderDetail);

  if (currentRole === 'customer') {
    if (currentPage === 'movies')           return React.createElement(CustomerMovies);
    if (currentPage === 'orders')           return React.createElement(CustomerOrders);
    if (currentPage === 'booking-showtime') return React.createElement(BookingShowtime);
    if (currentPage === 'booking-seats')    return React.createElement(BookingSeats);
    if (currentPage === 'booking-addons')   return React.createElement(BookingAddons);
    if (currentPage === 'booking-review')   return React.createElement(BookingReview);
    if (currentPage === 'booking-payment')  return React.createElement(BookingPayment);
    return React.createElement(CustomerMovies);
  }
  if (currentRole === 'staff') {
    if (currentPage === 'counter-pos')  return React.createElement(CounterPOS);
    if (currentPage === 'refund-queue') return React.createElement(RefundQueue);
    if (currentPage === 'order-lookup') return React.createElement(OrderLookup);
    return React.createElement(CounterPOS);
  }
  if (currentRole === 'scheduler') {
    if (currentPage === 'showtimes')       return React.createElement(SchedulerShowtimes);
    if (currentPage === 'create-showtime') return React.createElement(CreateShowtime);
    if (currentPage === 'showtime-detail') return React.createElement(ShowtimeDetail);
    return React.createElement(SchedulerShowtimes);
  }
  if (currentRole === 'manager') {
    if (currentPage === 'dashboard')      return React.createElement(ManagerDashboard);
    if (currentPage === 'movies-mgmt')    return React.createElement(MovieManagement);
    if (currentPage === 'products')       return React.createElement(ProductCatalog);
    if (currentPage === 'studios')        return React.createElement(StudioManagement);
    if (currentPage === 'studio-builder') return React.createElement(StudioLayoutBuilder);
    return React.createElement(ManagerDashboard);
  }
  return React.createElement(CustomerMovies);
}



/* ── App Shell ───────────────────────────────────── */
function AppShell() {
  var { currentPage } = useApp();

  // Gateway: full-screen, no shell chrome
  if (currentPage === 'gateway') {
    return (
      <div style={{ height:'100vh', overflowY:'auto' }}>
        <ToastContainer />
        <PageRouter />
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Topbar />
      <Navbar />
      <main className="main">
        <div className="main-inner">
          <PageRouter />
        </div>
      </main>
      <ToastContainer />
    </div>
  );
}

/* ── Root ────────────────────────────────────────── */
function App() {
  return React.createElement(AppProvider, null, React.createElement(AppShell));
}

ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(App));
