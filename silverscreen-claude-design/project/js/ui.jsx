/* ================================================
   SILVER SCREEN — Shared UI Components
   ================================================ */

/* ── SVG Icons ──────────────────────────────────── */
function Icon({ name, size, color }) {
  var s = size || 16;
  var c = color || 'currentColor';
  var icons = {
    film: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="17" y1="7" x2="22" y2="7"/><line x1="17" y1="17" x2="22" y2="17"/><line x1="2" y1="17" x2="7" y2="17"/></svg>,
    calendar: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>,
    seat: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 17v2a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-2"/><rect x="6" y="11" width="12" height="8" rx="2"/><path d="M6 11V7a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v4"/><line x1="6" y1="15" x2="18" y2="15"/></svg>,
    ticket: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 5v2M15 11v2M15 17v2M5 5h14a2 2 0 0 1 2 2v3a2 2 0 0 0 0 4v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-3a2 2 0 0 0 0-4V7a2 2 0 0 1 2-2z"/></svg>,
    shoppingBag: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>,
    clipboardList: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><line x1="9" y1="12" x2="15" y2="12"/><line x1="9" y1="16" x2="13" y2="16"/></svg>,
    clock: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
    settings: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>,
    dashboard: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>,
    printer: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>,
    eye: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>,
    edit: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>,
    trash: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>,
    plus: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2.5" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>,
    minus: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2.5" strokeLinecap="round"><line x1="5" y1="12" x2="19" y2="12"/></svg>,
    check: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>,
    x: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2.5" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
    checkCircle: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="9 12 11.5 14.5 16 9.5"/></svg>,
    xCircle: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>,
    alertTriangle: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>,
    info: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>,
    search: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>,
    arrowRight: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>,
    arrowLeft: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>,
    user: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>,
    creditCard: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>,
    package: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>,
    grid: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>,
    layers: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>,
    externalLink: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>,
    refreshCw: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>,
    shield: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
    qr: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="5" height="5"/><rect x="4" y="4" width="3" height="3" fill={c} stroke="none"/><rect x="16" y="3" width="5" height="5"/><rect x="17" y="4" width="3" height="3" fill={c} stroke="none"/><rect x="3" y="16" width="5" height="5"/><rect x="4" y="17" width="3" height="3" fill={c} stroke="none"/><line x1="16" y1="16" x2="16" y2="16"/><line x1="19" y1="16" x2="19" y2="16"/><line x1="16" y1="19" x2="16" y2="19"/><line x1="19" y1="19" x2="19" y2="19"/><line x1="16" y1="22" x2="16" y2="22"/><line x1="22" y1="16" x2="22" y2="16"/><line x1="22" y1="19" x2="22" y2="19"/><line x1="22" y1="22" x2="22" y2="22"/><line x1="10" y1="3" x2="10" y2="3"/><line x1="13" y1="3" x2="13" y2="3"/><line x1="10" y1="7" x2="10" y2="7"/><line x1="13" y1="6" x2="13" y2="6"/><line x1="10" y1="10" x2="10" y2="10"/><line x1="13" y1="11" x2="13" y2="11"/><line x1="10" y1="14" x2="10" y2="14"/><line x1="13" y1="14" x2="13" y2="14"/><line x1="3" y1="10" x2="3" y2="10"/><line x1="3" y1="13" x2="3" y2="13"/><line x1="7" y1="10" x2="7" y2="10"/><line x1="6" y1="13" x2="6" y2="13"/></svg>,
    star: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>,
    ban: <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>,
  };
  return <span style={{ display:'inline-flex', alignItems:'center', flexShrink:0 }}>{icons[name] || null}</span>;
}

/* ── Status Badge ────────────────────────────────── */
const STATUS_LABELS = {
  PENDING: 'Pending', CONFIRMED: 'Confirmed', EXPIRED: 'Expired',
  CANCELED: 'Canceled', HELD: 'Held', PRINTED: 'Printed',
  UNPAID: 'Unpaid', PAID: 'Paid', REFUND_PENDING: 'Refund Pending',
  REFUNDED: 'Refunded', CANCELED_BEFORE_PAID: 'Batal Sebelum Bayar',
  WAITING_PAYMENT: 'Menunggu Bayar',
  ONLINE: 'Online', ONSITE: 'Onsite',
  ALL_AGE: 'Semua Usia', R7: 'R7+', R13: 'R13+', R17: 'R17+', R21: 'R21+',
};

function StatusBadge({ status, label }) {
  var cls = 'status-badge badge-' + (status || '').toLowerCase();
  var lbl = label || STATUS_LABELS[status] || status;
  return (
    <span className={cls}>
      <span className="dot"></span>
      {lbl}
    </span>
  );
}

