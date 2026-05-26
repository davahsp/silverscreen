/* ================================================
   SILVER SCREEN — Manager View
   Dashboard, Movie Management, Product Catalog,
   Studio Management, Studio Seat Layout Builder
   ================================================ */

/* ── Manager Dashboard ───────────────────────────── */
function ManagerDashboard() {
  var { movies, studios, products, showtimes, orders, fmtCurrency } = useApp();

  var totalRevenue    = orders.filter(function(o){ return o.payment.status === 'PAID' || o.payment.status === 'REFUND_PENDING' || o.payment.status === 'REFUNDED'; })
                              .reduce(function(s,o){ return s + o.total_amount; }, 0);
  var confirmedOrders = orders.filter(function(o){ return o.status === 'CONFIRMED'; }).length;
  var pendingRefunds  = orders.filter(function(o){ return o.payment.status === 'REFUND_PENDING'; }).length;
  var totalTickets    = orders.reduce(function(s,o){ return s + o.tickets.filter(function(t){ return t.status === 'PRINTED' || t.status === 'CONFIRMED'; }).length; }, 0);

  var recentOrders = orders.slice(0, 5);

  return (
    <div>
      <PageHeader title="Dashboard Manajer" subtitle="Ringkasan operasional Silver Screen" />
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Pendapatan</div>
          <div className="stat-value" style={{ fontSize:22, color:'var(--red)' }}>{fmtCurrency(totalRevenue)}</div>
          <div className="stat-sub">Dari pesanan lunas</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Pesanan Aktif</div>
          <div className="stat-value">{confirmedOrders}</div>
          <div className="stat-sub">Status CONFIRMED</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Tiket Aktif</div>
          <div className="stat-value">{totalTickets}</div>
          <div className="stat-sub">Confirmed + Printed</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Antrian Refund</div>
          <div className="stat-value" style={{ color: pendingRefunds > 0 ? 'var(--s-orange)' : 'var(--s-green)' }}>{pendingRefunds}</div>
          <div className="stat-sub">REFUND_PENDING</div>
        </div>
      </div>
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:24 }}>
        <div className="card">
          <div className="card-header"><div className="card-title">Pesanan Terbaru</div></div>
          <div className="table-wrapper">
            <table>
              <thead><tr><th>No. Pesanan</th><th>Film</th><th>Status</th><th>Total</th></tr></thead>
              <tbody>
                {recentOrders.map(function(o){
                  return (
                    <tr key={o.id}>
                      <td className="font-mono" style={{ fontSize:12 }}>{o.number}</td>
                      <td style={{ fontSize:13 }}>{o.showtime.movie.title}</td>
                      <td><StatusBadge status={o.status} /></td>
                      <td style={{ fontWeight:700 }}>{fmtCurrency(o.total_amount)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
        <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
          <div className="card">
            <div className="card-header"><div className="card-title">Ringkasan Katalog</div></div>
            <div className="card-body">
              <div className="order-summary-row"><span>Film Aktif</span><span style={{ fontWeight:700, color:'var(--s-green)' }}>{movies.filter(function(m){return m.is_active;}).length}</span></div>
              <div className="order-summary-row"><span>Film Nonaktif</span><span style={{ color:'var(--text-3)' }}>{movies.filter(function(m){return !m.is_active;}).length}</span></div>
              <div className="order-summary-row"><span>Studio Aktif</span><span style={{ fontWeight:700, color:'var(--s-green)' }}>{studios.filter(function(s){return s.is_active;}).length}</span></div>
              <div className="order-summary-row"><span>Showtime Aktif</span><span style={{ fontWeight:700 }}>{showtimes.filter(function(s){return s.is_active;}).length}</span></div>
              <div className="order-summary-row" style={{ border:'none' }}><span>Produk Aktif</span><span style={{ fontWeight:700 }}>{products.filter(function(p){return p.is_active;}).length}</span></div>
            </div>
          </div>
          <div className="card">
            <div className="card-header"><div className="card-title">Distribusi Pesanan</div></div>
            <div className="card-body">
              {['PENDING','CONFIRMED','CANCELED','EXPIRED'].map(function(s){
                var count = orders.filter(function(o){ return o.status === s; }).length;
                return (
                  <div key={s} style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8 }}>
                    <StatusBadge status={s} />
                    <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                      <div style={{ width:80, height:6, background:'var(--border-lt)', borderRadius:3, overflow:'hidden' }}>
                        <div style={{ height:'100%', width: (count/orders.length*100)+'%', background:'var(--red)', borderRadius:3 }}></div>
                      </div>
                      <span style={{ fontWeight:700, fontSize:13, minWidth:20 }}>{count}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Movie Form (shared Add/Edit) ────────────────── */
function MovieForm({ initial, onSave, onCancel }) {
  var [form, setForm] = React.useState(initial || { title:'', synopsis:'', age_rating:'', runtime_minutes:'', theme_name:'', is_active:true });
  var [errors, setErrors] = React.useState({});

  function set(f, v) { setForm(function(p){ return Object.assign({},p,{[f]:v}); }); setErrors(function(p){ var n=Object.assign({},p); delete n[f]; return n; }); }

  function validate() {
    var e = {};
    if (!form.title.trim())       e.title      = 'Judul film wajib diisi.';
    if (!form.synopsis.trim())    e.synopsis   = 'Sinopsis wajib diisi.';
    if (!form.age_rating)         e.age_rating = 'Rating usia wajib dipilih.';
    if (!form.theme_name)         e.theme_name = 'Tema film wajib dipilih.';
    if (!form.runtime_minutes)    e.runtime    = 'Durasi wajib diisi.';
    else if (Number(form.runtime_minutes) <= 0) e.runtime = 'Durasi harus lebih dari 0 menit.';
    return e;
  }

  function handleSave() {
    var e = validate();
    if (Object.keys(e).length > 0) { setErrors(e); return; }
    onSave({
      title:           form.title.trim(),
      synopsis:        form.synopsis.trim(),
      age_rating:      form.age_rating,
      runtime_minutes: Number(form.runtime_minutes),
      is_active:       form.is_active,
      theme:           { id:'T-'+Date.now(), name: form.theme_name },
    });
  }

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:18 }}>
      <div className="form-group">
        <label className="form-label">Judul Film <span className="required">*</span></label>
        <input className="form-control" placeholder="Judul film" value={form.title} onChange={function(e){ set('title',e.target.value); }} />
        {errors.title && <div className="form-error"><Icon name="alertTriangle" size={12}/>{errors.title}</div>}
      </div>
      <div className="form-group">
        <label className="form-label">Sinopsis <span className="required">*</span></label>
        <textarea className="form-control" rows={4} style={{ resize:'vertical' }} placeholder="Deskripsi singkat film..." value={form.synopsis} onChange={function(e){ set('synopsis',e.target.value); }} />
        {errors.synopsis && <div className="form-error"><Icon name="alertTriangle" size={12}/>{errors.synopsis}</div>}
      </div>
      <div className="form-row form-row-3">
        <div className="form-group">
          <label className="form-label">Rating Usia <span className="required">*</span></label>
          <select className="form-control" value={form.age_rating} onChange={function(e){ set('age_rating',e.target.value); }}>
            <option value="">— Pilih —</option>
            {window.AGE_RATINGS.map(function(r){ return <option key={r} value={r}>{r}</option>; })}
          </select>
          {errors.age_rating && <div className="form-error"><Icon name="alertTriangle" size={12}/>{errors.age_rating}</div>}
        </div>
        <div className="form-group">
          <label className="form-label">Tema <span className="required">*</span></label>
          <select className="form-control" value={form.theme_name} onChange={function(e){ set('theme_name',e.target.value); }}>
            <option value="">— Pilih —</option>
            {window.THEMES.map(function(t){ return <option key={t} value={t}>{t}</option>; })}
          </select>
          {errors.theme_name && <div className="form-error"><Icon name="alertTriangle" size={12}/>{errors.theme_name}</div>}
        </div>
        <div className="form-group">
          <label className="form-label">Durasi (menit) <span className="required">*</span></label>
          <input type="number" className="form-control" placeholder="cth. 120" min="1" value={form.runtime_minutes} onChange={function(e){ set('runtime_minutes',e.target.value); }} />
          {errors.runtime && <div className="form-error"><Icon name="alertTriangle" size={12}/>{errors.runtime}</div>}
        </div>
      </div>
      <div className="form-group">
        <label className="form-label" style={{ display:'flex', alignItems:'center', gap:8, cursor:'pointer' }}>
          <input type="checkbox" checked={form.is_active} onChange={function(e){ set('is_active',e.target.checked); }} />
          Film aktif (tampil di pemesanan pelanggan)
        </label>
      </div>
      <div style={{ display:'flex', gap:8, justifyContent:'flex-end', paddingTop:8 }}>
        <button className="button button-secondary" onClick={onCancel}>Batal</button>
        <button className="button button-primary" onClick={handleSave}><Icon name="check" size={14} /> Simpan</button>
      </div>
    </div>
  );
}

/* ── Movie Management ────────────────────────────── */
function MovieManagement() {
  var { movies, addMovie, updateMovie, fmtCurrency } = useApp();
  var [modal, setModal] = React.useState(null); // null | 'add' | { movie }
  var [search, setSearch] = React.useState('');

  var filtered = movies.filter(function(m){ return !search || m.title.toLowerCase().includes(search.toLowerCase()); });

  function handleSave(data) {
    if (modal === 'add') addMovie(data);
    else updateMovie(modal.movie.id, data);
    setModal(null);
  }

  var editInitial = modal && modal !== 'add' ? {
    title: modal.movie.title, synopsis: modal.movie.synopsis,
    age_rating: modal.movie.age_rating, runtime_minutes: modal.movie.runtime_minutes,
    theme_name: modal.movie.theme && modal.movie.theme.name, is_active: modal.movie.is_active,
  } : null;

  return (
    <div>
      {modal && (
        <Modal title={modal === 'add' ? 'Tambah Film' : 'Edit Film'} onClose={function(){ setModal(null); }} size="lg">
          <MovieForm initial={editInitial} onSave={handleSave} onCancel={function(){ setModal(null); }} />
        </Modal>
      )}
      <PageHeader title="Kelola Film" subtitle="Tambah, edit, dan kelola daftar film" actions={
        <button className="button button-primary" onClick={function(){ setModal('add'); }}>
          <Icon name="plus" size={14} /> Tambah Film
        </button>
      } />
      <div className="filter-bar">
        <div className="filter-search" style={{ flex:'1 1 280px' }}>
          <div className="filter-search-icon"><Icon name="search" size={15} /></div>
          <input className="form-control" placeholder="Cari film..." value={search} onChange={function(e){ setSearch(e.target.value); }} />
        </div>
      </div>
      <div className="card">
        <div className="table-wrapper">
          <table>
            <thead><tr><th>Film</th><th>Genre</th><th>Rating</th><th>Durasi</th><th>Status</th><th>Aksi</th></tr></thead>
            <tbody>
              {filtered.map(function(m){
                return (
                  <tr key={m.id}>
                    <td>
                      <div style={{ fontWeight:700 }}>{m.title}</div>
                      <div style={{ fontSize:11, color:'var(--text-3)', maxWidth:280, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{m.synopsis}</div>
                    </td>
                    <td>{m.theme && m.theme.name}</td>
                    <td><StatusBadge status={m.age_rating} label={m.age_rating} /></td>
                    <td>{m.runtime_minutes} mnt</td>
                    <td><StatusBadge status={m.is_active ? 'active' : 'inactive'} label={m.is_active ? 'Aktif' : 'Nonaktif'} /></td>
                    <td>
                      <button className="button-icon" onClick={function(){ setModal({ movie:m }); }}>
                        <Icon name="edit" size={14} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ── Product Catalog ─────────────────────────────── */
function ProductCatalog() {
  var { products, addProduct, updateProduct, fmtCurrency } = useApp();
  var [modal, setModal] = React.useState(null);
  var [filterCat, setFilterCat] = React.useState('');

  var filtered = products.filter(function(p){ return !filterCat || p.category === filterCat; });

  function handleSave(data) {
    if (modal === 'add') addProduct(data);
    else updateProduct(modal.product.id, data);
    setModal(null);
  }

  return (
    <div>
      {modal && (
        <Modal title={modal === 'add' ? 'Tambah Produk' : 'Edit Produk'} onClose={function(){ setModal(null); }}>
          <ProductForm
            initial={modal !== 'add' ? modal.product : null}
            onSave={handleSave}
            onCancel={function(){ setModal(null); }}
          />
        </Modal>
      )}
      <PageHeader title="Katalog Produk" subtitle="Kelola produk add-on yang tersedia" actions={
        <button className="button button-primary" onClick={function(){ setModal('add'); }}>
          <Icon name="plus" size={14} /> Tambah Produk
        </button>
      } />
      <div className="filter-bar">
        <div className="filter-chips">
          <button className={'filter-chip'+(filterCat===''?' active':'')} onClick={function(){ setFilterCat(''); }}>Semua</button>
          {window.PRODUCT_CATEGORIES.map(function(c){ return <button key={c} className={'filter-chip'+(filterCat===c?' active':'')} onClick={function(){ setFilterCat(c===filterCat?'':c); }}>{c}</button>; })}
        </div>
      </div>
      <div className="card">
        <div className="table-wrapper">
          <table>
            <thead><tr><th>Nama Produk</th><th>Kategori</th><th>Harga</th><th>Status</th><th>Aksi</th></tr></thead>
            <tbody>
              {filtered.map(function(p){
                return (
                  <tr key={p.id} style={{ opacity: p.is_active ? 1 : 0.55 }}>
                    <td style={{ fontWeight:600 }}>{p.name}</td>
                    <td><span className="tag">{p.category}</span></td>
                    <td style={{ fontWeight:700, color:'var(--red)' }}>{fmtCurrency(p.price)}</td>
                    <td><StatusBadge status={p.is_active ? 'active' : 'inactive'} label={p.is_active ? 'Aktif' : 'Nonaktif'} /></td>
                    <td>
                      <button className="button-icon" onClick={function(){ setModal({ product:p }); }}>
                        <Icon name="edit" size={14} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function ProductForm({ initial, onSave, onCancel }) {
  var [form, setForm] = React.useState(initial ? { name:initial.name, price:initial.price, category:initial.category, is_active:initial.is_active } : { name:'', price:'', category:'', is_active:true });
  var [errors, setErrors] = React.useState({});
  function set(f,v){ setForm(function(p){ return Object.assign({},p,{[f]:v}); }); setErrors(function(p){ var n=Object.assign({},p); delete n[f]; return n; }); }
  function validate() {
    var e = {};
    if (!form.name.trim())  e.name     = 'Nama produk wajib diisi.';
    if (!form.category)     e.category = 'Kategori wajib dipilih.';
    if (!form.price)        e.price    = 'Harga wajib diisi.';
    else if (Number(form.price)<=0) e.price = 'Harga harus lebih dari 0.';
    return e;
  }
  function handleSave() {
    var e = validate();
    if (Object.keys(e).length>0){ setErrors(e); return; }
    onSave({ name:form.name.trim(), price:Number(form.price), category:form.category, is_active:form.is_active });
  }
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
      <div className="form-group">
        <label className="form-label">Nama Produk <span className="required">*</span></label>
        <input className="form-control" value={form.name} onChange={function(e){ set('name',e.target.value); }} />
        {errors.name && <div className="form-error"><Icon name="alertTriangle" size={12}/>{errors.name}</div>}
      </div>
      <div className="form-row form-row-2">
        <div className="form-group">
          <label className="form-label">Harga (IDR) <span className="required">*</span></label>
          <input type="number" className="form-control" min="0" value={form.price} onChange={function(e){ set('price',e.target.value); }} />
          {errors.price && <div className="form-error"><Icon name="alertTriangle" size={12}/>{errors.price}</div>}
        </div>
        <div className="form-group">
          <label className="form-label">Kategori <span className="required">*</span></label>
          <select className="form-control" value={form.category} onChange={function(e){ set('category',e.target.value); }}>
            <option value="">— Pilih —</option>
            {window.PRODUCT_CATEGORIES.map(function(c){ return <option key={c} value={c}>{c}</option>; })}
          </select>
          {errors.category && <div className="form-error"><Icon name="alertTriangle" size={12}/>{errors.category}</div>}
        </div>
      </div>
      <div className="form-group">
        <label className="form-label" style={{ display:'flex', alignItems:'center', gap:8, cursor:'pointer' }}>
          <input type="checkbox" checked={form.is_active} onChange={function(e){ set('is_active',e.target.checked); }} />
          Produk aktif (tampil di pemesanan)
        </label>
      </div>
      <div style={{ display:'flex', gap:8, justifyContent:'flex-end' }}>
        <button className="button button-secondary" onClick={onCancel}>Batal</button>
        <button className="button button-primary" onClick={handleSave}><Icon name="check" size={14} /> Simpan</button>
      </div>
    </div>
  );
}

/* ── Studio Management ───────────────────────────── */
function StudioManagement() {
  var { studios, navigate } = useApp();
  return (
    <div>
      <PageHeader title="Kelola Studio" subtitle="Daftar studio dan konfigurasi kursi" actions={
        <button className="button button-primary" onClick={function(){ navigate('studio-builder'); }}>
          <Icon name="plus" size={14} /> Tambah Studio
        </button>
      } />
      <div className="card">
        <div className="table-wrapper">
          <table>
            <thead><tr><th>Studio</th><th>Tipe</th><th>Grid</th><th>Kapasitas</th><th>Status</th><th>Aksi</th></tr></thead>
            <tbody>
              {studios.map(function(s){
                var activeSeatCount = s.seats.filter(function(seat){ return !seat.is_aisle && seat.is_active; }).length;
                return (
                  <tr key={s.id}>
                    <td style={{ fontWeight:700 }}>{s.name}</td>
                    <td><span className="tag">{s.studio_type.name}</span></td>
                    <td style={{ fontFamily:'var(--font-mono)', color:'var(--text-2)' }}>{s.grid_y_pos}R × {s.grid_x_pos}K</td>
                    <td>
                      <span style={{ fontWeight:700 }}>{activeSeatCount}</span>
                      <span style={{ color:'var(--text-3)', fontSize:12 }}> kursi aktif</span>
                    </td>
                    <td><StatusBadge status={s.is_active ? 'active':'inactive'} label={s.is_active?'Aktif':'Nonaktif'} /></td>
                    <td>
                      <button className="button button-secondary button-sm" onClick={function(){ navigate('studio-builder', { studioId:s.id }); }}>
                        <Icon name="grid" size={12} /> Layout Kursi
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ── Studio Seat Layout Builder ──────────────────── */
function StudioLayoutBuilder() {
  var { studios, addStudio, navigate, addToast } = useApp();
  var [phase, setPhase] = React.useState('config'); // 'config' | 'grid'
  var [config, setConfig] = React.useState({ name:'', studio_type_id:'ST001', rows:6, cols:8 });
  var [configErrors, setConfigErrors] = React.useState({});
  var [cells, setCells] = React.useState(null); // null until grid phase
  var [saved, setSaved] = React.useState(false);

  var ROW_LABELS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

  function setConfig_(f,v){ setConfig(function(p){ return Object.assign({},p,{[f]:v}); }); setConfigErrors(function(p){ var n=Object.assign({},p); delete n[f]; return n; }); }

  function initGrid() {
    var errs = {};
    if (!config.name.trim()) errs.name = 'Nama studio wajib diisi.';
    if (!config.studio_type_id) errs.type = 'Tipe studio wajib dipilih.';
    if (!config.rows || config.rows < 1 || config.rows > 20) errs.rows = 'Baris harus antara 1–20.';
    if (!config.cols || config.cols < 1 || config.cols > 20) errs.cols = 'Kolom harus antara 1–20.';
    if (Object.keys(errs).length > 0) { setConfigErrors(errs); return; }

    var rows = Number(config.rows);
    var cols = Number(config.cols);
    var grid = [];
    for (var r=0; r<rows; r++) {
      var row = [];
      for (var c=0; c<cols; c++) row.push(true); // true = seat, false = aisle
      grid.push(row);
    }
    setCells(grid);
    setPhase('grid');
  }

  function toggleCell(r, c) {
    setCells(function(prev){
      return prev.map(function(row, ri){
        if (ri !== r) return row;
        return row.map(function(cell, ci){ return ci===c ? !cell : cell; });
      });
    });
  }

  var seatCount = React.useMemo(function(){
    if (!cells) return 0;
    return cells.reduce(function(total, row){ return total + row.filter(Boolean).length; }, 0);
  }, [cells]);

  function handleSave() {
    if (seatCount === 0) { addToast('Pilih minimal satu kursi.', 'error'); return; }
    var stType = window.STUDIO_TYPES.find(function(t){ return t.id === config.studio_type_id; }) || window.STUDIO_TYPES[0];
    var rows = cells.length;
    var cols = cells[0].length;
    var seats = [];
    for (var r=0; r<rows; r++) {
      for (var c=0; c<cols; c++) {
        var isAisle = !cells[r][c];
        seats.push({
          id:         'NEW-' + ROW_LABELS[r] + (c+1),
          studio_id:  'NEW',
          number:     ROW_LABELS[r] + (c+1),
          row:        ROW_LABELS[r],
          grid_x_pos: c,
          grid_y_pos: r,
          is_active:  !isAisle,
          is_aisle:   isAisle,
        });
      }
    }
    addStudio({
      name:          config.name.trim(),
      studio_type:   stType,
      grid_x_pos:    cols,
      grid_y_pos:    rows,
      seats:         seats,
    });
    setSaved(true);
  }

  if (saved) {
    return (
      <div>
        <PageHeader title="Studio Berhasil Dibuat" />
        <div style={{ maxWidth:480 }}>
          <div className="card">
            <div className="card-body" style={{ textAlign:'center', padding:40 }}>
              <div style={{ marginBottom:16 }}><Icon name="checkCircle" size={48} color="var(--s-green)" /></div>
              <div style={{ fontSize:18, fontWeight:700, marginBottom:8 }}>{config.name} berhasil dibuat</div>
              <div style={{ fontSize:14, color:'var(--text-2)', marginBottom:24 }}>{seatCount} kursi aktif telah dikonfigurasi.</div>
              <div style={{ display:'flex', gap:12, justifyContent:'center' }}>
                <button className="button button-primary" onClick={function(){ navigate('studios'); }}>
                  <Icon name="layers" size={14} /> Kelola Studio
                </button>
                <button className="button button-secondary" onClick={function(){ setPhase('config'); setCells(null); setSaved(false); setConfig({name:'',studio_type_id:'ST001',rows:6,cols:8}); }}>
                  <Icon name="plus" size={14} /> Tambah Studio Lagi
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Layout Builder Studio" subtitle="Konfigurasi studio dan denah kursi" back onBack={function(){ if(phase==='grid'){ setPhase('config'); }else{ navigate('studios'); } }} />
      {phase === 'config' && (
        <div style={{ maxWidth:640 }}>
          <div className="card">
            <div className="card-header"><Icon name="settings" size={15} /><div className="card-title">Konfigurasi Dasar</div></div>
            <div className="card-body" style={{ display:'flex', flexDirection:'column', gap:20 }}>
              <div className="form-group">
                <label className="form-label">Nama Studio <span className="required">*</span></label>
                <input className="form-control" placeholder="cth. Studio 4" value={config.name} onChange={function(e){ setConfig_('name',e.target.value); }} />
                {configErrors.name && <div className="form-error"><Icon name="alertTriangle" size={12}/>{configErrors.name}</div>}
              </div>
              <div className="form-group">
                <label className="form-label">Tipe Studio <span className="required">*</span></label>
                <select className="form-control" value={config.studio_type_id} onChange={function(e){ setConfig_('studio_type_id',e.target.value); }}>
                  {window.STUDIO_TYPES.map(function(t){ return <option key={t.id} value={t.id}>{t.name} (Harga Dasar: {window.fmtCurrency(t.base_price)})</option>; })}
                </select>
                {configErrors.type && <div className="form-error"><Icon name="alertTriangle" size={12}/>{configErrors.type}</div>}
              </div>
              <div className="form-row form-row-2">
                <div className="form-group">
                  <label className="form-label">Jumlah Baris (1–20) <span className="required">*</span></label>
                  <input type="number" className="form-control" min="1" max="20" value={config.rows} onChange={function(e){ setConfig_('rows',Number(e.target.value)); }} />
                  {configErrors.rows && <div className="form-error"><Icon name="alertTriangle" size={12}/>{configErrors.rows}</div>}
                </div>
                <div className="form-group">
                  <label className="form-label">Jumlah Kolom (1–20) <span className="required">*</span></label>
                  <input type="number" className="form-control" min="1" max="20" value={config.cols} onChange={function(e){ setConfig_('cols',Number(e.target.value)); }} />
                  {configErrors.cols && <div className="form-error"><Icon name="alertTriangle" size={12}/>{configErrors.cols}</div>}
                </div>
              </div>
              <InfoBanner type="info">
                Setelah menentukan konfigurasi, Anda akan masuk ke halaman Grid Builder untuk memilih kursi aktif dan lorong.
              </InfoBanner>
            </div>
            <div className="card-footer" style={{ display:'flex', justifyContent:'flex-end', gap:8 }}>
              <button className="button button-secondary" onClick={function(){ navigate('studios'); }}>Batal</button>
              <button className="button button-primary" onClick={initGrid}>
                Lanjut ke Layout Kursi <Icon name="arrowRight" size={14} />
              </button>
            </div>
          </div>
        </div>
      )}
      {phase === 'grid' && cells && (
        <div style={{ display:'grid', gridTemplateColumns:'1fr 300px', gap:24 }}>
          <div className="card">
            <div className="card-header">
              <Icon name="grid" size={15} />
              <div>
                <div className="card-title">Grid Builder — {config.name}</div>
                <div className="card-subtitle">Klik sel untuk toggle antara Kursi dan Lorong</div>
              </div>
            </div>
            <div className="card-body">
              <div style={{ overflowX:'auto' }}>
                <div className="seat-screen" style={{ maxWidth:'fit-content', margin:'0 auto 16px' }}>— Layar / Depan —</div>
                <div style={{ display:'flex', flexDirection:'column', gap:5, alignItems:'center' }}>
                  {cells.map(function(row, r){
                    return (
                      <div key={r} style={{ display:'flex', alignItems:'center', gap:5 }}>
                        <span style={{ width:24, fontSize:12, fontWeight:700, color:'var(--text-3)', textAlign:'center', fontFamily:'var(--font-mono)' }}>
                          {ROW_LABELS[r]}
                        </span>
                        {row.map(function(isSeat, c){
                          return (
                            <button
                              key={c}
                              className={'builder-grid-cell ' + (isSeat ? 'is-seat' : 'is-aisle')}
                              title={(isSeat ? 'Kursi ' : 'Lorong ') + ROW_LABELS[r] + (c+1)}
                              onClick={function(){ toggleCell(r, c); }}
                            >
                              {isSeat ? ROW_LABELS[r]+(c+1) : ''}
                            </button>
                          );
                        })}
                      </div>
                    );
                  })}
                </div>
                <div style={{ marginTop:16, display:'flex', gap:16, justifyContent:'center', fontSize:12, color:'var(--text-2)' }}>
                  <div style={{ display:'flex', alignItems:'center', gap:6 }}>
                    <div className="builder-grid-cell is-seat" style={{ width:20, height:18, fontSize:8, pointerEvents:'none' }}></div>
                    Kursi Aktif
                  </div>
                  <div style={{ display:'flex', alignItems:'center', gap:6 }}>
                    <div className="builder-grid-cell is-aisle" style={{ width:20, height:18, pointerEvents:'none' }}></div>
                    Lorong / Kosong
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
            <div className="card">
              <div className="card-header"><div className="card-title">Ringkasan</div></div>
              <div className="card-body">
                <div className="order-summary-row"><span>Studio</span><span style={{ fontWeight:700 }}>{config.name}</span></div>
                <div className="order-summary-row"><span>Tipe</span><span>{(window.STUDIO_TYPES.find(function(t){ return t.id===config.studio_type_id; })||{}).name}</span></div>
                <div className="order-summary-row"><span>Grid</span><span style={{ fontFamily:'var(--font-mono)' }}>{cells.length}R × {cells[0].length}K</span></div>
                <div className="order-summary-row"><span>Total Sel</span><span>{cells.length * cells[0].length}</span></div>
                <div className="order-summary-row" style={{ border:'none' }}>
                  <span>Kapasitas Kursi</span>
                  <span style={{ fontWeight:800, fontSize:20, color: seatCount>0?'var(--s-green)':'var(--s-red)' }}>{seatCount}</span>
                </div>
              </div>
            </div>
            {seatCount === 0 && (
              <InfoBanner type="error">Pilih minimal satu kursi untuk melanjutkan.</InfoBanner>
            )}
            <button className="button button-primary button-full button-lg" onClick={handleSave} disabled={seatCount === 0}>
              <Icon name="checkCircle" size={16} /> Simpan Studio &amp; Kursi
            </button>
            <button className="button button-secondary button-full" onClick={function(){ setPhase('config'); setCells(null); }}>
              <Icon name="arrowLeft" size={14} /> Kembali ke Konfigurasi
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { ManagerDashboard, MovieManagement, ProductCatalog, StudioManagement, StudioLayoutBuilder });
