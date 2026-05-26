/* ================================================
   SILVER SCREEN — Staff Counter View
   POS, Refund Queue, Order Lookup
   ================================================ */

/* ── Counter POS ─────────────────────────────────── */
function CounterPOS() {
  var { showtimes, products, orders, getOccupancy, createOnsiteOrder, fmtCurrency, fmtTime, fmtDate, navigate, addToast } = useApp();

  var [step, setStep]           = React.useState(0); // 0=select showtime, 1=select seats, 2=addons, 3=review, 4=done
  var [showtime, setShowtime]   = React.useState(null);
  var [seats, setSeats]         = React.useState([]);
  var [addons, setAddons]       = React.useState({});
  var [createdOrder, setCreatedOrder] = React.useState(null);
  var [printing, setPrinting]   = React.useState(false);
  var [ticketCount, setTicketCount] = React.useState(1);
  var [seatError, setSeatError] = React.useState('');

  var activeShowtimes = showtimes.filter(function(st){ return st.is_active; });
  var activeProducts  = products.filter(function(p){ return p.is_active; });
  var occupancy       = showtime ? getOccupancy(showtime.id) : {};

  var addonList    = Object.values(addons);
  var ticketTotal  = showtime ? showtime.price * seats.length : 0;
  var addonTotal   = addonList.reduce(function(s,a){ return s+a.total_price; }, 0);
  var grandTotal   = ticketTotal + addonTotal;

  function reset() {
    setStep(0); setShowtime(null); setSeats([]); setAddons({});
    setCreatedOrder(null); setTicketCount(1); setSeatError('');
  }

  function toggleSeat(seat) {
    setSeatError('');
    setSeats(function(prev){
      var idx = prev.findIndex(function(s){ return s.id === seat.id; });
      if (idx !== -1) return prev.filter(function(s){ return s.id !== seat.id; });
      if (prev.length >= ticketCount) { setSeatError('Sudah memilih ' + ticketCount + ' kursi sesuai jumlah tiket.'); return prev; }
      return prev.concat(seat);
    });
  }

  function setQty(product, qty) {
    setAddons(function(prev){
      if (qty <= 0) { var n = Object.assign({}, prev); delete n[product.id]; return n; }
      return Object.assign({}, prev, { [product.id]: { product:product, quantity:qty, unit_price:product.price, total_price:product.price*qty } });
    });
  }

  function handleCreateAndPrint() {
    setPrinting(true);
    setTimeout(function(){
      var order = createOnsiteOrder({ showtime:showtime, selectedSeats:seats, addons:addonList, customer_name:'Pelanggan Onsite' });
      setCreatedOrder(order);
      setPrinting(false);
      setStep(4);
    }, 800);
  }

  /* ─── DONE / Print View ─────────────────────── */
  if (step === 4 && createdOrder) {
    return (
      <div>
        <PageHeader title="Tiket Dicetak" subtitle={'Pesanan ' + createdOrder.number} />
        <div style={{ marginBottom:16 }}>
          <InfoBanner type="success">
            Pesanan berhasil dibuat. Order langsung CONFIRMED, tiket langsung PRINTED. Tidak ada status PENDING atau HELD untuk transaksi onsite.
          </InfoBanner>
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(440px,1fr))', gap:20 }}>
          {createdOrder.tickets.map(function(ticket){
            return <TicketPreviewCard key={ticket.id} ticket={ticket} order={createdOrder} />;
          })}
        </div>
        <div style={{ marginTop:20, display:'flex', gap:12 }}>
          <button className="button button-primary button-lg" onClick={reset}>
            <Icon name="plus" size={16} /> Transaksi Baru
          </button>
          <button className="button button-secondary" onClick={function(){ navigate('order-detail', { orderId:createdOrder.id }); }}>
            <Icon name="eye" size={14} /> Lihat Detail Pesanan
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Counter POS" subtitle="Buat tiket onsite untuk pelanggan walk-in" />
      <div style={{ marginBottom:16 }}>
        <InfoBanner type="warning">
          <strong>Prosedur Onsite:</strong> Konfirmasi pesanan dan terima pembayaran dari pelanggan terlebih dahulu. Sistem baru membuat order dan mencetak tiket setelah staf menekan "Buat &amp; Cetak Tiket".
        </InfoBanner>
      </div>
      <div className="pos-layout">
        {/* Left Panel */}
        <div className="pos-panel">
          {step === 0 && (
            <>
              <div className="pos-panel-header"><Icon name="calendar" size={14} />Pilih Jadwal Tayang</div>
              <div className="pos-panel-body">
                {activeShowtimes.length === 0
                  ? <EmptyState icon="calendar" title="Tidak ada jadwal aktif" />
                  : (
                    <div className="showtime-list">
                      {activeShowtimes.map(function(st){
                        var occ = getOccupancy(st.id);
                        var total = st.studio.seats.filter(function(s){ return s.is_active && !s.is_aisle; }).length;
                        var avail = total - Object.keys(occ).length;
                        var soldOut = avail === 0;
                        return (
                          <div key={st.id} className={'showtime-card' + (showtime && showtime.id===st.id?' selected':'') + (soldOut?' sold-out':'')}
                            onClick={soldOut ? null : function(){ setShowtime(st); setSeats([]); setTicketCount(1); }}>
                            <div>
                              <div className="showtime-time">{fmtTime(st.start_at)}</div>
                              <div className="showtime-end">{fmtDate(st.start_at)}</div>
                            </div>
                            <div className="showtime-divider"></div>
                            <div className="showtime-meta">
                              <div className="showtime-studio">{st.movie.title}</div>
                              <div className="showtime-type">{st.studio.name} — {st.studio.studio_type.name}</div>
                              {soldOut
                                ? <span style={{ fontSize:12, color:'var(--s-red)', fontWeight:700 }}>Habis</span>
                                : <span className="showtime-avail">{avail} kursi tersedia</span>
                              }
                            </div>
                            <div className="showtime-price">{fmtCurrency(st.price)}</div>
                          </div>
                        );
                      })}
                    </div>
                  )
                }
              </div>
              <div className="pos-panel-footer">
                <button className="button button-primary button-full" disabled={!showtime} onClick={function(){ setStep(1); }}>
                  Pilih Kursi <Icon name="arrowRight" size={14} />
                </button>
              </div>
            </>
          )}

          {step === 1 && showtime && (
            <>
              <div className="pos-panel-header">
                <button className="button-icon" style={{ border:'none', background:'transparent', marginRight:4, color:'var(--text-2)' }} onClick={function(){ setStep(0); setSeats([]); }}>
                  <Icon name="arrowLeft" size={14} />
                </button>
                <Icon name="seat" size={14} />
                Pilih Kursi — {showtime.studio.name}
                <div style={{ marginLeft:'auto', display:'flex', alignItems:'center', gap:8 }}>
                  <span style={{ fontSize:12 }}>Tiket:</span>
                  <div className="addon-counter">
                    <button className="addon-counter-btn" onClick={function(){ if(ticketCount>1){ setTicketCount(function(p){return p-1;}); setSeats(function(p){return p.slice(0,ticketCount-1);}); }}}>−</button>
                    <span className="addon-counter-val">{ticketCount}</span>
                    <button className="addon-counter-btn" onClick={function(){ if(ticketCount<10){ setTicketCount(function(p){return p+1;}); }}}>+</button>
                  </div>
                </div>
              </div>
              <div className="pos-panel-body">
                <SeatGrid studio={showtime.studio} occupancy={occupancy} selectedSeats={seats} onSeatClick={toggleSeat} />
                {seatError && <div className="form-error" style={{ marginTop:8 }}><Icon name="alertTriangle" size={13} />{seatError}</div>}
              </div>
              <div className="pos-panel-footer">
                <button className="button button-primary button-full" disabled={seats.length !== ticketCount} onClick={function(){ setStep(2); setSeatError(''); }}>
                  {seats.length}/{ticketCount} kursi — Lanjut Add-ons <Icon name="arrowRight" size={14} />
                </button>
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <div className="pos-panel-header">
                <button className="button-icon" style={{ border:'none', background:'transparent', marginRight:4, color:'var(--text-2)' }} onClick={function(){ setStep(1); }}>
                  <Icon name="arrowLeft" size={14} />
                </button>
                <Icon name="shoppingBag" size={14} />
                Tambah Add-ons (Opsional)
              </div>
              <div className="pos-panel-body">
                {activeProducts.length === 0
                  ? <EmptyState icon="package" title="Tidak ada produk aktif" />
                  : (
                    <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
                      {activeProducts.map(function(p){
                        var qty = addons[p.id] ? addons[p.id].quantity : 0;
                        return (
                          <div key={p.id} className="addon-card">
                            <div className="addon-card-info">
                              <div className="addon-card-name">{p.name}</div>
                              <div className="addon-card-meta">{fmtCurrency(p.price)} · {p.category}</div>
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
                  )
                }
              </div>
              <div className="pos-panel-footer">
                <button className="button button-primary button-full" onClick={function(){ setStep(3); }}>
                  Tinjau Pesanan <Icon name="arrowRight" size={14} />
                </button>
              </div>
            </>
          )}

          {step === 3 && showtime && (
            <>
              <div className="pos-panel-header">
                <button className="button-icon" style={{ border:'none', background:'transparent', marginRight:4, color:'var(--text-2)' }} onClick={function(){ setStep(2); }}>
                  <Icon name="arrowLeft" size={14} />
                </button>
                <Icon name="clipboardList" size={14} />
                Konfirmasi dengan Pelanggan
              </div>
              <div className="pos-panel-body">
                <InfoBanner type="warning">
                  Bacakan pesanan berikut kepada pelanggan. Terima pembayaran sebelum menekan tombol cetak.
                </InfoBanner>
                <div style={{ marginTop:16 }}>
                  <div className="order-summary-row"><span>Film</span><span style={{ fontWeight:700 }}>{showtime.movie.title}</span></div>
                  <div className="order-summary-row"><span>Studio</span><span>{showtime.studio.name} ({showtime.studio.studio_type.name})</span></div>
                  <div className="order-summary-row"><span>Tanggal</span><span>{fmtDate(showtime.start_at)}</span></div>
                  <div className="order-summary-row"><span>Jam</span><span>{fmtTime(showtime.start_at)} — {fmtTime(showtime.end_at)}</span></div>
                  <div className="order-summary-row"><span>Kursi</span>
                    <span style={{ display:'flex', gap:4, flexWrap:'wrap' }}>
                      {seats.map(function(s){ return <span key={s.id} className="tag font-bold">{s.number}</span>; })}
                    </span>
                  </div>
                  {addonList.length > 0 && (
                    <div style={{ marginTop:8 }}>
                      <div style={{ fontSize:12, color:'var(--text-3)', fontWeight:700, textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:6 }}>Add-ons</div>
                      {addonList.map(function(a){ return <div key={a.product.id} className="order-summary-row"><span>{a.product.name} x{a.quantity}</span><span>{fmtCurrency(a.total_price)}</span></div>; })}
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Right Panel — Order Summary */}
        <div className="pos-panel">
          <div className="pos-panel-header"><Icon name="ticket" size={14} />Ringkasan Pesanan</div>
          <div className="pos-panel-body">
            {!showtime ? (
              <div style={{ color:'var(--text-3)', fontSize:13, textAlign:'center', padding:'40px 0' }}>
                Pilih jadwal dan kursi terlebih dahulu
              </div>
            ) : (
              <div>
                <div style={{ padding:'12px', background:'var(--red-light)', borderRadius:'var(--r-md)', border:'1px solid var(--red-border)', marginBottom:16 }}>
                  <div style={{ fontWeight:700, fontSize:15 }}>{showtime.movie.title}</div>
                  <div style={{ fontSize:12, color:'var(--text-2)', marginTop:2 }}>{showtime.studio.name} · {fmtTime(showtime.start_at)} · {fmtDate(showtime.start_at)}</div>
                </div>
                <div className="order-summary-row"><span>Tiket ({seats.length}x)</span><span>{fmtCurrency(ticketTotal)}</span></div>
                {addonList.map(function(a){ return <div key={a.product.id} className="order-summary-row"><span>{a.product.name} x{a.quantity}</span><span>{fmtCurrency(a.total_price)}</span></div>; })}
                {seats.length > 0 && (
                  <div style={{ marginTop:8 }}>
                    <div style={{ fontSize:12, color:'var(--text-3)', marginBottom:6 }}>Kursi dipilih:</div>
                    <div style={{ display:'flex', gap:4, flexWrap:'wrap' }}>
                      {seats.map(function(s){ return <span key={s.id} className="status-badge badge-confirmed">{s.number}</span>; })}
                    </div>
                  </div>
                )}
                <div className="order-summary-total">
                  <span className="order-summary-total-label">Total</span>
                  <span className="order-summary-total-value">{fmtCurrency(grandTotal)}</span>
                </div>
                <div style={{ marginTop:12, padding:'10px', background:'var(--s-purple-bg)', border:'1px solid var(--s-purple-bg)', borderRadius:'var(--r-sm)', fontSize:12, color:'var(--s-purple-t)' }}>
                  <strong>Sumber: ONSITE</strong> — Tidak ada biaya layanan. Pembayaran diterima di kasir.
                </div>
              </div>
            )}
          </div>
          <div className="pos-panel-footer">
            {step === 3 && showtime && seats.length > 0 ? (
              <button className="button button-gold button-full button-lg" onClick={handleCreateAndPrint} disabled={printing}>
                {printing
                  ? <><Icon name="refreshCw" size={16} /> Memproses...</>
                  : <><Icon name="printer" size={16} /> Buat &amp; Cetak Tiket</>
                }
              </button>
            ) : (
              <button className="button button-secondary button-full" disabled>
                Selesaikan pilihan untuk mencetak
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Refund Queue ─────────────────────────────────── */
function RefundQueue() {
  var { orders, markRefundComplete, fmtCurrency, fmtDateTime, navigate, addToast } = useApp();
  var [confirmId, setConfirmId] = React.useState(null);

  var pendingRefunds   = orders.filter(function(o){ return o.payment.status === 'REFUND_PENDING'; });
  var completedRefunds = orders.filter(function(o){ return o.payment.status === 'REFUNDED'; });

  function handleConfirm() {
    markRefundComplete(confirmId);
    setConfirmId(null);
  }

  return (
    <div>
      {confirmId && (
        <ConfirmModal
          title="Tandai Refund Selesai"
          message="Konfirmasi bahwa refund telah diproses secara manual dan uang telah dikembalikan ke pelanggan."
          onConfirm={handleConfirm}
          onCancel={function(){ setConfirmId(null); }}
        />
      )}
      <PageHeader title="Antrian Refund" subtitle="Kelola refund untuk pesanan yang dibatalkan setelah pembayaran" />
      {pendingRefunds.length === 0 ? (
        <div style={{ marginBottom:24 }}>
          <EmptyState icon="checkCircle" title="Tidak ada refund yang menunggu" desc="Semua refund telah diproses." />
        </div>
      ) : (
        <div style={{ marginBottom:32 }}>
          <div className="section-title">Menunggu Diproses ({pendingRefunds.length})</div>
          <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
            {pendingRefunds.map(function(order){
              var pay = order.payment;
              return (
                <div key={order.id} className="card">
                  <div style={{ padding:'16px 20px', display:'grid', gridTemplateColumns:'1fr auto', gap:16, alignItems:'start' }}>
                    <div>
                      <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:6 }}>
                        <span className="font-mono font-bold" style={{ fontSize:14 }}>{order.number}</span>
                        <StatusBadge status={order.status} />
                        <StatusBadge status={pay.status} />
                      </div>
                      <div style={{ fontWeight:600, fontSize:15 }}>{order.showtime.movie.title}</div>
                      <div style={{ fontSize:12, color:'var(--text-3)', marginTop:2 }}>
                        {order.showtime.studio.name} · {window.fmtDateTime(order.showtime.start_at)}
                      </div>
                      <div style={{ fontSize:12, color:'var(--text-2)', marginTop:6 }}>
                        <span style={{ marginRight:12 }}>Pelanggan: <strong>{order.customer_name}</strong></span>
                        <span>Kursi: {order.tickets.map(function(t){ return t.seat.number; }).join(', ')}</span>
                      </div>
                      <div style={{ marginTop:8, fontSize:12, color:'var(--text-3)' }}>
                        Dibuat: {fmtDateTime(order.created_at)}
                        {pay.paid_at && <span style={{ marginLeft:12 }}>Dibayar: {fmtDateTime(pay.paid_at)}</span>}
                      </div>
                    </div>
                    <div style={{ textAlign:'right', display:'flex', flexDirection:'column', gap:10, alignItems:'flex-end' }}>
                      <div style={{ fontSize:20, fontWeight:800, color:'var(--red)' }}>{fmtCurrency(pay.amount)}</div>
                      <button className="button button-primary" onClick={function(){ setConfirmId(order.id); }}>
                        <Icon name="checkCircle" size={14} /> Tandai Refund Selesai
                      </button>
                      <button className="button button-ghost button-sm" onClick={function(){ navigate('order-detail', { orderId:order.id }); }}>
                        <Icon name="eye" size={12} /> Detail
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
      {completedRefunds.length > 0 && (
        <div>
          <div className="section-title">Selesai ({completedRefunds.length})</div>
          <div className="table-wrapper">
            <div className="card"><table>
              <thead><tr>
                <th>No. Pesanan</th><th>Pelanggan</th><th>Film</th><th>Jumlah</th><th>Status</th>
              </tr></thead>
              <tbody>
                {completedRefunds.map(function(o){
                  return (
                    <tr key={o.id} style={{ cursor:'pointer' }} onClick={function(){ navigate('order-detail', { orderId:o.id }); }}>
                      <td className="font-mono" style={{ fontWeight:600 }}>{o.number}</td>
                      <td>{o.customer_name}</td>
                      <td>{o.showtime.movie.title}</td>
                      <td style={{ fontWeight:700 }}>{fmtCurrency(o.payment.amount)}</td>
                      <td><StatusBadge status={o.payment.status} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table></div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Order Lookup ─────────────────────────────────── */
function OrderLookup() {
  var { orders, navigate, fmtCurrency, fmtDateTime } = useApp();
  var [query, setQuery] = React.useState('');
  var [filterStatus, setFilterStatus] = React.useState('');

  var statuses = ['PENDING','CONFIRMED','CANCELED','EXPIRED'];
  var results  = orders.filter(function(o){
    var q = query.trim().toLowerCase();
    if (q && !o.number.toLowerCase().includes(q) && !o.customer_name.toLowerCase().includes(q) && !o.showtime.movie.title.toLowerCase().includes(q)) return false;
    if (filterStatus && o.status !== filterStatus) return false;
    return true;
  });

  return (
    <div>
      <PageHeader title="Pencarian Pesanan" subtitle="Cari pesanan berdasarkan nomor, nama pelanggan, atau film" />
      <div className="filter-bar" style={{ marginBottom:20 }}>
        <div className="filter-search" style={{ flex:'1 1 300px' }}>
          <div className="filter-search-icon"><Icon name="search" size={15} /></div>
          <input className="form-control" placeholder="Cari no. pesanan, nama, atau film..." value={query} onChange={function(e){ setQuery(e.target.value); }} />
        </div>
        <div className="filter-chips">
          <button className={'filter-chip'+(filterStatus===''?' active':'')} onClick={function(){ setFilterStatus(''); }}>Semua</button>
          {statuses.map(function(s){ return <button key={s} className={'filter-chip'+(filterStatus===s?' active':'')} onClick={function(){ setFilterStatus(s===filterStatus?'':s); }}>{s}</button>; })}
        </div>
      </div>
      {results.length === 0 ? (
        <EmptyState icon="search" title="Tidak ada pesanan ditemukan" desc="Coba kata kunci lain." />
      ) : (
        <div className="card">
          <div className="table-wrapper">
            <table>
              <thead><tr>
                <th>No. Pesanan</th><th>Pelanggan</th><th>Film</th><th>Studio</th>
                <th>Sumber</th><th>Status Order</th><th>Pembayaran</th><th>Total</th><th></th>
              </tr></thead>
              <tbody>
                {results.map(function(o){
                  return (
                    <tr key={o.id}>
                      <td className="font-mono" style={{ fontWeight:600 }}>{o.number}</td>
                      <td>{o.customer_name}</td>
                      <td style={{ fontWeight:600 }}>{o.showtime.movie.title}</td>
                      <td>{o.showtime.studio.name}</td>
                      <td><SourceBadge source={o.source} /></td>
                      <td><StatusBadge status={o.status} /></td>
                      <td><StatusBadge status={o.payment.status} /></td>
                      <td style={{ fontWeight:700 }}>{fmtCurrency(o.total_amount)}</td>
                      <td>
                        <button className="button button-secondary button-sm" onClick={function(){ navigate('order-detail', { orderId:o.id }); }}>
                          <Icon name="eye" size={12} /> Detail
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Printed Ticket Preview ──────────────────────── */
function PrintedTicketView() {
  var { pageParams, orders, navigate } = useApp();
  var orderId  = pageParams.orderId;
  var ticketId = pageParams.ticketId;
  var order    = orders.find(function(o){ return o.id === orderId; });
  var ticket   = order && order.tickets.find(function(t){ return t.id === ticketId; });

  if (!order || !ticket) {
    return <EmptyState icon="ticket" title="Tiket tidak ditemukan" />;
  }

  return (
    <div>
      <PageHeader title="Preview Tiket" back onBack={function(){ navigate('order-lookup'); }} />
      <TicketPreviewCard ticket={ticket} order={order} />
    </div>
  );
}

Object.assign(window, { CounterPOS, RefundQueue, OrderLookup, PrintedTicketView });