function SourceBadge({ source }) {
  var cls = source === 'ONLINE' ? 'status-badge badge-source-online' : 'status-badge badge-source-onsite';
  return <span className={cls}><span className="dot"></span>{source}</span>;
}

/* ── Toast System ────────────────────────────────── */
function ToastContainer() {
  var { toasts, removeToast } = useApp();
  var iconMap = { success: 'checkCircle', error: 'xCircle', warning: 'alertTriangle', info: 'info' };
  var colorMap = { success: 'var(--s-green)', error: 'var(--s-red)', warning: 'var(--s-amber)', info: 'var(--s-blue)' };
  return (
    <div className="toast-container">
      {toasts.map(function(t) {
        return (
          <div key={t.id} className={'toast toast-' + t.type}>
            <span className="toast-icon" style={{ color: colorMap[t.type] }}>
              <Icon name={iconMap[t.type] || 'info'} size={18} />
            </span>
            <span className="toast-message">{t.message}</span>
            <button className="button-icon" style={{ border:'none', background:'transparent', padding:'2px' }} onClick={function(){ removeToast(t.id); }}>
              <Icon name="x" size={14} color="var(--text-3)" />
            </button>
          </div>
        );
      })}
    </div>
  );
}

/* ── Modal ───────────────────────────────────────── */
function Modal({ title, children, onClose, actions, size }) {
  React.useEffect(function() {
    function onKey(e) { if (e.key === 'Escape' && onClose) onClose(); }
    document.addEventListener('keydown', onKey);
    return function() { document.removeEventListener('keydown', onKey); };
  }, [onClose]);
  var sizeClass = size === 'lg' ? 'modal modal-lg' : size === 'xl' ? 'modal modal-xl' : 'modal';
  return (
    <div className="modal-overlay" onClick={function(e){ if(e.target === e.currentTarget && onClose) onClose(); }}>
      <div className={sizeClass}>
        <div className="modal-header">
          <span className="modal-title">{title}</span>
          {onClose && (
            <button className="button-icon" onClick={onClose} style={{ border:'none', background:'transparent' }}>
              <Icon name="x" size={18} />
            </button>
          )}
        </div>
        <div className="modal-body">{children}</div>
        {actions && <div className="modal-footer">{actions}</div>}
      </div>
    </div>
  );
}

