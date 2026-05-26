/* ================================================
   SILVER SCREEN — React Context + Business Logic
   ================================================ */

const AppContext = React.createContext(null);

function AppProvider({ children }) {
  const [movies, setMovies]               = React.useState(window.INITIAL_DATA.movies);
  const [studios, setStudios]             = React.useState(window.INITIAL_DATA.studios);
  const [products, setProducts]           = React.useState(window.INITIAL_DATA.products);
  const [showtimes, setShowtimes]         = React.useState(window.INITIAL_DATA.showtimes);
  const [orders, setOrders]               = React.useState(window.INITIAL_DATA.orders);
  const [gatewayPayments, setGatewayPayments] = React.useState(window.INITIAL_DATA.gatewayPayments);
  const [toasts, setToasts]               = React.useState([]);
  const [integrationLog, setIntegrationLog] = React.useState([]);

  // Navigation
  const [currentRole, setCurrentRole]     = React.useState('customer');
  const [currentPage, setCurrentPage]     = React.useState('movies');
  const [pageParams, setPageParams]       = React.useState({});
  const [booking, setBooking]             = React.useState(null);

  const navigate = React.useCallback(function(page, params) {
    setCurrentPage(page);
    setPageParams(params || {});
  }, []);

  // ── Toasts ──────────────────────────────────────
  const addToast = React.useCallback(function(message, type) {
    var id = Date.now() + Math.random();
    var t = type || 'success';
    setToasts(function(prev) { return prev.concat({ id: id, message: message, type: t }); });
    setTimeout(function() {
      setToasts(function(prev) { return prev.filter(function(x) { return x.id !== id; }); });
    }, 4000);
  }, []);

  const removeToast = React.useCallback(function(id) {
    setToasts(function(prev) { return prev.filter(function(x) { return x.id !== id; }); });
  }, []);

  // ── Integration Log ──────────────────────────────
  const logEvent = React.useCallback(function(message, kind) {
    setIntegrationLog(function(prev) {
      return prev.concat({
        id: Date.now() + Math.random(),
        time: new Date().toLocaleTimeString('id-ID', { hour:'2-digit', minute:'2-digit', second:'2-digit' }),
        message: message,
        kind: kind || 'default',
      });
    });
  }, []);

  // ── Seat Occupancy ───────────────────────────────
  const getOccupancy = React.useCallback(function(showtimeId) {
    var occ = {};
    orders.forEach(function(order) {
      if (order.showtime.id !== showtimeId) return;
      order.tickets.forEach(function(ticket) {
        if (['HELD','CONFIRMED','PRINTED'].indexOf(ticket.status) !== -1) {
          occ[ticket.seat.id] = { status: ticket.status, orderId: order.id };
        }
      });
    });
    return occ;
  }, [orders]);

  // ── Showtime ticket counts ───────────────────────
  const getShowtimeStats = React.useCallback(function(showtimeId) {
    var held = 0, confirmed = 0, printed = 0;
    orders.forEach(function(order) {
      if (order.showtime.id !== showtimeId) return;
      order.tickets.forEach(function(t) {
        if (t.status === 'HELD') held++;
        else if (t.status === 'CONFIRMED') confirmed++;
        else if (t.status === 'PRINTED') printed++;
      });
    });
    return { held: held, confirmed: confirmed, printed: printed };
  }, [orders]);

  // ── Create Online Order ──────────────────────────
  const createOnlineOrder = React.useCallback(function(data) {
    // data: { showtime, selectedSeats, addons, customer_name }
    var now        = new Date().toISOString();
    var expireAt   = new Date(Date.now() + 15 * 60 * 1000).toISOString();
    var orderId    = window.genId('ORD');
    var orderNum   = 'SS-2026-' + String(Math.floor(Math.random() * 9000) + 1000);
    var intPayId   = window.genId('PAY-INT');
    var gwPayId    = window.genId('PGW');
    var payId      = window.genId('PAY');

    var ticketPrice = data.showtime.price;
    var ticketsTotal = ticketPrice * data.selectedSeats.length;
    var addonsTotal  = data.addons.reduce(function(s, a) { return s + a.total_price; }, 0);
    var serviceCharge = data.selectedSeats.length > 0 ? 5000 : 0;
    var totalAmount  = ticketsTotal + addonsTotal + serviceCharge;

    var tickets = data.selectedSeats.map(function(seat, i) {
      return {
        id:         window.genId('TKT'),
        code:       'TKT-' + Math.random().toString(36).substr(2,6).toUpperCase(),
        seat:       seat,
        status:     'HELD',
        printed_at: null,
      };
    });

    var payment = {
      id:                  payId,
      internal_payment_id: intPayId,
      gateway_payment_id:  gwPayId,
      amount:              totalAmount,
      status:              'UNPAID',
      created_at:          now,
      paid_at:             null,
      expired_at:          expireAt,
      payment_url:         '/stub/payment-gateway/pay/' + gwPayId,
    };

    var gatewayPay = {
      gateway_payment_id:  gwPayId,
      internal_payment_id: intPayId,
      client_id:           'SILVERSCREEN',
      amount:              totalAmount,
      issued_at:           now,
      expiration_in:       900,
      expired_at:          expireAt,
      status:              'WAITING_PAYMENT',
    };

    var order = {
      id:            orderId,
      number:        orderNum,
      source:        'ONLINE',
      status:        'PENDING',
      customer_name: data.customer_name || 'Pelanggan',
      showtime:      data.showtime,
      tickets:       tickets,
      addons:        data.addons,
      charges:       serviceCharge > 0 ? [{ id: window.genId('CHG'), name: 'Biaya Layanan', price: serviceCharge }] : [],
      payment:       payment,
      total_amount:  totalAmount,
      created_at:    now,
    };

    setOrders(function(prev) { return [order].concat(prev); });
    setGatewayPayments(function(prev) { return [gatewayPay].concat(prev); });

    logEvent('Order ' + orderNum + ' dibuat (ONLINE)', 'default');
    logEvent('Internal Payment ' + intPayId + ' dibuat [UNPAID]', 'default');
    logEvent('POST /stub/payment-gateway/issue-payment/', 'request');
    logEvent('Gateway Payment ' + gwPayId + ' dibuat [WAITING_PAYMENT]', 'response');
    logEvent('Payment URL: /stub/payment-gateway/pay/' + gwPayId, 'response');

    return order;
  }, [logEvent]);

  // ── Gateway Callback ─────────────────────────────
  const processPaymentCallback = React.useCallback(function(intPayId, gwPayId, cbStatus) {
    logEvent('POST /payments/callback/ — status: ' + cbStatus, 'request');

    setGatewayPayments(function(prev) {
      return prev.map(function(gp) {
        if (gp.gateway_payment_id !== gwPayId) return gp;
        return Object.assign({}, gp, { status: cbStatus === 'PAID' ? 'PAID' : 'EXPIRED' });
      });
    });

    setOrders(function(prev) {
      return prev.map(function(order) {
        if (order.payment.internal_payment_id !== intPayId) return order;
        var now = new Date().toISOString();
        var newPayStatus, newOrderStatus, newTicketStatus;
        if (cbStatus === 'PAID') {
          newPayStatus    = 'PAID';
          newOrderStatus  = 'CONFIRMED';
          newTicketStatus = 'CONFIRMED';
        } else {
          newPayStatus    = 'EXPIRED';
          newOrderStatus  = 'EXPIRED';
          newTicketStatus = 'EXPIRED';
        }
        return Object.assign({}, order, {
          status: newOrderStatus,
          payment: Object.assign({}, order.payment, {
            status:  newPayStatus,
            paid_at: cbStatus === 'PAID' ? now : null,
          }),
          tickets: order.tickets.map(function(t) {
            return Object.assign({}, t, { status: newTicketStatus });
          }),
        });
      });
    });

    if (cbStatus === 'PAID') {
      logEvent('Internal Payment ' + intPayId + ' → PAID', 'response');
      logEvent('Order → CONFIRMED', 'response');
      logEvent('Tiket → CONFIRMED', 'response');
    } else {
      logEvent('Internal Payment ' + intPayId + ' → EXPIRED', 'response');
      logEvent('Order → EXPIRED', 'response');
      logEvent('Tiket → EXPIRED — kursi dilepas', 'response');
    }
  }, [logEvent]);

  // ── Print Ticket ─────────────────────────────────
  const printTicket = React.useCallback(function(orderId, ticketId) {
    var now = new Date().toISOString();
    setOrders(function(prev) {
      return prev.map(function(order) {
        if (order.id !== orderId) return order;
        return Object.assign({}, order, {
          tickets: order.tickets.map(function(t) {
            if (t.id !== ticketId) return t;
            return Object.assign({}, t, { status: 'PRINTED', printed_at: now });
          }),
        });
      });
    });
    addToast('Tiket berhasil dicetak', 'success');
  }, [addToast]);

  const printAllTickets = React.useCallback(function(orderId) {
    var now = new Date().toISOString();
    setOrders(function(prev) {
      return prev.map(function(order) {
        if (order.id !== orderId) return order;
        return Object.assign({}, order, {
          tickets: order.tickets.map(function(t) {
            if (t.status !== 'CONFIRMED') return t;
            return Object.assign({}, t, { status: 'PRINTED', printed_at: now });
          }),
        });
      });
    });
    addToast('Semua tiket berhasil dicetak', 'success');
  }, [addToast]);

  // ── Cancel Order ─────────────────────────────────
  const cancelOrder = React.useCallback(function(orderId) {
    setOrders(function(prev) {
      return prev.map(function(order) {
        if (order.id !== orderId) return order;
        var hasPrinted = order.tickets.some(function(t) { return t.status === 'PRINTED'; });
        if (hasPrinted) return order; // business rule: can't cancel printed
        var payStatus = order.payment.status === 'PAID' ? 'REFUND_PENDING' : 'CANCELED_BEFORE_PAID';
        return Object.assign({}, order, {
          status: 'CANCELED',
          payment: Object.assign({}, order.payment, { status: payStatus }),
          tickets: order.tickets.map(function(t) {
            return Object.assign({}, t, { status: 'CANCELED' });
          }),
        });
      });
    });
    addToast('Pesanan dibatalkan', 'info');
    logEvent('Order ' + orderId + ' → CANCELED', 'default');
  }, [addToast, logEvent]);

  // ── Mark Refund Complete ─────────────────────────
  const markRefundComplete = React.useCallback(function(orderId) {
    setOrders(function(prev) {
      return prev.map(function(order) {
        if (order.id !== orderId) return order;
        return Object.assign({}, order, {
          payment: Object.assign({}, order.payment, { status: 'REFUNDED' }),
        });
      });
    });
    addToast('Refund berhasil ditandai selesai', 'success');
    logEvent('Refund untuk order ' + orderId + ' → REFUNDED', 'default');
  }, [addToast, logEvent]);

  // ── Create Onsite Order ──────────────────────────
  const createOnsiteOrder = React.useCallback(function(data) {
    var now       = new Date().toISOString();
    var orderId   = window.genId('ORD');
    var orderNum  = 'SS-2026-' + String(Math.floor(Math.random() * 9000) + 1000);
    var intPayId  = window.genId('PAY-INT');
    var payId     = window.genId('PAY');

    var ticketPrice  = data.showtime.price;
    var ticketsTotal = ticketPrice * data.selectedSeats.length;
    var addonsTotal  = data.addons.reduce(function(s, a) { return s + a.total_price; }, 0);
    var totalAmount  = ticketsTotal + addonsTotal;

    var tickets = data.selectedSeats.map(function(seat) {
      return {
        id:         window.genId('TKT'),
        code:       'TKT-' + Math.random().toString(36).substr(2,6).toUpperCase(),
        seat:       seat,
        status:     'PRINTED',
        printed_at: now,
      };
    });

    var payment = {
      id:                  payId,
      internal_payment_id: intPayId,
      gateway_payment_id:  null,
      amount:              totalAmount,
      status:              'PAID',
      created_at:          now,
      paid_at:             now,
      expired_at:          null,
      payment_url:         null,
    };

    var order = {
      id:            orderId,
      number:        orderNum,
      source:        'ONSITE',
      status:        'CONFIRMED',
      customer_name: data.customer_name || 'Pelanggan Onsite',
      showtime:      data.showtime,
      tickets:       tickets,
      addons:        data.addons,
      charges:       [],
      payment:       payment,
      total_amount:  totalAmount,
      created_at:    now,
    };

    setOrders(function(prev) { return [order].concat(prev); });
    addToast('Tiket berhasil dibuat dan dicetak', 'success');
    return order;
  }, [addToast]);

  // ── Showtime Management ──────────────────────────
  const createShowtime = React.useCallback(function(data) {
    var id = window.genId('SH');
    var dur = data.movie.runtime_minutes;
    var endAt = new Date(new Date(data.start_at).getTime() + dur * 60000).toISOString();
    var st = Object.assign({}, data, {
      id: id,
      duration_minutes: dur,
      end_at: endAt,
      is_active: true,
    });
    setShowtimes(function(prev) { return [st].concat(prev); });
    addToast('Showtime berhasil dijadwalkan', 'success');
    return st;
  }, [addToast]);

  const toggleShowtime = React.useCallback(function(showtimeId) {
    setShowtimes(function(prev) {
      return prev.map(function(st) {
        if (st.id !== showtimeId) return st;
        return Object.assign({}, st, { is_active: !st.is_active });
      });
    });
  }, []);

  // ── Movie Management ─────────────────────────────
  const addMovie = React.useCallback(function(data) {
    var m = Object.assign({ id: window.genId('M') }, data);
    setMovies(function(prev) { return [m].concat(prev); });
    addToast('Film berhasil ditambahkan', 'success');
    return m;
  }, [addToast]);

  const updateMovie = React.useCallback(function(id, data) {
    setMovies(function(prev) {
      return prev.map(function(m) {
        return m.id === id ? Object.assign({}, m, data) : m;
      });
    });
    addToast('Film berhasil diperbarui', 'success');
  }, [addToast]);

  // ── Product Management ───────────────────────────
  const addProduct = React.useCallback(function(data) {
    var p = Object.assign({ id: window.genId('P') }, data);
    setProducts(function(prev) { return [p].concat(prev); });
    addToast('Produk berhasil ditambahkan', 'success');
    return p;
  }, [addToast]);

  const updateProduct = React.useCallback(function(id, data) {
    setProducts(function(prev) {
      return prev.map(function(p) {
        return p.id === id ? Object.assign({}, p, data) : p;
      });
    });
    addToast('Produk berhasil diperbarui', 'success');
  }, [addToast]);

  // ── Studio Management ────────────────────────────
  const addStudio = React.useCallback(function(data) {
    var st = Object.assign({ id: window.genId('STD'), is_active: true }, data);
    st.capacity = st.seats.filter(function(s) { return s.is_active && !s.is_aisle; }).length;
    setStudios(function(prev) { return [st].concat(prev); });
    addToast('Studio berhasil dibuat', 'success');
    return st;
  }, [addToast]);

  const ctxValue = {
    // State
    movies, studios, products, showtimes, orders, gatewayPayments,
    toasts, integrationLog,
    currentRole, currentPage, pageParams, booking,
    // Setters
    setCurrentRole, navigate, setBooking,
    // Actions
    addToast, removeToast, logEvent,
    getOccupancy, getShowtimeStats,
    createOnlineOrder, processPaymentCallback,
    printTicket, printAllTickets, cancelOrder,
    markRefundComplete, createOnsiteOrder,
    createShowtime, toggleShowtime,
    addMovie, updateMovie, addProduct, updateProduct, addStudio,
    // Formatters (also on window, but convenient here)
    fmtCurrency: window.fmtCurrency,
    fmtDate:     window.fmtDate,
    fmtDateTime: window.fmtDateTime,
    fmtTime:     window.fmtTime,
  };

  return React.createElement(AppContext.Provider, { value: ctxValue }, children);
}

function useApp() {
  return React.useContext(AppContext);
}

Object.assign(window, { AppContext, AppProvider, useApp });
