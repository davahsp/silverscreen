/* ================================================
   SILVER SCREEN — Customer View
   Booking Flow (6 steps), My Orders, Order Detail, Ticket Print
   ================================================ */

/* ── Step 1: Movie List ──────────────────────────── */
function CustomerMovies() {
  var { movies, setBooking, navigate } = useApp();
  var [search,    setSearch]    = React.useState('');
  var [filterTheme, setTheme]   = React.useState('');
  var [filterAge,   setAge]     = React.useState('');

  var themes    = [...new Set(movies.map(function(m){ return m.theme && m.theme.name; }).filter(Boolean))];
  var ageRatings = window.AGE_RATINGS;

  var active = movies.filter(function(m) {
    if (!m.is_active) return false;
    if (search && !m.title.toLowerCase().includes(search.toLowerCase())) return false;
    if (filterTheme && m.theme && m.theme.name !== filterTheme) return false;
    if (filterAge && m.age_rating !== filterAge) return false;
    return true;
  });

  function selectMovie(movie) {
    setBooking({ step:1, movie:movie, showtime:null, ticketCount:1, seats:[], addons:{} });
    navigate('booking-showtime');
  }

  return (
    <div>
      <PageHeader
        title="Pilih Film"
        subtitle="Pilih film yang ingin Anda tonton"
        actions={
          <button className="button button-secondary" onClick={function(){ navigate('orders'); }}>
            <Icon name="clipboardList" size={14} /> Pesanan Saya
          </button>
        }
      />
      <div className="filter-bar">
        <div className="filter-search">
          <div className="filter-search-icon"><Icon name="search" size={15} /></div>
          <input className="form-control" placeholder="Cari judul film..." value={search} onChange={function(e){ setSearch(e.target.value); }} />
        </div>
        <div className="filter-chips">
          <button className={'filter-chip' + (!filterTheme ? ' active' : '')} onClick={function(){ setTheme(''); }}>Semua Genre</button>
          {themes.map(function(t){ return <button key={t} className={'filter-chip' + (filterTheme===t?' active':'')} onClick={function(){ setTheme(filterTheme===t?'':t); }}>{t}</button>; })}
        </div>
        <div className="filter-chips">
          {ageRatings.map(function(r){ return <button key={r} className={'filter-chip' + (filterAge===r?' active':'')} onClick={function(){ setAge(filterAge===r?'':r); }}>{r}</button>; })}
        </div>
      </div>
      {active.length === 0 ? (
        <EmptyState icon="film" title="Tidak ada film ditemukan" desc="Coba ubah filter pencarian Anda." />
      ) : (
        <div className="movie-grid">
          {active.map(function(movie) {
            return (
              <div key={movie.id} className="movie-card">
                <MoviePoster movie={movie} />
                <div className="movie-card-body">
                  <div className="movie-card-title">{movie.title}</div>
                  <div className="movie-card-meta">
                    <span className="tag">{movie.theme && movie.theme.name}</span>
                    <StatusBadge status={movie.age_rating} label={window.STATUS_LABELS[movie.age_rating] || movie.age_rating} />
                    <span className="tag"><Icon name="clock" size={11} />{movie.runtime_minutes} mnt</span>
                  </div>
                  <div className="movie-card-synopsis">{movie.synopsis}</div>
                </div>
                <div className="movie-card-footer">
                  <button className="button button-primary button-full" onClick={function(){ selectMovie(movie); }}>
                    <Icon name="ticket" size={14} /> Pilih Film
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
      {movies.some(function(m){ return !m.is_active; }) && (
        <div style={{ marginTop:24 }}>
          <div className="section-title">Film Tidak Aktif (Tidak Dapat Dipesan)</div>
          <div className="movie-grid">
            {movies.filter(function(m){ return !m.is_active; }).map(function(movie){
              return (
                <div key={movie.id} className="movie-card" style={{ opacity:0.5 }}>
                  <MoviePoster movie={movie} />
                  <div className="movie-card-body">
                    <div className="movie-card-title">{movie.title}</div>
                    <div className="movie-card-meta">
                      <span className="tag">{movie.theme && movie.theme.name}</span>
                      <StatusBadge status="inactive" label="Nonaktif" />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Step 2: Showtime Selection ──────────────────── */
function BookingShowtime() {
  var { booking, setBooking, navigate, showtimes, getOccupancy, fmtTime, fmtDate, fmtCurrency } = useApp();
  if (!booking) { navigate('movies'); return null; }
  var movie = booking.movie;

  var [synopsisExpanded, setSynopsisExpanded] = React.useState(false);
  var SYNOPSIS_LIMIT = 160;
  var synopsisLong = movie.synopsis.length > SYNOPSIS_LIMIT;

  var available = showtimes.filter(function(st) {
    return st.movie.id === movie.id && st.is_active;
  });

  function selectShowtime(st) {
    setBooking(function(prev){ return Object.assign({}, prev, { showtime:st, seats:[], ticketCount:1 }); });
    navigate('booking-seats');
  }

  function getAvailSeats(st) {
    var occ = getOccupancy(st.id);
    var total = st.studio.seats.filter(function(s){ return s.is_active && !s.is_aisle; }).length;
    var taken = Object.keys(occ).length;
    return total - taken;
  }

  return (
    <div>
      <PageHeader
        title="Pilih Jadwal"
        subtitle={movie.title + ' — ' + movie.runtime_minutes + ' menit'}
        back onBack={function(){ navigate('movies'); setBooking(null); }}
      />
      <Stepper steps={['Pilih Film','Pilih Jadwal','Pilih Kursi','Add-ons','Tinjau','Bayar']} current={1} />
      <div style={{ display:'flex', alignItems:'center', gap:12, marginBottom:20, padding:16, background:'var(--red-light)', borderRadius:'var(--r-md)', border:'1px solid var(--red-border)' }}>
        <MoviePoster movie={movie} height={80} />
        <div>
          <div style={{ fontWeight:700, fontSize:16 }}>{movie.title}</div>
          <div className="flex gap-2" style={{ marginTop:4 }}>
            <span className="tag">{movie.theme && movie.theme.name}</span>
            <StatusBadge status={movie.age_rating} label={movie.age_rating} />
            <span className="tag"><Icon name="clock" size={11} />{movie.runtime_minutes} mnt</span>
          </div>
        </div>
      </div>
      <div style={{ marginBottom: 20, padding: '14px 16px', border: '1px solid var(--border-lt)', borderRadius: 'var(--r-md)', background: 'var(--bg-card)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <Icon name="film" size={14} color="var(--red)" />
          <span style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-1)' }}>Sinopsis</span>
        </div>
        <p style={{ fontSize: 13.5, color: 'var(--text-2)', lineHeight: 1.7, margin: 0 }}>
          {synopsisLong && !synopsisExpanded
            ? movie.synopsis.slice(0, SYNOPSIS_LIMIT).trimEnd() + '…'
            : movie.synopsis
          }
        </p>
        {synopsisLong && (
          <button
            onClick={function(){ setSynopsisExpanded(function(e){ return !e; }); }}
            style={{ marginTop: 6, background: 'none', border: 'none', padding: 0, cursor: 'pointer', fontSize: 13, fontWeight: 700, color: 'var(--red)' }}
          >
            {synopsisExpanded ? 'Sembunyikan' : 'Lihat Selengkapnya'}
          </button>
        )}
        <div style={{ display: 'flex', gap: 6, marginTop: 10, flexWrap: 'wrap' }}>
          <span className="tag"><Icon name="clock" size={11} />{movie.runtime_minutes} menit</span>
          <span className="tag">{movie.theme && movie.theme.name}</span>
          <StatusBadge status={movie.age_rating} label={movie.age_rating} />
        </div>
      </div>

      {available.length === 0 ? (
        <EmptyState icon="calendar" title="Tidak ada jadwal tersedia" desc="Belum ada showtime aktif untuk film ini." />
      ) : (
        <div className="showtime-list">
          {available.map(function(st) {
            var avail = getAvailSeats(st);
            var soldOut = avail === 0;
            return (
              <div key={st.id} className={'showtime-card' + (soldOut ? ' sold-out' : '')} onClick={soldOut ? null : function(){ selectShowtime(st); }}>
                <div>
                  <div className="showtime-time">{fmtTime(st.start_at)}</div>
                  <div className="showtime-end">s/d {fmtTime(st.end_at)}</div>
                </div>
                <div className="showtime-divider"></div>
                <div className="showtime-meta">
                  <div className="showtime-studio">{st.studio.name}</div>
                  <div className="showtime-type">{st.studio.studio_type.name}</div>
                  <div style={{ fontSize:12, color:'var(--text-3)', marginTop:2 }}>{fmtDate(st.start_at)}</div>
                  {soldOut
                    ? <div style={{ fontSize:12, color:'var(--s-red)', fontWeight:700, marginTop:4 }}>Habis Terjual</div>
                    : <div className="showtime-avail">{avail} kursi tersedia</div>
                  }
                </div>
                <div className="showtime-price">{fmtCurrency(st.price)}</div>
                {!soldOut && <Icon name="arrowRight" size={16} color="var(--text-3)" />}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ── Step 3: Seat Selection ──────────────────────── */
function BookingSeats() {
  var { booking, setBooking, navigate, getOccupancy, fmtCurrency } = useApp();
  if (!booking || !booking.showtime) { navigate('movies'); return null; }
  var { movie, showtime } = booking;
  var [ticketCount, setTicketCount] = React.useState(booking.ticketCount || 1);
  var [seats, setSeats] = React.useState(booking.seats || []);
  var [error, setError] = React.useState('');

  var occupancy = getOccupancy(showtime.id);
  var maxSeats  = showtime.studio.seats.filter(function(s){ return s.is_active && !s.is_aisle && !occupancy[s.id]; }).length;

  function toggleSeat(seat) {
    setError('');
    setSeats(function(prev) {
      var idx = prev.findIndex(function(s){ return s.id === seat.id; });
      if (idx !== -1) return prev.filter(function(s){ return s.id !== seat.id; });
      if (prev.length >= ticketCount) { setError('Jumlah kursi dipilih sudah sesuai jumlah tiket.'); return prev; }
      return prev.concat(seat);
    });
  }

  function handleNext() {
    if (seats.length !== ticketCount) { setError('Jumlah kursi yang dipilih harus sesuai jumlah tiket (' + ticketCount + ' tiket, ' + seats.length + ' kursi dipilih).'); return; }
    setBooking(function(prev){ return Object.assign({}, prev, { ticketCount:ticketCount, seats:seats }); });
    navigate('booking-addons');
  }

  return (
    <div>
      <PageHeader
        title="Pilih Kursi"
        subtitle={showtime.studio.name + ' — ' + movie.title}
        back onBack={function(){ navigate('booking-showtime'); }}
      />
      <Stepper steps={['Pilih Film','Pilih Jadwal','Pilih Kursi','Add-ons','Tinjau','Bayar']} current={2} />
      <div style={{ display:'grid', gridTemplateColumns:'1fr 280px', gap:24 }}>
        <div className="card">
          <div className="card-header">
            <Icon name="seat" size={16} />
            <div className="card-title">Denah Kursi — {showtime.studio.name}</div>
            <div style={{ marginLeft:'auto', display:'flex', alignItems:'center', gap:8 }}>
              <span style={{ fontSize:13, color:'var(--text-2)' }}>Jumlah Tiket:</span>
              <div className="addon-counter">
                <button className="addon-counter-btn" onClick={function(){ if(ticketCount>1){ setTicketCount(function(p){return p-1;}); setSeats(function(p){return p.slice(0,ticketCount-1);}); }}}>−</button>
                <span className="addon-counter-val">{ticketCount}</span>
                <button className="addon-counter-btn" onClick={function(){ if(ticketCount<maxSeats && ticketCount<10){ setTicketCount(function(p){return p+1;}); }}}>+</button>
              </div>
            </div>
          </div>
          <div className="card-body">
            <SeatGrid studio={showtime.studio} occupancy={occupancy} selectedSeats={seats} onSeatClick={toggleSeat} />
          </div>
        </div>
        <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
          <div className="card">
            <div className="card-header"><div className="card-title">Kursi Dipilih</div></div>
            <div className="card-body">
              {seats.length === 0
                ? <div style={{ color:'var(--text-3)', fontSize:13 }}>Belum ada kursi dipilih</div>
                : <div style={{ display:'flex', flexWrap:'wrap', gap:6 }}>
                    {seats.map(function(s){ return <span key={s.id} className="status-badge badge-confirmed">{s.number}</span>; })}
                  </div>
              }
              <div style={{ marginTop:12, padding:'10px 0', borderTop:'1px solid var(--border-lt)' }}>
                <div className="order-summary-row">
                  <span>Jumlah tiket</span><span>{ticketCount}</span>
                </div>
                <div className="order-summary-row">
                  <span>Dipilih</span>
                  <span style={{ color: seats.length === ticketCount ? 'var(--s-green)' : 'var(--s-red)', fontWeight:700 }}>
                    {seats.length} / {ticketCount}
                  </span>
                </div>
                <div className="order-summary-row" style={{ border:'none' }}>
                  <span>Harga/kursi</span><span>{fmtCurrency(showtime.price)}</span>
                </div>
              </div>
              {error && <div className="form-error" style={{ marginTop:8 }}><Icon name="alertTriangle" size={13} />{error}</div>}
            </div>
          </div>
          <button className="button button-primary button-full button-lg" onClick={handleNext} disabled={seats.length !== ticketCount}>
            Lanjut ke Add-ons <Icon name="arrowRight" size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Step 4: Add-ons ─────────────────────────────── */
function BookingAddons() {
  var { booking, setBooking, navigate, products, fmtCurrency } = useApp();
  if (!booking) { navigate('movies'); return null; }
  var [addons, setAddons] = React.useState(booking.addons || {});
  var active = products.filter(function(p){ return p.is_active; });
  var cats   = [...new Set(active.map(function(p){ return p.category; }))];

  function setQty(product, qty) {
    setAddons(function(prev) {
      if (qty <= 0) {
        var next = Object.assign({}, prev);
        delete next[product.id];
        return next;
      }
      return Object.assign({}, prev, { [product.id]: { product:product, quantity:qty, unit_price:product.price, total_price:product.price*qty } });
    });
  }

  var total = Object.values(addons).reduce(function(s,a){ return s+a.total_price; }, 0);

  function handleNext() {
    setBooking(function(prev){ return Object.assign({}, prev, { addons: addons }); });
    navigate('booking-review');
  }

  return (
    <div>
      <PageHeader title="Tambah Add-ons" subtitle="Opsional — tambah makanan & minuman" back onBack={function(){ navigate('booking-seats'); }} />
      <Stepper steps={['Pilih Film','Pilih Jadwal','Pilih Kursi','Add-ons','Tinjau','Bayar']} current={3} />
      <div style={{ display:'grid', gridTemplateColumns:'1fr 280px', gap:24 }}>
        <div>
          {cats.map(function(cat) {
            var items = active.filter(function(p){ return p.category === cat; });
            return (
              <div key={cat} className="section">
                <div className="section-title">{cat}</div>
                <div className="addon-grid">
                  {items.map(function(p) {
                    var qty = addons[p.id] ? addons[p.id].quantity : 0;
                    return (
                      <div key={p.id} className="addon-card">
                        <div className="addon-card-info">
                          <div className="addon-card-name">{p.name}</div>
                          <div className="addon-card-meta">{fmtCurrency(p.price)}</div>
                        </div>
                        <div className="addon-counter">
                          <button className="addon-counter-btn" onClick={function(){ setQty(p, qty-1); }}>−</button>
                          <span className="addon-counter-val">{qty}</span>
                          <button className="addon-counter-btn" onClick={function(){ setQty(p, qty+1); }}>+</button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
        <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
          <div className="card">
            <div className="card-header"><div className="card-title">Add-ons Dipilih</div></div>
            <div className="card-body">
              {Object.values(addons).length === 0
                ? <div style={{ color:'var(--text-3)', fontSize:13 }}>Belum ada add-on</div>
                : Object.values(addons).map(function(a){
                    return (
                      <div key={a.product.id} className="order-summary-row">
                        <span>{a.product.name} x{a.quantity}</span>
                        <span>{fmtCurrency(a.total_price)}</span>
                      </div>
                    );
                  })
              }
              {total > 0 && (
                <div style={{ marginTop:8, paddingTop:8, borderTop:'2px solid var(--text-1)', display:'flex', justifyContent:'space-between', fontWeight:800 }}>
                  <span>Subtotal</span><span style={{ color:'var(--red)' }}>{fmtCurrency(total)}</span>
                </div>
              )}
            </div>
          </div>
          <button className="button button-primary button-full button-lg" onClick={handleNext}>
            Tinjau Pesanan <Icon name="arrowRight" size={16} />
          </button>
          <button className="button button-ghost button-full" onClick={handleNext}>
            Lewati Add-ons
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Step 5: Review Order ────────────────────────── */
function BookingReview() {
  var { booking, setBooking, navigate, createOnlineOrder, fmtCurrency, fmtTime, fmtDate } = useApp();
  if (!booking) { navigate('movies'); return null; }
  var { movie, showtime, ticketCount, seats, addons } = booking;
  var [name, setName]     = React.useState('');
  var [nameErr, setNameErr] = React.useState('');
  var [submitting, setSubmitting] = React.useState(false);

  var ticketTotal = showtime.price * seats.length;
  var addonList   = Object.values(addons);
  var addonTotal  = addonList.reduce(function(s,a){ return s+a.total_price; }, 0);
  var serviceCharge = 5000;
  var grandTotal  = ticketTotal + addonTotal + serviceCharge;

  function handleCreate() {
    if (!name.trim()) { setNameErr('Nama tidak boleh kosong.'); return; }
    setNameErr('');
    setSubmitting(true);
    setTimeout(function() {
      var order = createOnlineOrder({ showtime:showtime, selectedSeats:seats, addons:addonList, customer_name:name.trim() });
      setBooking(function(prev){ return Object.assign({}, prev, { createdOrderId: order.id }); });
      navigate('booking-payment', { orderId: order.id });
      setSubmitting(false);
    }, 600);
  }

  return (
    <div>
      <PageHeader title="Tinjau Pesanan" subtitle="Periksa kembali sebelum membuat pesanan" back onBack={function(){ navigate('booking-addons'); }} />
      <Stepper steps={['Pilih Film','Pilih Jadwal','Pilih Kursi','Add-ons','Tinjau','Bayar']} current={4} />
      <div style={{ display:'grid', gridTemplateColumns:'1fr 340px', gap:24 }}>
        <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
          <div className="card">
            <div className="card-header"><Icon name="film" size={15} /><div className="card-title">Detail Film &amp; Jadwal</div></div>
            <div className="card-body">
              <div className="order-summary-row"><span>Film</span><span style={{ fontWeight:700 }}>{movie.title}</span></div>
              <div className="order-summary-row"><span>Studio</span><span>{showtime.studio.name} ({showtime.studio.studio_type.name})</span></div>
              <div className="order-summary-row"><span>Tanggal</span><span>{fmtDate(showtime.start_at)}</span></div>
              <div className="order-summary-row"><span>Jam Tayang</span><span>{fmtTime(showtime.start_at)} — {fmtTime(showtime.end_at)}</span></div>
              <div className="order-summary-row" style={{ border:'none' }}><span>Kursi</span>
                <span style={{ display:'flex', gap:4, flexWrap:'wrap', justifyContent:'flex-end' }}>
                  {seats.map(function(s){ return <span key={s.id} className="tag font-bold">{s.number}</span>; })}
                </span>
              </div>
            </div>
          </div>
          {addonList.length > 0 && (
            <div className="card">
              <div className="card-header"><Icon name="shoppingBag" size={15} /><div className="card-title">Add-ons</div></div>
              <div className="card-body">
                {addonList.map(function(a){
                  return <div key={a.product.id} className="order-summary-row"><span>{a.product.name} x{a.quantity}</span><span>{fmtCurrency(a.total_price)}</span></div>;
                })}
              </div>
            </div>
          )}
          <div className="card">
            <div className="card-header"><Icon name="user" size={15} /><div className="card-title">Data Pemesan</div></div>
            <div className="card-body">
              <div className="form-group">
                <label className="form-label">Nama Pemesan <span className="required">*</span></label>
                <input className="form-control" placeholder="Masukkan nama lengkap Anda" value={name} onChange={function(e){ setName(e.target.value); setNameErr(''); }} />
                {nameErr && <div className="form-error"><Icon name="alertTriangle" size={12} />{nameErr}</div>}
              </div>
            </div>
          </div>
        </div>
        <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
          <div className="card">
            <div className="card-header"><div className="card-title">Ringkasan Biaya</div></div>
            <div className="card-body">
              <div className="order-summary-row"><span>Tiket ({seats.length}x)</span><span>{fmtCurrency(ticketTotal)}</span></div>
              {addonList.length > 0 && <div className="order-summary-row"><span>Add-ons</span><span>{fmtCurrency(addonTotal)}</span></div>}
              <div className="order-summary-row"><span>Biaya Layanan</span><span>{fmtCurrency(serviceCharge)}</span></div>
              <div className="order-summary-total">
                <span className="order-summary-total-label">Total</span>
                <span className="order-summary-total-value">{fmtCurrency(grandTotal)}</span>
              </div>
            </div>
          </div>
          <InfoBanner type="info">
            Setelah menekan "Buat Pesanan", Anda akan diarahkan ke halaman pembayaran. Kursi akan ditahan selama 15 menit.
          </InfoBanner>
          <button className="button button-primary button-full button-lg" onClick={handleCreate} disabled={submitting}>
            {submitting ? 'Memproses...' : 'Buat Pesanan'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Step 6: Payment Info ────────────────────────── */
function BookingPayment() {
  var { pageParams, orders, navigate, fmtCurrency, fmtDateTime } = useApp();
  var orderId = pageParams.orderId;
  var order   = orders.find(function(o){ return o.id === orderId; });
  if (!order) { navigate('orders'); return null; }
  var pay = order.payment;

  return (
    <div>
      <PageHeader title="Pembayaran" subtitle={'Pesanan ' + order.number + ' berhasil dibuat'} />
      <Stepper steps={['Pilih Film','Pilih Jadwal','Pilih Kursi','Add-ons','Tinjau','Bayar']} current={5} />
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:24 }}>
        <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
          <div className="card">
            <div className="card-header">
              <Icon name="checkCircle" size={16} color="var(--s-green)" />
              <div className="card-title">Pesanan Berhasil Dibuat</div>
            </div>
            <div className="card-body">
              <div className="order-summary-row"><span>No. Pesanan</span><span className="font-mono" style={{ fontWeight:700 }}>{order.number}</span></div>
              <div className="order-summary-row"><span>Status Order</span><StatusBadge status={order.status} /></div>
              <div className="order-summary-row"><span>Status Tiket</span><StatusBadge status={order.tickets[0] && order.tickets[0].status} /></div>
              <div className="order-summary-row" style={{ border:'none' }}><span>Total</span><span style={{ fontWeight:800, color:'var(--red)', fontSize:16 }}>{fmtCurrency(order.total_amount)}</span></div>
            </div>
          </div>
          <div className="card">
            <div className="card-header"><Icon name="creditCard" size={15} /><div className="card-title">Internal Payment</div></div>
            <div className="card-body">
              <div className="order-summary-row"><span>Internal Payment ID</span><span className="font-mono">{pay.internal_payment_id}</span></div>
              <div className="order-summary-row"><span>Gateway Payment ID</span><span className="font-mono">{pay.gateway_payment_id}</span></div>
              <div className="order-summary-row"><span>Status Pembayaran</span><StatusBadge status={pay.status} /></div>
              <div className="order-summary-row"><span>Batas Bayar</span><span style={{ color:'var(--s-orange)', fontWeight:600 }}>{fmtDateTime(pay.expired_at)}</span></div>
              <div className="order-summary-row" style={{ border:'none' }}><span>Payment URL</span><span className="font-mono" style={{ fontSize:11, color:'var(--text-3)' }}>{pay.payment_url}</span></div>
            </div>
          </div>
        </div>
        <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
          <div style={{ padding:20, background:'linear-gradient(135deg, #0f172a, #1e293b)', borderRadius:'var(--r-lg)', color:'white' }}>
            <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:12 }}>
              <Icon name="externalLink" size={16} color="#94a3b8" />
              <span style={{ color:'#94a3b8', fontSize:13 }}>Stub Payment Gateway</span>
            </div>
            <div style={{ fontSize:15, fontWeight:600, marginBottom:8, lineHeight:1.5 }}>
              Lanjutkan ke halaman pembayaran untuk menyelesaikan transaksi.
            </div>
            <div style={{ fontSize:12, color:'#64748b', marginBottom:16 }}>
              Halaman payment gateway adalah lingkungan stub terpisah yang mensimulasikan penyedia pembayaran eksternal.
            </div>
            <button
              className="button button-primary button-full"
              style={{ background:'#3b82f6', borderColor:'#3b82f6', padding:'12px 20px', fontSize:15 }}
              onClick={function(){ navigate('gateway', { gatewayPaymentId: pay.gateway_payment_id }); }}
            >
              <Icon name="externalLink" size={16} /> Buka Stub Payment Gateway
            </button>
          </div>
          <InfoBanner type="warning">
            Kursi Anda ditahan hingga {fmtDateTime(pay.expired_at)}. Segera selesaikan pembayaran.
          </InfoBanner>
          <button className="button button-secondary button-full" onClick={function(){ navigate('orders'); }}>
            Lihat Semua Pesanan
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── My Orders ───────────────────────────────────── */
function CustomerOrders() {
  var { orders, navigate, fmtCurrency, fmtDateTime } = useApp();
  var myOrders = orders.filter(function(o){ return o.source === 'ONLINE'; });

  return (
    <div>
      <PageHeader title="Pesanan Saya" subtitle="Riwayat pesanan online Anda" actions={
        <button className="button button-primary" onClick={function(){ navigate('movies'); }}>
          <Icon name="plus" size={14} /> Pesan Baru
        </button>
      } />
      {myOrders.length === 0
        ? <EmptyState icon="clipboardList" title="Belum ada pesanan" desc="Buat pesanan online pertama Anda." action={<button className="button button-primary" onClick={function(){ navigate('movies'); }}>Pesan Sekarang</button>} />
        : (
          <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
            {myOrders.map(function(order) {
              var pay = order.payment;
              return (
                <div key={order.id} className="card" style={{ cursor:'pointer' }} onClick={function(){ navigate('order-detail', { orderId:order.id }); }}>
                  <div style={{ padding:'16px 20px', display:'flex', alignItems:'center', gap:16 }}>
                    <div style={{ flex:1 }}>
                      <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:4 }}>
                        <span className="font-mono" style={{ fontWeight:700, fontSize:14 }}>{order.number}</span>
                        <StatusBadge status={order.status} />
                        <SourceBadge source={order.source} />
                      </div>
                      <div style={{ fontSize:14, fontWeight:600 }}>{order.showtime.movie.title}</div>
                      <div style={{ fontSize:12, color:'var(--text-3)' }}>
                        {order.showtime.studio.name} · {window.fmtDateTime(order.showtime.start_at)} · {order.tickets.length} tiket
                      </div>
                    </div>
                    <div style={{ textAlign:'right' }}>
                      <div style={{ fontWeight:800, fontSize:16, color:'var(--red)' }}>{fmtCurrency(order.total_amount)}</div>
                      <StatusBadge status={pay.status} />
                      <div style={{ fontSize:11, color:'var(--text-3)', marginTop:4 }}>{fmtDateTime(order.created_at)}</div>
                    </div>
                    <Icon name="arrowRight" size={16} color="var(--text-3)" />
                  </div>
                </div>
              );
            })}
          </div>
        )
      }
    </div>
  );
}

/* ── Order Detail ────────────────────────────────── */
function OrderDetail() {
  var { pageParams, orders, navigate, cancelOrder, printAllTickets, printTicket, fmtCurrency, fmtDateTime, fmtTime, fmtDate } = useApp();
  var [confirmCancel, setConfirmCancel] = React.useState(false);
  var [printView, setPrintView]         = React.useState(null); // ticketId
  var orderId = pageParams.orderId;
  var order   = orders.find(function(o){ return o.id === orderId; });
  if (!order) return <div style={{ padding:32 }}><EmptyState icon="xCircle" title="Pesanan tidak ditemukan" /></div>;

  var pay      = order.payment;
  var hasPrinted = order.tickets.some(function(t){ return t.status === 'PRINTED'; });
  var canCancel  = (order.status === 'PENDING' || order.status === 'CONFIRMED') && !hasPrinted;
  var canPrint   = order.status === 'CONFIRMED';
  var confirmedTickets = order.tickets.filter(function(t){ return t.status === 'CONFIRMED'; });

  if (printView) {
    var tkt = order.tickets.find(function(t){ return t.id === printView; });
    return (
      <div>
        <PageHeader title="Tiket" subtitle={'Kode: ' + (tkt && tkt.code)} back onBack={function(){ setPrintView(null); }} />
        {tkt && <TicketPreviewCard ticket={tkt} order={order} />}
        <div style={{ textAlign:'center', marginTop:16 }}>
          <button className="button button-primary" onClick={function(){ printTicket(orderId, tkt.id); }}>
            <Icon name="printer" size={14} /> Cetak Tiket
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      {confirmCancel && (
        <ConfirmModal
          title="Batalkan Pesanan"
          message={pay.status === 'PAID'
            ? 'Pembayaran sudah diterima. Pesanan ini akan dibatalkan dan pembayaran akan masuk antrian refund (REFUND_PENDING). Lanjutkan?'
            : 'Pesanan akan dibatalkan dan kursi dilepas. Lanjutkan?'
          }
          danger
          onConfirm={function(){ cancelOrder(orderId); setConfirmCancel(false); }}
          onCancel={function(){ setConfirmCancel(false); }}
        />
      )}
      <PageHeader
        title={'Pesanan ' + order.number}
        subtitle={order.showtime.movie.title}
        back onBack={function(){ navigate('orders'); }}
        actions={
          <div style={{ display:'flex', gap:8 }}>
            {order.source === 'ONLINE' && pay.gateway_payment_id && order.status === 'PENDING' && (
              <button className="button button-secondary" onClick={function(){ navigate('gateway', { gatewayPaymentId: pay.gateway_payment_id }); }}>
                <Icon name="externalLink" size={14} /> Buka Payment Gateway
              </button>
            )}
            {canCancel && (
              <button className="button button-danger" onClick={function(){ setConfirmCancel(true); }}>
                <Icon name="ban" size={14} /> Batalkan Pesanan
              </button>
            )}
          </div>
        }
      />
      {hasPrinted && (
        <InfoBanner type="error" style={{ marginBottom:16 }}>
          Tiket sudah dicetak — pesanan tidak dapat dibatalkan.
        </InfoBanner>
      )}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:24 }}>
        <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
          <div className="card">
            <div className="card-header"><Icon name="clipboardList" size={15} /><div className="card-title">Detail Pesanan</div></div>
            <div className="card-body">
              <div className="order-summary-row"><span>No. Pesanan</span><span className="font-mono font-bold">{order.number}</span></div>
              <div className="order-summary-row"><span>Sumber</span><SourceBadge source={order.source} /></div>
              <div className="order-summary-row"><span>Status Order</span><StatusBadge status={order.status} /></div>
              <div className="order-summary-row"><span>Pelanggan</span><span>{order.customer_name}</span></div>
              <div className="order-summary-row"><span>Dibuat</span><span>{fmtDateTime(order.created_at)}</span></div>
              <div className="order-summary-row"><span>Film</span><span style={{ fontWeight:600 }}>{order.showtime.movie.title}</span></div>
              <div className="order-summary-row"><span>Studio</span><span>{order.showtime.studio.name}</span></div>
              <div className="order-summary-row"><span>Tanggal Tayang</span><span>{fmtDate(order.showtime.start_at)}</span></div>
              <div className="order-summary-row" style={{ border:'none' }}><span>Jam</span><span>{fmtTime(order.showtime.start_at)} — {fmtTime(order.showtime.end_at)}</span></div>
            </div>
          </div>
          <div className="card">
            <div className="card-header"><Icon name="creditCard" size={15} /><div className="card-title">Pembayaran</div></div>
            <div className="card-body">
              <div className="order-summary-row"><span>Internal ID</span><span className="font-mono">{pay.internal_payment_id}</span></div>
              {pay.gateway_payment_id && <div className="order-summary-row"><span>Gateway ID</span><span className="font-mono">{pay.gateway_payment_id}</span></div>}
              <div className="order-summary-row"><span>Status</span><StatusBadge status={pay.status} /></div>
              <div className="order-summary-row"><span>Jumlah</span><span style={{ fontWeight:800, color:'var(--red)' }}>{fmtCurrency(pay.amount)}</span></div>
              {pay.paid_at && <div className="order-summary-row"><span>Dibayar</span><span>{fmtDateTime(pay.paid_at)}</span></div>}
              {pay.expired_at && pay.status === 'UNPAID' && <div className="order-summary-row"><span>Batas Bayar</span><span style={{ color:'var(--s-orange)' }}>{fmtDateTime(pay.expired_at)}</span></div>}
            </div>
          </div>
        </div>
        <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
          <div className="card">
            <div className="card-header"><Icon name="ticket" size={15} /><div className="card-title">Tiket ({order.tickets.length})</div></div>
            <div className="card-body">
              {order.tickets.map(function(t) {
                return (
                  <div key={t.id} style={{ display:'flex', alignItems:'center', gap:12, padding:'10px 0', borderBottom:'1px solid var(--border-lt)' }}>
                    <span className="ticket-seat-badge" style={{ fontSize:16, padding:'4px 10px' }}>{t.seat.number}</span>
                    <div style={{ flex:1 }}>
                      <div className="font-mono" style={{ fontSize:12, color:'var(--text-2)' }}>{t.code}</div>
                      {t.printed_at && <div style={{ fontSize:11, color:'var(--text-3)' }}>Dicetak: {fmtDateTime(t.printed_at)}</div>}
                    </div>
                    <StatusBadge status={t.status} />
                    {(t.status === 'CONFIRMED' || t.status === 'PRINTED') && (
                      <button className="button button-secondary button-sm" onClick={function(){ setPrintView(t.id); }}>
                        <Icon name="eye" size={12} /> Lihat
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
            {confirmedTickets.length > 0 && (
              <div className="card-footer">
                <button className="button button-primary button-full" onClick={function(){ printAllTickets(orderId); }}>
                  <Icon name="printer" size={14} /> Cetak Semua Tiket
                </button>
              </div>
            )}
          </div>
          {order.addons.length > 0 && (
            <div className="card">
              <div className="card-header"><Icon name="shoppingBag" size={15} /><div className="card-title">Add-ons</div></div>
              <div className="card-body">
                {order.addons.map(function(a){ return <div key={a.id} className="order-summary-row"><span>{a.product.name} x{a.quantity}</span><span>{fmtCurrency(a.total_price)}</span></div>; })}
              </div>
            </div>
          )}
          <div className="card">
            <div className="card-header"><div className="card-title">Total Biaya</div></div>
            <div className="card-body">
              <div className="order-summary-row"><span>Tiket ({order.tickets.length}x)</span><span>{fmtCurrency(order.showtime.price * order.tickets.length)}</span></div>
              {order.addons.map(function(a){ return <div key={a.id} className="order-summary-row"><span>{a.product.name}</span><span>{fmtCurrency(a.total_price)}</span></div>; })}
              {order.charges.map(function(c){ return <div key={c.id} className="order-summary-row"><span>{c.name}</span><span>{fmtCurrency(c.price)}</span></div>; })}
              <div className="order-summary-total">
                <span className="order-summary-total-label">Total</span>
                <span className="order-summary-total-value">{fmtCurrency(order.total_amount)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { CustomerMovies, BookingShowtime, BookingSeats, BookingAddons, BookingReview, BookingPayment, CustomerOrders, OrderDetail });
