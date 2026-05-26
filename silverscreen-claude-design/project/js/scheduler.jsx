/* ================================================
   SILVER SCREEN — Scheduler View
   Showtime List, Create Showtime, Showtime Detail
   ================================================ */

/* ── Showtime List ───────────────────────────────── */
function SchedulerShowtimes() {
  var { showtimes, movies, studios, navigate, toggleShowtime, getShowtimeStats, fmtCurrency, fmtDateTime, fmtTime, addToast } = useApp();
  var [filterMovie,  setFilterMovie]  = React.useState('');
  var [filterActive, setFilterActive] = React.useState('all');
  var [confirmDisable, setConfirmDisable] = React.useState(null); // showtimeId
  var [blockMsg, setBlockMsg] = React.useState('');

  var filtered = showtimes.filter(function(st){
    if (filterMovie && st.movie.id !== filterMovie) return false;
    if (filterActive === 'active'   && !st.is_active) return false;
    if (filterActive === 'inactive' && st.is_active)  return false;
    return true;
  });

  function tryDisable(st) {
    var stats = getShowtimeStats(st.id);
    if (stats.held > 0 || stats.confirmed > 0 || stats.printed > 0) {
      setBlockMsg('Showtime "' + st.movie.title + '" tidak dapat dinonaktifkan karena sudah memiliki tiket aktif (Held: ' + stats.held + ', Confirmed: ' + stats.confirmed + ', Printed: ' + stats.printed + ').');
      return;
    }
    setConfirmDisable(st.id);
  }

  function handleDisable() {
    toggleShowtime(confirmDisable);
    addToast('Showtime berhasil dinonaktifkan', 'success');
    setConfirmDisable(null);
  }

  function handleEnable(stId) {
    toggleShowtime(stId);
    addToast('Showtime berhasil diaktifkan kembali', 'success');
  }

  return (
    <div>
      {confirmDisable && (
        <ConfirmModal
          title="Nonaktifkan Showtime"
          message="Showtime ini akan dinonaktifkan dan tidak akan muncul di halaman pemesanan pelanggan. Lanjutkan?"
          danger
          onConfirm={handleDisable}
          onCancel={function(){ setConfirmDisable(null); }}
        />
      )}
      {blockMsg && (
        <Modal title="Tidak Dapat Dinonaktifkan" onClose={function(){ setBlockMsg(''); }}
          actions={<button className="button button-primary" onClick={function(){ setBlockMsg(''); }}>Mengerti</button>}>
          <InfoBanner type="error">{blockMsg}</InfoBanner>
        </Modal>
      )}
      <PageHeader
        title="Daftar Showtime"
        subtitle="Kelola jadwal tayang seluruh studio"
        actions={
          <button className="button button-primary" onClick={function(){ navigate('create-showtime'); }}>
            <Icon name="plus" size={14} /> Jadwalkan Showtime
          </button>
        }
      />
      <div className="filter-bar">
        <select className="form-control" style={{ width:'auto', minWidth:180 }} value={filterMovie} onChange={function(e){ setFilterMovie(e.target.value); }}>
          <option value="">Semua Film</option>
          {movies.map(function(m){ return <option key={m.id} value={m.id}>{m.title}</option>; })}
        </select>
        <div className="filter-chips">
          {[['all','Semua'],['active','Aktif'],['inactive','Nonaktif']].map(function(opt){
            return <button key={opt[0]} className={'filter-chip'+(filterActive===opt[0]?' active':'')} onClick={function(){ setFilterActive(opt[0]); }}>{opt[1]}</button>;
          })}
        </div>
      </div>
      {filtered.length === 0
        ? <EmptyState icon="calendar" title="Tidak ada showtime" desc="Buat jadwal baru dengan tombol di atas." />
        : (
          <div className="card">
            <div className="table-wrapper">
              <table>
                <thead><tr>
                  <th>Film</th><th>Studio</th><th>Mulai</th><th>Selesai</th>
                  <th>Harga</th><th>Status</th><th>Tiket</th><th>Aksi</th>
                </tr></thead>
                <tbody>
                  {filtered.map(function(st){
                    var stats = getShowtimeStats(st.id);
                    return (
                      <tr key={st.id}>
                        <td>
                          <div style={{ fontWeight:600, fontSize:13 }}>{st.movie.title}</div>
                          <div style={{ fontSize:11, color:'var(--text-3)' }}>{st.movie.theme.name} · {st.movie.age_rating}</div>
                        </td>
                        <td>
                          <div style={{ fontWeight:600 }}>{st.studio.name}</div>
                          <div style={{ fontSize:11, color:'var(--text-3)' }}>{st.studio.studio_type.name}</div>
                        </td>
                        <td>
                          <div style={{ fontFamily:'var(--font-mono)', fontWeight:700 }}>{fmtTime(st.start_at)}</div>
                          <div style={{ fontSize:11, color:'var(--text-3)' }}>{window.fmtDate(st.start_at)}</div>
                        </td>
                        <td style={{ fontFamily:'var(--font-mono)', color:'var(--text-2)' }}>{fmtTime(st.end_at)}</td>
                        <td style={{ fontWeight:700, color:'var(--red)' }}>{fmtCurrency(st.price)}</td>
                        <td><StatusBadge status={st.is_active ? 'active' : 'inactive'} label={st.is_active ? 'Aktif' : 'Nonaktif'} /></td>
                        <td>
                          <div style={{ display:'flex', flexDirection:'column', gap:2, fontSize:12 }}>
                            {stats.held > 0     && <span style={{ color:'var(--s-amber)' }}>Held: {stats.held}</span>}
                            {stats.confirmed > 0 && <span style={{ color:'var(--s-green)' }}>Confirmed: {stats.confirmed}</span>}
                            {stats.printed > 0  && <span style={{ color:'var(--s-purple)' }}>Printed: {stats.printed}</span>}
                            {stats.held===0 && stats.confirmed===0 && stats.printed===0 && <span style={{ color:'var(--text-3)' }}>—</span>}
                          </div>
                        </td>
                        <td>
                          <div style={{ display:'flex', gap:4 }}>
                            <button className="button-icon" title="Detail" onClick={function(){ navigate('showtime-detail', { showtimeId:st.id }); }}>
                              <Icon name="eye" size={14} />
                            </button>
                            {st.is_active
                              ? <button className="button-icon" title="Nonaktifkan" onClick={function(){ tryDisable(st); }}
                                  style={{ color:'var(--s-red)', borderColor:'var(--s-red-bg)' }}>
                                  <Icon name="ban" size={14} />
                                </button>
                              : <button className="button-icon" title="Aktifkan kembali" onClick={function(){ handleEnable(st.id); }}
                                  style={{ color:'var(--s-green)', borderColor:'var(--s-green-bg)' }}>
                                  <Icon name="checkCircle" size={14} />
                                </button>
                            }
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )
      }
    </div>
  );
}

/* ── Create Showtime ─────────────────────────────── */
function CreateShowtime() {
  var { movies, studios, createShowtime, navigate, fmtCurrency } = useApp();
  var [form, setForm] = React.useState({ movie_id:'', studio_id:'', start_at:'', price:'' });
  var [errors, setErrors] = React.useState({});
  var [preview, setPreview] = React.useState(null);

  var activeMovies  = movies.filter(function(m){ return m.is_active; });
  var activeStudios = studios.filter(function(s){ return s.is_active; });

  var selMovie  = activeMovies.find(function(m){ return m.id === form.movie_id; }) || null;
  var selStudio = activeStudios.find(function(s){ return s.id === form.studio_id; }) || null;

  // Auto-calculate end_at preview
  var endAtPreview = React.useMemo(function(){
    if (!selMovie || !form.start_at) return '';
    var d = new Date(form.start_at);
    if (isNaN(d.getTime())) return '';
    d.setMinutes(d.getMinutes() + selMovie.runtime_minutes);
    return d.toISOString().slice(0,16).replace('T',' ');
  }, [selMovie, form.start_at]);

  function set(field, val) {
    setForm(function(prev){ return Object.assign({}, prev, { [field]:val }); });
    setErrors(function(prev){ var n=Object.assign({},prev); delete n[field]; return n; });
  }

  function validate() {
    var errs = {};
    if (!form.movie_id)   errs.movie_id   = 'Film wajib dipilih.';
    if (!form.studio_id)  errs.studio_id  = 'Studio wajib dipilih.';
    if (!form.start_at)   errs.start_at   = 'Waktu mulai wajib diisi.';
    if (!form.price)      errs.price      = 'Harga tiket wajib diisi.';
    else if (Number(form.price) <= 0) errs.price = 'Harga tiket harus lebih dari 0.';
    return errs;
  }

  function handleSubmit() {
    var errs = validate();
    if (Object.keys(errs).length > 0) { setErrors(errs); return; }
    createShowtime({
      movie:    selMovie,
      studio:   selStudio,
      start_at: form.start_at,
      price:    Number(form.price),
    });
    navigate('showtimes');
  }

  return (
    <div>
      <PageHeader title="Jadwalkan Showtime" subtitle="Buat jadwal tayang baru" back onBack={function(){ navigate('showtimes'); }} />
      <div style={{ display:'grid', gridTemplateColumns:'1fr 340px', gap:24 }}>
        <div className="card">
          <div className="card-header"><Icon name="calendar" size={15} /><div className="card-title">Detail Showtime</div></div>
          <div className="card-body" style={{ display:'flex', flexDirection:'column', gap:20 }}>
            <div className="form-group">
              <label className="form-label">Film <span className="required">*</span></label>
              <select className="form-control" value={form.movie_id} onChange={function(e){ set('movie_id', e.target.value); }}>
                <option value="">— Pilih Film —</option>
                {activeMovies.map(function(m){ return <option key={m.id} value={m.id}>{m.title} ({m.runtime_minutes} mnt)</option>; })}
              </select>
              {errors.movie_id && <div className="form-error"><Icon name="alertTriangle" size={12} />{errors.movie_id}</div>}
            </div>
            <div className="form-group">
              <label className="form-label">Studio <span className="required">*</span></label>
              <select className="form-control" value={form.studio_id} onChange={function(e){ set('studio_id', e.target.value); }}>
                <option value="">— Pilih Studio —</option>
                {activeStudios.map(function(s){ return <option key={s.id} value={s.id}>{s.name} ({s.studio_type.name} — {s.capacity} kursi)</option>; })}
              </select>
              {errors.studio_id && <div className="form-error"><Icon name="alertTriangle" size={12} />{errors.studio_id}</div>}
            </div>
            <div className="form-row form-row-2">
              <div className="form-group">
                <label className="form-label">Waktu Mulai <span className="required">*</span></label>
                <input type="datetime-local" className="form-control" value={form.start_at} onChange={function(e){ set('start_at', e.target.value); }} />
                {errors.start_at && <div className="form-error"><Icon name="alertTriangle" size={12} />{errors.start_at}</div>}
              </div>
              <div className="form-group">
                <label className="form-label">Harga Tiket (IDR) <span className="required">*</span></label>
                <input type="number" className="form-control" placeholder="cth. 50000" value={form.price} onChange={function(e){ set('price', e.target.value); }} min="0" />
                {errors.price && <div className="form-error"><Icon name="alertTriangle" size={12} />{errors.price}</div>}
              </div>
            </div>
            <div className="form-row form-row-2">
              <div className="form-group">
                <label className="form-label">Durasi (dari film)</label>
                <input className="form-control" value={selMovie ? selMovie.runtime_minutes + ' menit' : '— pilih film —'} disabled />
                <div className="form-hint">Durasi otomatis dari runtime film yang dipilih.</div>
              </div>
              <div className="form-group">
                <label className="form-label">Waktu Selesai (otomatis)</label>
                <input className="form-control" value={endAtPreview || '— isi waktu mulai —'} disabled />
                <div className="form-hint">Dihitung dari waktu mulai + durasi film.</div>
              </div>
            </div>
          </div>
          <div className="card-footer" style={{ display:'flex', justifyContent:'flex-end', gap:8 }}>
            <button className="button button-secondary" onClick={function(){ navigate('showtimes'); }}>Batal</button>
            <button className="button button-primary" onClick={handleSubmit}>
              <Icon name="checkCircle" size={14} /> Jadwalkan
            </button>
          </div>
        </div>
        <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
          <div className="card">
            <div className="card-header"><div className="card-title">Preview</div></div>
            <div className="card-body">
              {!selMovie && !selStudio && !form.start_at
                ? <div style={{ color:'var(--text-3)', fontSize:13 }}>Isi form untuk melihat preview</div>
                : (
                  <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
                    {selMovie && (
                      <>
                        <div className="order-summary-row"><span>Film</span><span style={{ fontWeight:700 }}>{selMovie.title}</span></div>
                        <div className="order-summary-row"><span>Genre</span><span>{selMovie.theme.name}</span></div>
                        <div className="order-summary-row"><span>Rating</span><StatusBadge status={selMovie.age_rating} label={selMovie.age_rating} /></div>
                        <div className="order-summary-row"><span>Durasi</span><span>{selMovie.runtime_minutes} menit</span></div>
                      </>
                    )}
                    {selStudio && (
                      <>
                        <div className="order-summary-row"><span>Studio</span><span>{selStudio.name}</span></div>
                        <div className="order-summary-row"><span>Tipe</span><span>{selStudio.studio_type.name}</span></div>
                        <div className="order-summary-row"><span>Kapasitas</span><span>{selStudio.capacity} kursi</span></div>
                      </>
                    )}
                    {endAtPreview && <div className="order-summary-row"><span>Selesai</span><span style={{ fontFamily:'var(--font-mono)', fontWeight:700 }}>{endAtPreview}</span></div>}
                    {form.price && Number(form.price) > 0 && (
                      <div className="order-summary-total" style={{ marginTop:8 }}>
                        <span>Harga Tiket</span>
                        <span style={{ color:'var(--red)', fontWeight:800, fontSize:18 }}>{fmtCurrency(Number(form.price))}</span>
                      </div>
                    )}
                  </div>
                )
              }
            </div>
          </div>
          <InfoBanner type="info">
            Waktu selesai dihitung otomatis dari waktu mulai + durasi film. Scheduler hanya perlu memasukkan waktu mulai dan harga tiket.
          </InfoBanner>
        </div>
      </div>
    </div>
  );
}

/* ── Showtime Detail ─────────────────────────────── */
function ShowtimeDetail() {
  var { pageParams, showtimes, orders, navigate, toggleShowtime, getShowtimeStats, fmtCurrency, fmtDateTime, fmtTime, addToast } = useApp();
  var [blockMsg, setBlockMsg] = React.useState('');
  var [confirmId, setConfirmId] = React.useState(null);
  var stId = pageParams.showtimeId;
  var st   = showtimes.find(function(s){ return s.id === stId; });
  if (!st) return <EmptyState icon="calendar" title="Showtime tidak ditemukan" />;

  var stats = getShowtimeStats(stId);
  var activeTickets = stats.held + stats.confirmed + stats.printed;

  var stOrders = orders.filter(function(o){ return o.showtime.id === stId; });

  function tryDisable() {
    if (activeTickets > 0) {
      setBlockMsg('Showtime tidak dapat dinonaktifkan karena sudah memiliki tiket aktif (Held: ' + stats.held + ', Confirmed: ' + stats.confirmed + ', Printed: ' + stats.printed + ').');
      return;
    }
    setConfirmId(stId);
  }

  return (
    <div>
      {blockMsg && (
        <Modal title="Tidak Dapat Dinonaktifkan" onClose={function(){ setBlockMsg(''); }}
          actions={<button className="button button-primary" onClick={function(){ setBlockMsg(''); }}>Mengerti</button>}>
          <InfoBanner type="error">{blockMsg}</InfoBanner>
        </Modal>
      )}
      {confirmId && (
        <ConfirmModal
          title={st.is_active ? 'Nonaktifkan Showtime' : 'Aktifkan Showtime'}
          message={st.is_active
            ? 'Showtime akan dinonaktifkan dan tidak muncul di pemesanan pelanggan.'
            : 'Showtime akan diaktifkan kembali dan muncul di pemesanan pelanggan.'}
          danger={st.is_active}
          onConfirm={function(){
            toggleShowtime(stId);
            addToast(st.is_active ? 'Showtime dinonaktifkan' : 'Showtime diaktifkan', 'success');
            setConfirmId(null);
          }}
          onCancel={function(){ setConfirmId(null); }}
        />
      )}
      <PageHeader
        title={st.movie.title}
        subtitle={'Detail Showtime — ' + st.id}
        back onBack={function(){ navigate('showtimes'); }}
        actions={
          <div style={{ display:'flex', gap:8 }}>
            {st.is_active
              ? <button className="button button-danger" onClick={tryDisable}><Icon name="ban" size={14} /> Nonaktifkan</button>
              : <button className="button button-primary" onClick={function(){ setConfirmId(stId); }}><Icon name="checkCircle" size={14} /> Aktifkan</button>
            }
          </div>
        }
      />
      {!st.is_active && (
        <div style={{ marginBottom:16 }}>
          <InfoBanner type="warning">Showtime ini nonaktif dan tidak muncul di halaman pemesanan pelanggan.</InfoBanner>
        </div>
      )}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:24 }}>
        <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
          <div className="card">
            <div className="card-header"><Icon name="film" size={15} /><div className="card-title">Film</div></div>
            <div className="card-body">
              <div className="order-summary-row"><span>Judul</span><span style={{ fontWeight:700 }}>{st.movie.title}</span></div>
              <div className="order-summary-row"><span>Genre</span><span>{st.movie.theme.name}</span></div>
              <div className="order-summary-row"><span>Rating</span><StatusBadge status={st.movie.age_rating} label={st.movie.age_rating} /></div>
              <div className="order-summary-row" style={{ border:'none' }}><span>Durasi</span><span>{st.movie.runtime_minutes} menit</span></div>
            </div>
          </div>
          <div className="card">
            <div className="card-header"><Icon name="layers" size={15} /><div className="card-title">Studio &amp; Jadwal</div></div>
            <div className="card-body">
              <div className="order-summary-row"><span>Studio</span><span>{st.studio.name}</span></div>
              <div className="order-summary-row"><span>Tipe</span><span>{st.studio.studio_type.name}</span></div>
              <div className="order-summary-row"><span>Kapasitas</span><span>{st.studio.capacity} kursi</span></div>
              <div className="order-summary-row"><span>Waktu Mulai</span><span style={{ fontFamily:'var(--font-mono)', fontWeight:700 }}>{fmtTime(st.start_at)}</span></div>
              <div className="order-summary-row"><span>Waktu Selesai</span><span style={{ fontFamily:'var(--font-mono)' }}>{fmtTime(st.end_at)}</span></div>
              <div className="order-summary-row"><span>Tanggal</span><span>{window.fmtDate(st.start_at)}</span></div>
              <div className="order-summary-row" style={{ border:'none' }}><span>Harga</span><span style={{ fontWeight:800, color:'var(--red)', fontSize:16 }}>{fmtCurrency(st.price)}</span></div>
            </div>
          </div>
        </div>
        <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
          <div style={{ display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:12 }}>
            <div className="stat-card">
              <div className="stat-label">Held</div>
              <div className="stat-value" style={{ color:'var(--s-amber)' }}>{stats.held}</div>
              <div className="stat-sub">Ditahan</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Confirmed</div>
              <div className="stat-value" style={{ color:'var(--s-green)' }}>{stats.confirmed}</div>
              <div className="stat-sub">Dikonfirmasi</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Printed</div>
              <div className="stat-value" style={{ color:'var(--s-purple)' }}>{stats.printed}</div>
              <div className="stat-sub">Tercetak</div>
            </div>
          </div>
          {activeTickets > 0 && (
            <InfoBanner type="warning">
              Showtime ini memiliki {activeTickets} tiket aktif. Tidak dapat dinonaktifkan sampai semua tiket aktif diselesaikan atau dibatalkan.
            </InfoBanner>
          )}
          <div className="card">
            <div className="card-header"><div className="card-title">Pesanan Terkait ({stOrders.length})</div></div>
            <div className="card-body" style={{ padding:0 }}>
              {stOrders.length === 0
                ? <div style={{ padding:16, color:'var(--text-3)', fontSize:13 }}>Belum ada pesanan</div>
                : stOrders.slice(0,8).map(function(o){
                    return (
                      <div key={o.id} style={{ display:'flex', alignItems:'center', gap:12, padding:'10px 16px', borderBottom:'1px solid var(--border-lt)' }}>
                        <span className="font-mono" style={{ fontSize:12, color:'var(--text-2)' }}>{o.number}</span>
                        <StatusBadge status={o.status} />
                        <span style={{ fontSize:12, color:'var(--text-3)', flex:1 }}>{o.tickets.length} tiket</span>
                        <button className="button-icon" onClick={function(){ navigate('order-detail', { orderId:o.id }); }}>
                          <Icon name="eye" size={13} />
                        </button>
                      </div>
                    );
                  })
              }
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { SchedulerShowtimes, CreateShowtime, ShowtimeDetail });
