/* ================================================
   SILVER SCREEN — Payment Gateway Stub Page
   Visually distinct from Silver Screen app
   ================================================ */

function GatewayPage() {
  var { pageParams, gatewayPayments, processPaymentCallback, navigate, addToast } = useApp();
  var gwPayId = pageParams.gatewayPaymentId;

  var [gwPay, setGwPay]   = React.useState(null);
  var [timeLeft, setTimeLeft] = React.useState(null);
  var [processing, setProcessing] = React.useState(false);
  var [done, setDone]     = React.useState(false);
  var [doneStatus, setDoneStatus] = React.useState(null);

  React.useEffect(function() {
    var found = gatewayPayments.find(function(g) { return g.gateway_payment_id === gwPayId; });
    setGwPay(found || null);
    if (found && found.status === 'WAITING_PAYMENT') {
      var expireMs = new Date(found.expired_at).getTime() - Date.now();
      setTimeLeft(Math.max(0, Math.floor(expireMs / 1000)));
    }
  }, [gwPayId, gatewayPayments]);

  React.useEffect(function() {
    if (timeLeft === null || timeLeft <= 0 || done) return;
    var timer = setInterval(function() {
      setTimeLeft(function(prev) {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return function() { clearInterval(timer); };
  }, [timeLeft, done]);

  function formatCountdown(secs) {
    var m = Math.floor(secs / 60);
    var s = secs % 60;
    return String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
  }

  function handlePay() {
    if (processing || done) return;
    setProcessing(true);
    setTimeout(function() {
      processPaymentCallback(gwPay.internal_payment_id, gwPay.gateway_payment_id, 'PAID');
      setDone(true);
      setDoneStatus('PAID');
      setProcessing(false);
    }, 1200);
  }

  function handleExpire() {
    if (processing || done) return;
    setProcessing(true);
    setTimeout(function() {
      processPaymentCallback(gwPay.internal_payment_id, gwPay.gateway_payment_id, 'EXPIRED');
      setDone(true);
      setDoneStatus('EXPIRED');
      setProcessing(false);
    }, 1000);
  }

  function handleBack() {
    navigate('orders');
  }

  if (!gwPay) {
    return (
      <div className="gw-page">
        <div className="gw-header">
          <div className="gw-logo">
            <div className="gw-logo-mark"><Icon name="shield" size={22} color="white" /></div>
            <div>
              <div className="gw-logo-text">PayGate</div>
              <div className="gw-logo-sub">Secure Payment Gateway</div>
            </div>
          </div>
        </div>
        <div className="gw-card">
          <div style={{ textAlign:'center', color:'#94a3b8', padding:'32px 0' }}>
            <Icon name="xCircle" size={40} color="#ef4444" />
            <div style={{ marginTop:12, fontSize:16, fontWeight:700, color:'#f1f5f9' }}>Pembayaran Tidak Ditemukan</div>
            <div style={{ marginTop:8, fontSize:13 }}>ID pembayaran gateway tidak valid.</div>
          </div>
          <button className="gw-btn gw-btn-back" onClick={handleBack}>
            ← Kembali ke Silver Screen
          </button>
        </div>
      </div>
    );
  }

  var isWaiting = gwPay.status === 'WAITING_PAYMENT' && !done;
  var isPaid    = gwPay.status === 'PAID'    || doneStatus === 'PAID';
  var isExpired = gwPay.status === 'EXPIRED' || doneStatus === 'EXPIRED' || (timeLeft !== null && timeLeft <= 0 && !isPaid);

  return (
    <div className="gw-page">
      {/* Header */}
      <div className="gw-header">
        <div className="gw-logo" style={{ justifyContent:'center' }}>
          <div className="gw-logo-mark"><Icon name="shield" size={22} color="white" /></div>
          <div>
            <div className="gw-logo-text" style={{ fontSize:24 }}>PayGate</div>
            <div className="gw-logo-sub">Stub Payment Gateway — Demo Environment</div>
          </div>
        </div>
        <div style={{ marginTop:12, display:'inline-block', padding:'4px 14px', background:'rgba(239,68,68,0.12)', border:'1px solid rgba(239,68,68,0.25)', borderRadius:99, fontSize:11, color:'#fca5a5', letterSpacing:'0.06em', fontWeight:700 }}>
          STUB / SANDBOX MODE
        </div>
      </div>

      <div className="gw-card">
        {/* Status Banner */}
        {done && isPaid && (
          <div style={{ padding:'16px', background:'rgba(52,211,153,0.10)', border:'1px solid rgba(52,211,153,0.25)', borderRadius:10, marginBottom:20, display:'flex', alignItems:'center', gap:10 }}>
            <Icon name="checkCircle" size={22} color="#34d399" />
            <div>
              <div style={{ fontWeight:700, color:'#34d399' }}>Pembayaran Berhasil</div>
              <div style={{ fontSize:12, color:'#64748b', marginTop:2 }}>Gateway telah mengirim callback ke Silver Screen App</div>
            </div>
          </div>
        )}
        {(isExpired && !isPaid) && (
          <div style={{ padding:'16px', background:'rgba(148,163,184,0.10)', border:'1px solid rgba(148,163,184,0.25)', borderRadius:10, marginBottom:20, display:'flex', alignItems:'center', gap:10 }}>
            <Icon name="ban" size={22} color="#94a3b8" />
            <div>
              <div style={{ fontWeight:700, color:'#94a3b8' }}>Pembayaran Expired</div>
              <div style={{ fontSize:12, color:'#64748b', marginTop:2 }}>Gateway telah mengirim callback expired ke Silver Screen App</div>
            </div>
          </div>
        )}

        {/* Payment Info */}
        <div className="gw-amount-label">Total Pembayaran</div>
        <div className="gw-amount">{window.fmtCurrency(gwPay.amount)}</div>

        <div className="gw-separator"></div>

        <div className="gw-field">
          <span className="gw-field-label">Gateway Payment ID</span>
          <span className="gw-field-value">{gwPay.gateway_payment_id}</span>
        </div>
        <div className="gw-field">
          <span className="gw-field-label">Internal Payment ID</span>
          <span className="gw-field-value">{gwPay.internal_payment_id}</span>
        </div>
        <div className="gw-field">
          <span className="gw-field-label">Client ID</span>
          <span className="gw-field-value">{gwPay.client_id}</span>
        </div>
        <div className="gw-field">
          <span className="gw-field-label">Waktu Bayar Maks.</span>
          <span className="gw-field-value">{window.fmtDateTime(gwPay.expired_at)}</span>
        </div>
        <div className="gw-field" style={{ borderBottom:'none' }}>
          <span className="gw-field-label">Status Gateway</span>
          <span className="gw-field-value" style={{ color: isPaid ? '#34d399' : isExpired ? '#94a3b8' : '#fbbf24' }}>
            {isPaid ? 'PAID' : isExpired ? 'EXPIRED' : gwPay.status}
          </span>
        </div>

        {/* Countdown */}
        {isWaiting && timeLeft !== null && (
          <div className="gw-countdown">
            <div className="gw-countdown-time">{formatCountdown(timeLeft)}</div>
            <div className="gw-countdown-label">Waktu tersisa untuk membayar</div>
          </div>
        )}

        <div className="gw-separator"></div>

        {/* Status indicator */}
        <div style={{ textAlign:'center', marginBottom:20 }}>
          {isWaiting && (
            <div className="gw-status-waiting">
              <Icon name="clock" size={18} color="#fbbf24" />
              Menunggu Pembayaran
            </div>
          )}
          {isPaid && (
            <div className="gw-status-paid">
              <Icon name="checkCircle" size={18} color="#34d399" />
              Pembayaran Diterima
            </div>
          )}
          {isExpired && !isPaid && (
            <div className="gw-status-expired">
              <Icon name="ban" size={18} color="#94a3b8" />
              Pembayaran Expired
            </div>
          )}
        </div>

        {/* Action Buttons */}
        {isWaiting && (
          <>
            <button className="gw-btn gw-btn-pay" onClick={handlePay} disabled={processing}>
              {processing ? 'Memproses...' : 'Bayar Sekarang'}
            </button>
            <button className="gw-btn gw-btn-expire" onClick={handleExpire} disabled={processing}>
              Simulate Expired
            </button>
          </>
        )}

        {/* Architecture note */}
        <div className="gw-separator"></div>
        <div style={{ background:'rgba(255,255,255,0.03)', border:'1px solid rgba(255,255,255,0.06)', borderRadius:8, padding:14 }}>
          <div style={{ fontSize:11, color:'#475569', fontWeight:700, textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:8 }}>Arsitektur Stub</div>
          <div style={{ fontSize:12, color:'#475569', lineHeight:1.6 }}>
            Halaman ini merepresentasikan <strong style={{ color:'#64748b' }}>Payment Gateway eksternal</strong> yang terpisah dari Silver Screen App.
            Gateway memiliki record pembayaran sendiri (<strong style={{ color:'#64748b' }}>{gwPay.gateway_payment_id}</strong>).
            Setelah tombol diklik, gateway memanggil callback ke:
          </div>
          <div style={{ marginTop:8, fontFamily:'var(--font-mono)', fontSize:11, color:'#3b82f6', background:'rgba(59,130,246,0.08)', padding:'6px 10px', borderRadius:6 }}>
            POST /payments/callback/ ← dipanggil oleh gateway stub
          </div>
        </div>

        <button className="gw-btn gw-btn-back" onClick={handleBack}>
          ← Kembali ke Silver Screen
        </button>

        <div className="gw-secure-badge">
          <Icon name="shield" size={14} color="#475569" />
          Stub Gateway — Demo Only — Tidak ada transaksi nyata
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { GatewayPage });