/* ── Stepper ─────────────────────────────────────── */
function Stepper({ steps, current }) {
  return (
    <div className="stepper">
      {steps.map(function(step, i) {
        var state = i < current ? 'completed' : i === current ? 'active' : 'inactive';
        return (
          <React.Fragment key={i}>
            <div className={'stepper-step ' + state}>
              <div className="stepper-circle">
                {state === 'completed' ? <Icon name="check" size={13} /> : i + 1}
              </div>
              <span className="stepper-label">{step}</span>
            </div>
            {i < steps.length - 1 && (
              <div className={'stepper-line' + (i < current ? ' completed' : '')}></div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

/* ── Page Header ─────────────────────────────────── */
function PageHeader({ title, subtitle, actions, back, onBack }) {
  return (
    <div className="page-header">
      {back && (
        <button className="button button-ghost" style={{ padding:'8px', marginRight:4 }} onClick={onBack}>
          <Icon name="arrowLeft" size={18} />
        </button>
      )}
      <div className="page-header-text">
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  );
}

/* ── Empty State ─────────────────────────────────── */
function EmptyState({ icon, title, desc, action }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon"><Icon name={icon || 'package'} size={40} /></div>
      <div className="empty-state-title">{title}</div>
      {desc && <div className="empty-state-desc">{desc}</div>}
      {action}
    </div>
  );
}

/* ── Info Banner ─────────────────────────────────── */
function InfoBanner({ type, icon, children }) {
  var iconMap = { warning:'alertTriangle', error:'xCircle', success:'checkCircle', info:'info' };
  return (
    <div className={'info-banner info-banner-' + (type||'info')}>
      <span className="info-banner-icon"><Icon name={iconMap[type||'info']} size={16} /></span>
      <span>{children}</span>
    </div>
  );
}

/* ── Confirm Modal ───────────────────────────────── */
function ConfirmModal({ title, message, onConfirm, onCancel, danger }) {
  return (
    <Modal
      title={title}
      onClose={onCancel}
      actions={
        <>
          <button className="button button-secondary" onClick={onCancel}>Batal</button>
          <button className={'button ' + (danger ? 'button-danger' : 'button-primary')} onClick={onConfirm}>
            Konfirmasi
          </button>
        </>
      }
    >
      <p style={{ color: 'var(--text-2)', fontSize: 14, lineHeight: 1.6 }}>{message}</p>
    </Modal>
  );
}

/* ── Movie Poster Placeholder ────────────────────── */
function MoviePoster({ movie, height }) {
  var themeColors = {
    'Drama':       ['#2d1f3d','#4a2d5e'],
    'Sci-Fi':      ['#0f1f3d','#1a3a5e'],
    'Horror':      ['#1a0d0d','#3a1515'],
    'Family':      ['#1a2d1a','#2d4a2d'],
    'Documentary': ['#2d2a1f','#4a4530'],
    'Action':      ['#2d1a0d','#4a3015'],
    'Romance':     ['#3d1f2d','#5e2d4a'],
  };
  var colors = themeColors[movie.theme && movie.theme.name] || ['#1c1612','#2d2520'];
  return (
    <div className="movie-poster" style={{ height: height, background: 'linear-gradient(160deg, ' + colors[0] + ' 0%, ' + colors[1] + ' 100%)' }}>
      <div className="movie-poster-pattern"></div>
      <div style={{ position:'relative', zIndex:1, display:'flex', flexDirection:'column', alignItems:'center', gap:8 }}>
        <Icon name="film" size={28} color="rgba(255,255,255,0.25)" />
        <div className="movie-poster-genre">{movie.theme && movie.theme.name}</div>
        <div className="movie-poster-title">{movie.title}</div>
      </div>
    </div>
  );
}

/* ── Seat Grid ───────────────────────────────────── */
function SeatGrid({ studio, occupancy, selectedSeats, onSeatClick, readOnly }) {
  var rows   = studio.grid_y_pos;
  var cols   = studio.grid_x_pos;
  var seats  = studio.seats;
  var rowLabels = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  var occ = occupancy || {};
  var sel = selectedSeats || [];

  return (
    <div className="seat-grid-container">
      <div className="seat-screen">— Layar —</div>
      <div style={{ overflowX:'auto', paddingBottom: 8 }}>
        {Array.from({ length: rows }, function(_, r) {
          return (
            <div key={r} style={{ display:'flex', alignItems:'center', gap:5, marginBottom:5, justifyContent:'center' }}>
              <span className="seat-row-label">{rowLabels[r]}</span>
              {Array.from({ length: cols }, function(_, c) {
                var seat = seats.find(function(s){ return s.grid_y_pos === r && s.grid_x_pos === c; });
                if (!seat) return <div key={c} style={{ width:30, height:28 }}></div>;
                if (seat.is_aisle) return <div key={c} className="seat aisle"></div>;

                var occData = occ[seat.id];
                var isSel   = sel.some(function(s){ return s.id === seat.id; });
                var cls = 'seat ';
                if (isSel) cls += 'selected';
                else if (occData) cls += occData.status.toLowerCase();
                else if (!seat.is_active) cls += 'disabled';
                else cls += 'available';

                var canClick = !readOnly && !occData && seat.is_active;

                return (
                  <button
                    key={c}
                    className={cls}
                    title={seat.number + (occData ? ' (' + occData.status + ')' : '')}
                    disabled={!canClick && !isSel}
                    onClick={canClick || isSel ? function(){ onSeatClick && onSeatClick(seat); } : undefined}
                  >
                    {seat.number}
                  </button>
                );
              })}
            </div>
          );
        })}
      </div>
      <div className="seat-legend">
        {[
          { cls:'available', label:'Tersedia' },
          { cls:'selected',  label:'Dipilih' },
          { cls:'held',      label:'Ditahan' },
          { cls:'confirmed', label:'Terkonfirmasi' },
          { cls:'printed',   label:'Tercetak' },
          { cls:'disabled',  label:'Nonaktif' },
        ].map(function(item) {
          var bg = { available:'#e0dbd2', selected:'var(--red)', held:'#fbbf24', confirmed:'#22c55e', printed:'#7c3aed', disabled:'#d1d5db' };
          return (
            <div key={item.cls} className="seat-legend-item">
              <div className="seat-legend-dot" style={{ background: bg[item.cls] }}></div>
              {item.label}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── State Machine Diagram ───────────────────────── */
function StateMachineDiagram() {
  var flows = [
    {
      title: 'Order Status',
      nodes: [
        { from:'PENDING', to:['CONFIRMED','EXPIRED','CANCELED'], conditions:['Pembayaran sukses','Pembayaran expired','Pelanggan batalkan (sebelum cetak)'] },
        { from:'CONFIRMED', to:['CANCELED'], conditions:['Tiket belum dicetak'] },
      ]
    },
    {
      title: 'Ticket Status',
      nodes: [
        { from:'HELD', to:['CONFIRMED','EXPIRED','CANCELED'], conditions:['Pembayaran sukses','Pembayaran expired','Order dibatalkan'] },
        { from:'CONFIRMED', to:['PRINTED','CANCELED'], conditions:['Cetak tiket','Order dibatalkan (sebelum cetak)'] },
      ]
    },
    {
      title: 'Payment Status',
      nodes: [
        { from:'UNPAID', to:['PAID','EXPIRED','CANCELED_BEFORE_PAID'], conditions:['Callback sukses','Callback expired','Order batal sebelum bayar'] },
        { from:'PAID', to:['REFUND_PENDING'], conditions:['Order dibatalkan setelah bayar'] },
        { from:'REFUND_PENDING', to:['REFUNDED'], conditions:['Staff tandai refund selesai'] },
      ]
    },
  ];
  return (
    <div style={{ display:'flex', flexDirection:'column', gap: 24 }}>
      {flows.map(function(flow) {
        return (
          <div key={flow.title}>
            <div className="section-title" style={{ marginBottom:12 }}>{flow.title}</div>
            <div className="card"><div className="card-body" style={{ padding:16 }}>
              {flow.nodes.map(function(node, i) {
                return (
                  <div key={i} style={{ display:'flex', alignItems:'flex-start', gap:12, marginBottom:12 }}>
                    <StatusBadge status={node.from} />
                    <div style={{ display:'flex', flexDirection:'column', gap:6, flex:1 }}>
                      {node.to.map(function(to, j) {
                        return (
                          <div key={to} style={{ display:'flex', alignItems:'center', gap:8 }}>
                            <Icon name="arrowRight" size={14} color="var(--text-3)" />
                            <StatusBadge status={to} />
                            <span style={{ fontSize:12, color:'var(--text-3)', fontStyle:'italic' }}>
                              — {node.conditions[j]}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div></div>
          </div>
        );
      })}
      <div>
        <div className="section-title" style={{ marginBottom:12 }}>Onsite Flow</div>
        <div className="card"><div className="card-body" style={{ padding:16 }}>
          <InfoBanner type="info">
            Order onsite tidak melalui alur PENDING. Order, tiket, dan pembayaran dibuat sekaligus dalam satu aksi atomik setelah pelanggan membayar. Status tiket langsung PRINTED.
          </InfoBanner>
        </div></div>
      </div>
    </div>
  );
}

/* ── Integration Flow Panel ──────────────────────── */
function IntegrationFlowPanel() {
  var { integrationLog } = useApp();
  var logRef = React.useRef(null);
  React.useEffect(function() {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [integrationLog]);

  var steps = [
    { label:'Pelanggan buat pesanan online', dir:null },
    { label:'POST /stub/payment-gateway/issue-payment/', dir:'right' },
    { label:'Gateway kembalikan payment_url + gateway_payment_id', dir:'left' },
    { label:'Pelanggan buka halaman gateway', dir:null },
    { label:'Pelanggan klik Bayar / Expired', dir:null },
    { label:'POST /payments/callback/', dir:'left' },
    { label:'Internal Payment / Order / Tiket diperbarui', dir:null },
  ];

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:24 }}>
      <div className="integration-grid">
        <div className="integration-app integration-app-ss">
          <div className="integration-app-title">Silver Screen App</div>
          {['Internal Order','Internal Payment','Internal Ticket'].map(function(item){
            return <div key={item} className="integration-item"><Icon name="arrowRight" size={12} />{item}</div>;
          })}
          <div style={{ marginTop:10 }}>
            <div className="integration-endpoint">POST /payments/callback/</div>
          </div>
        </div>
        <div className="integration-arrows">
          <div className="integration-arrow">
            <Icon name="arrowRight" size={14} />
            <span>issue-payment</span>
          </div>
          <div className="integration-arrow" style={{ flexDirection:'row-reverse' }}>
            <Icon name="arrowLeft" size={14} />
            <span>payment_url</span>
          </div>
          <div className="integration-arrow" style={{ flexDirection:'row-reverse' }}>
            <Icon name="arrowLeft" size={14} />
            <span>callback</span>
          </div>
        </div>
        <div className="integration-app integration-app-gw">
          <div className="integration-app-title">Stub Payment Gateway</div>
          {['Gateway Payment (terpisah dari Internal Payment)'].map(function(item){
            return <div key={item} className="integration-item"><Icon name="arrowRight" size={12} />{item}</div>;
          })}
          <div style={{ marginTop:10, display:'flex', flexDirection:'column', gap:6 }}>
            <div className="integration-endpoint">POST /stub/payment-gateway/issue-payment/</div>
            <div className="integration-endpoint">GET /stub/payment-gateway/pay/:gwPayId</div>
          </div>
        </div>
      </div>

      <div>
        <div className="section-title" style={{ marginBottom:10 }}>Alur Transaksi</div>
        <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
          {steps.map(function(step, i) {
            return (
              <div key={i} style={{ display:'flex', alignItems:'center', gap:10, padding:'8px 12px', background:'var(--bg-card)', border:'1px solid var(--border-lt)', borderRadius:'var(--r-sm)' }}>
                <div style={{ width:22, height:22, borderRadius:'50%', background:'var(--red)', color:'white', fontSize:11, fontWeight:700, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>{i+1}</div>
                {step.dir === 'right' && <Icon name="arrowRight" size={14} color="var(--s-blue)" />}
                {step.dir === 'left'  && <Icon name="arrowLeft"  size={14} color="var(--s-orange)" />}
                <span style={{ fontSize:13, color:'var(--text-2)' }}>{step.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div>
        <div className="section-title" style={{ marginBottom:10 }}>Event Log</div>
        {integrationLog.length === 0 ? (
          <div style={{ padding:16, background:'#0f1117', borderRadius:'var(--r-md)', color:'#4b5563', fontSize:13, fontFamily:'var(--font-mono)' }}>
            — Belum ada event. Buat pesanan online untuk memulai. —
          </div>
        ) : (
          <div className="integration-log" ref={logRef}>
            {integrationLog.map(function(entry) {
              var cls = 'log-msg' + (entry.kind === 'request' ? ' log-request' : entry.kind === 'response' ? ' log-response' : '');
              return (
                <div key={entry.id} className="log-entry">
                  <span className="log-time">{entry.time}</span>
                  <span className={cls}>{entry.message}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Ticket Preview Card ──────────────────────────── */
function TicketPreviewCard({ ticket, order }) {
  var { fmtTime, fmtDate } = useApp();
  var st = order.showtime;
  return (
    <div className="ticket-card">
      <div className="ticket-card-header">
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', position:'relative' }}>
          <div>
            <div className="ticket-movie-title">{st.movie.title}</div>
            <div className="ticket-studio">{st.studio.name} — {st.studio.studio_type.name}</div>
          </div>
          <StatusBadge status={ticket.status} />
        </div>
      </div>
      <div className="ticket-red-stripe"></div>
      <div className="ticket-body">
        <div className="ticket-row">
          <div className="ticket-field">
            <div className="ticket-field-label">Tanggal</div>
            <div className="ticket-field-value" style={{ fontSize:14 }}>{fmtDate(st.start_at)}</div>
          </div>
          <div className="ticket-field">
            <div className="ticket-field-label">Jam Tayang</div>
            <div className="ticket-field-value">{fmtTime(st.start_at)} — {fmtTime(st.end_at)}</div>
          </div>
        </div>
        <div className="ticket-row">
          <div className="ticket-field">
            <div className="ticket-field-label">Kursi</div>
            <div className="ticket-seat-badge">{ticket.seat.number}</div>
          </div>
          <div className="ticket-field">
            <div className="ticket-field-label">No. Pesanan</div>
            <div className="ticket-field-value" style={{ fontSize:13, fontFamily:'var(--font-mono)' }}>{order.number}</div>
          </div>
        </div>
        <div className="ticket-divider">
          <div className="ticket-divider-line"></div>
          <Icon name="ticket" size={16} color="var(--text-3)" />
          <div className="ticket-divider-line"></div>
        </div>
        <div className="ticket-code-section">
          <div className="ticket-qr">
            <Icon name="qr" size={52} color="white" />
          </div>
          <div>
            <div style={{ fontSize:11, color:'var(--text-3)', marginBottom:4 }}>Kode Tiket</div>
            <div className="ticket-code">{ticket.code}</div>
            {ticket.printed_at && (
              <div style={{ fontSize:11, color:'var(--text-3)', marginTop:4 }}>
                Dicetak: {window.fmtDateTime(ticket.printed_at)}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, {
  Icon, StatusBadge, SourceBadge, ToastContainer,
  Modal, Stepper, PageHeader, EmptyState, InfoBanner, ConfirmModal,
  MoviePoster, SeatGrid, StateMachineDiagram, IntegrationFlowPanel,
  TicketPreviewCard, STATUS_LABELS,
});
