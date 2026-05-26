/* ================================================
   SILVER SCREEN — Sample Data & Initial State
   Plain JS — no JSX, exported to window.INITIAL_DATA
   ================================================ */

(function () {
  var rowLabels = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

  function generateSeats(studioId, rows, cols, aisles) {
    var seats = [];
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        var isAisle = aisles.some(function (a) { return a[0] === r && a[1] === c; });
        seats.push({
          id: studioId + '-' + rowLabels[r] + (c + 1),
          studio_id: studioId,
          number: rowLabels[r] + (c + 1),
          row: rowLabels[r],
          grid_x_pos: c,
          grid_y_pos: r,
          is_active: !isAisle,
          is_aisle: isAisle,
        });
      }
    }
    return seats;
  }

  var studioTypes = [
    { id: 'ST001', name: 'Regular',  base_price: 45000  },
    { id: 'ST002', name: 'Premiere', base_price: 85000  },
    { id: 'ST003', name: 'IMAX',     base_price: 120000 },
  ];

  var s1Seats = generateSeats('STD001', 8, 10, [[3,4],[3,5]]);
  var s2Seats = generateSeats('STD002', 6, 8,  [[2,3],[2,4]]);
  var s3Seats = generateSeats('STD003', 10, 12, [[4,5],[4,6],[5,5],[5,6]]);

  var studios = [
    {
      id: 'STD001', name: 'Studio 1', studio_type: studioTypes[0],
      grid_x_pos: 10, grid_y_pos: 8, is_active: true, seats: s1Seats,
      capacity: s1Seats.filter(function(s){ return s.is_active && !s.is_aisle; }).length,
    },
    {
      id: 'STD002', name: 'Studio 2', studio_type: studioTypes[1],
      grid_x_pos: 8, grid_y_pos: 6, is_active: true, seats: s2Seats,
      capacity: s2Seats.filter(function(s){ return s.is_active && !s.is_aisle; }).length,
    },
    {
      id: 'STD003', name: 'Studio 3', studio_type: studioTypes[2],
      grid_x_pos: 12, grid_y_pos: 10, is_active: true, seats: s3Seats,
      capacity: s3Seats.filter(function(s){ return s.is_active && !s.is_aisle; }).length,
    },
  ];

  var movies = [
    {
      id: 'M001', title: 'Ruang Sunyi',
      synopsis: 'Seorang pianis muda yang kehilangan kemampuan mendengar harus menemukan kembali makna dalam musik melalui perjalanan emosional yang mendalam bersama seorang guru misterius.',
      age_rating: 'R13', runtime_minutes: 112, is_active: true,
      theme: { id: 'T001', name: 'Drama' },
    },
    {
      id: 'M002', title: 'Galaksi Terakhir',
      synopsis: 'Ekspedisi luar angkasa terakhir umat manusia menuju galaksi yang jauh demi menyelamatkan bumi dari kehancuran kosmik yang tak terhindarkan.',
      age_rating: 'R13', runtime_minutes: 128, is_active: true,
      theme: { id: 'T002', name: 'Sci-Fi' },
    },
    {
      id: 'M003', title: 'Rumah di Belakang Layar',
      synopsis: 'Sebuah keluarga pindah ke rumah tua di pinggiran kota dan mulai menemukan rahasia gelap yang tersimpan di balik dinding rumah tersebut.',
      age_rating: 'R17', runtime_minutes: 101, is_active: true,
      theme: { id: 'T003', name: 'Horror' },
    },
    {
      id: 'M004', title: 'Petualangan Raka',
      synopsis: 'Raka, bocah 10 tahun yang pemberani, memulai petualangan luar biasa bersama sahabat-sahabatnya untuk menemukan harta karun legendaris yang telah hilang selama berabad-abad.',
      age_rating: 'ALL_AGE', runtime_minutes: 95, is_active: true,
      theme: { id: 'T004', name: 'Family' },
    },
    {
      id: 'M005', title: 'Arsip Film Lama',
      synopsis: 'Dokumenter tentang sejarah industri film Indonesia dari masa ke masa melalui koleksi arsip langka yang hampir punah dan hampir terlupakan.',
      age_rating: 'R7', runtime_minutes: 90, is_active: false,
      theme: { id: 'T005', name: 'Documentary' },
    },
  ];

  var products = [
    { id: 'P001', name: 'Popcorn Regular',  category: 'FOOD',          price: 30000, is_active: true  },
    { id: 'P002', name: 'Popcorn Large',    category: 'FOOD',          price: 45000, is_active: true  },
    { id: 'P003', name: 'Iced Tea',         category: 'DRINK',         price: 20000, is_active: true  },
    { id: 'P004', name: 'Cola',             category: 'DRINK',         price: 22000, is_active: true  },
    { id: 'P005', name: 'Couple Combo',     category: 'COMBO',         price: 75000, is_active: true  },
    { id: 'P006', name: 'Movie Poster',     category: 'MERCHANDISE',   price: 50000, is_active: true  },
    { id: 'P007', name: 'Legacy Snack',     category: 'FOOD',          price: 15000, is_active: false },
  ];

  function calcEndAt(startAt, durationMinutes) {
    var d = new Date(startAt);
    d.setMinutes(d.getMinutes() + durationMinutes);
    return d.toISOString();
  }

  var showtimes = [
    {
      id: 'SH001', movie: movies[0], studio: studios[0],
      start_at: '2026-05-26T13:00:00', duration_minutes: 112,
      end_at: calcEndAt('2026-05-26T13:00:00', 112),
      price: 45000, is_active: true,
    },
    {
      id: 'SH002', movie: movies[0], studio: studios[1],
      start_at: '2026-05-26T16:00:00', duration_minutes: 112,
      end_at: calcEndAt('2026-05-26T16:00:00', 112),
      price: 85000, is_active: true,
    },
    {
      id: 'SH003', movie: movies[1], studio: studios[2],
      start_at: '2026-05-26T14:00:00', duration_minutes: 128,
      end_at: calcEndAt('2026-05-26T14:00:00', 128),
      price: 120000, is_active: true,
    },
    {
      id: 'SH004', movie: movies[2], studio: studios[0],
      start_at: '2026-05-26T19:00:00', duration_minutes: 101,
      end_at: calcEndAt('2026-05-26T19:00:00', 101),
      price: 50000, is_active: true,
    },
    {
      id: 'SH005', movie: movies[3], studio: studios[1],
      start_at: '2026-05-26T11:00:00', duration_minutes: 95,
      end_at: calcEndAt('2026-05-26T11:00:00', 95),
      price: 90000, is_active: true,
    },
    {
      id: 'SH006', movie: movies[1], studio: studios[0],
      start_at: '2026-05-27T10:00:00', duration_minutes: 128,
      end_at: calcEndAt('2026-05-27T10:00:00', 128),
      price: 50000, is_active: false,
    },
  ];

  function mkTicket(id, code, seat, status, printedAt) {
    return { id: id, code: code, seat: seat, status: status, printed_at: printedAt || null };
  }
  function mkPayment(id, intId, gwId, amount, status, createdAt, paidAt, expiredAt, url) {
    return {
      id: id, internal_payment_id: intId, gateway_payment_id: gwId,
      amount: amount, status: status,
      created_at: createdAt, paid_at: paidAt || null, expired_at: expiredAt || null,
      payment_url: url || null,
    };
  }

  var s1 = studios[0].seats;
  var s2 = studios[1].seats;
  var s3 = studios[2].seats;

  var orders = [
    // 1. Pending online order
    {
      id: 'ORD001', number: 'SS-2026-0001', source: 'ONLINE',
      status: 'PENDING', customer_name: 'Andi Pratama',
      showtime: showtimes[0],
      tickets: [
        mkTicket('TKT001','TKT-A1B2C3', s1.find(function(s){return s.number==='A1';}), 'HELD'),
        mkTicket('TKT002','TKT-D4E5F6', s1.find(function(s){return s.number==='A2';}), 'HELD'),
      ],
      addons: [{ id:'AON001', product: products[0], quantity:2, unit_price:30000, total_price:60000 }],
      charges: [{ id:'CHG001', name:'Biaya Layanan', price:5000 }],
      payment: mkPayment('PAY001','PAY-INT-0001','PGW-0001',155000,'UNPAID','2026-05-26T09:30:00',null,'2026-05-26T09:45:00','/stub/payment-gateway/pay/PGW-0001'),
      total_amount: 155000, created_at: '2026-05-26T09:30:00',
    },
    // 2. Confirmed online order
    {
      id: 'ORD002', number: 'SS-2026-0002', source: 'ONLINE',
      status: 'CONFIRMED', customer_name: 'Budi Santoso',
      showtime: showtimes[1],
      tickets: [
        mkTicket('TKT003','TKT-G7H8I9', s2.find(function(s){return s.number==='B2';}), 'CONFIRMED'),
      ],
      addons: [{ id:'AON002', product: products[4], quantity:1, unit_price:75000, total_price:75000 }],
      charges: [{ id:'CHG002', name:'Biaya Layanan', price:5000 }],
      payment: mkPayment('PAY002','PAY-INT-0002','PGW-0002',165000,'PAID','2026-05-26T08:00:00','2026-05-26T08:05:00','2026-05-26T08:15:00','/stub/payment-gateway/pay/PGW-0002'),
      total_amount: 165000, created_at: '2026-05-26T08:00:00',
    },
    // 3. Printed ticket order
    {
      id: 'ORD003', number: 'SS-2026-0003', source: 'ONLINE',
      status: 'CONFIRMED', customer_name: 'Citra Dewi',
      showtime: showtimes[2],
      tickets: [
        mkTicket('TKT004','TKT-J1K2L3', s3.find(function(s){return s.number==='A3';}), 'PRINTED','2026-05-26T09:00:00'),
        mkTicket('TKT005','TKT-M4N5O6', s3.find(function(s){return s.number==='A4';}), 'PRINTED','2026-05-26T09:00:00'),
      ],
      addons: [],
      charges: [{ id:'CHG003', name:'Biaya Layanan', price:5000 }],
      payment: mkPayment('PAY003','PAY-INT-0003','PGW-0003',245000,'PAID','2026-05-26T08:30:00','2026-05-26T08:35:00','2026-05-26T08:45:00','/stub/payment-gateway/pay/PGW-0003'),
      total_amount: 245000, created_at: '2026-05-26T08:30:00',
    },
    // 4. Canceled paid order — refund pending
    {
      id: 'ORD004', number: 'SS-2026-0004', source: 'ONLINE',
      status: 'CANCELED', customer_name: 'Dian Permata',
      showtime: showtimes[3],
      tickets: [
        mkTicket('TKT006','TKT-P7Q8R9', s1.find(function(s){return s.number==='C3';}), 'CANCELED'),
      ],
      addons: [],
      charges: [{ id:'CHG004', name:'Biaya Layanan', price:5000 }],
      payment: mkPayment('PAY004','PAY-INT-0004','PGW-0004',55000,'REFUND_PENDING','2026-05-26T07:00:00','2026-05-26T07:05:00',null,'/stub/payment-gateway/pay/PGW-0004'),
      total_amount: 55000, created_at: '2026-05-26T07:00:00',
    },
    // 5. Expired online order
    {
      id: 'ORD005', number: 'SS-2026-0005', source: 'ONLINE',
      status: 'EXPIRED', customer_name: 'Eka Wahyu',
      showtime: showtimes[4],
      tickets: [
        mkTicket('TKT007','TKT-S1T2U3', s2.find(function(s){return s.number==='A1';}), 'EXPIRED'),
      ],
      addons: [],
      charges: [{ id:'CHG005', name:'Biaya Layanan', price:5000 }],
      payment: mkPayment('PAY005','PAY-INT-0005','PGW-0005',95000,'EXPIRED','2026-05-26T06:00:00',null,'2026-05-26T06:15:00','/stub/payment-gateway/pay/PGW-0005'),
      total_amount: 95000, created_at: '2026-05-26T06:00:00',
    },
    // 6. Onsite counter order
    {
      id: 'ORD006', number: 'SS-2026-0006', source: 'ONSITE',
      status: 'CONFIRMED', customer_name: 'Fajar Rizky',
      showtime: showtimes[0],
      tickets: [
        mkTicket('TKT008','TKT-V4W5X6', s1.find(function(s){return s.number==='D1';}), 'PRINTED','2026-05-26T09:45:00'),
      ],
      addons: [{ id:'AON003', product: products[2], quantity:2, unit_price:20000, total_price:40000 }],
      charges: [],
      payment: mkPayment('PAY006','PAY-INT-0006',null,85000,'PAID','2026-05-26T09:45:00','2026-05-26T09:45:00',null,null),
      total_amount: 85000, created_at: '2026-05-26T09:45:00',
    },
  ];

  var gatewayPayments = [
    { gateway_payment_id:'PGW-0001', internal_payment_id:'PAY-INT-0001', client_id:'SILVERSCREEN', amount:155000, issued_at:'2026-05-26T09:30:00', expiration_in:900, expired_at:'2026-05-26T09:45:00', status:'WAITING_PAYMENT' },
    { gateway_payment_id:'PGW-0002', internal_payment_id:'PAY-INT-0002', client_id:'SILVERSCREEN', amount:165000, issued_at:'2026-05-26T08:00:00', expiration_in:900, expired_at:'2026-05-26T08:15:00', status:'PAID' },
    { gateway_payment_id:'PGW-0003', internal_payment_id:'PAY-INT-0003', client_id:'SILVERSCREEN', amount:245000, issued_at:'2026-05-26T08:30:00', expiration_in:900, expired_at:'2026-05-26T08:45:00', status:'PAID' },
    { gateway_payment_id:'PGW-0004', internal_payment_id:'PAY-INT-0004', client_id:'SILVERSCREEN', amount:55000,  issued_at:'2026-05-26T07:00:00', expiration_in:900, expired_at:'2026-05-26T07:15:00', status:'PAID' },
    { gateway_payment_id:'PGW-0005', internal_payment_id:'PAY-INT-0005', client_id:'SILVERSCREEN', amount:95000,  issued_at:'2026-05-26T06:00:00', expiration_in:900, expired_at:'2026-05-26T06:15:00', status:'EXPIRED' },
  ];

  window.INITIAL_DATA = {
    movies: movies,
    studios: studios,
    studioTypes: studioTypes,
    products: products,
    showtimes: showtimes,
    orders: orders,
    gatewayPayments: gatewayPayments,
  };

  window.THEMES = ['Drama','Sci-Fi','Horror','Family','Documentary','Action','Romance','Thriller','Comedy','Animation'];
  window.AGE_RATINGS = ['ALL_AGE','R7','R13','R17','R21'];
  window.PRODUCT_CATEGORIES = ['FOOD','DRINK','COMBO','MERCHANDISE','OTHER'];
  window.STUDIO_TYPES = studioTypes;

  window.fmtCurrency = function(n) {
    return new Intl.NumberFormat('id-ID', { style:'currency', currency:'IDR', minimumFractionDigits:0 }).format(n);
  };
  window.fmtDate = function(d) {
    return new Date(d).toLocaleDateString('id-ID', { day:'numeric', month:'long', year:'numeric' });
  };
  window.fmtDateTime = function(d) {
    return new Date(d).toLocaleString('id-ID', { day:'numeric', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit' });
  };
  window.fmtTime = function(d) {
    return new Date(d).toLocaleTimeString('id-ID', { hour:'2-digit', minute:'2-digit' });
  };
  window.genId = (function() {
    var counter = 100;
    return function(prefix) { return (prefix || 'ID') + '-' + (++counter); };
  })();

})();
