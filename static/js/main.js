/* =============================================================
   KSHETRA — Main JS
   ============================================================= */

document.addEventListener('DOMContentLoaded', function () {

  // ----- Hamburger nav toggle -----
  const toggle = document.querySelector('.nav-toggle');
  const links  = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      links.classList.toggle('open');
    });
  }

  // ----- Auto-dismiss flash messages after 5s -----
  const flashes = document.querySelectorAll('.flash');
  flashes.forEach(function (el) {
    setTimeout(function () { fadeOut(el); }, 5000);
  });

  document.querySelectorAll('.flash-close').forEach(function (btn) {
    btn.addEventListener('click', function () { fadeOut(btn.closest('.flash')); });
  });

  function fadeOut(el) {
    if (!el) return;
    el.style.transition = 'opacity .4s, transform .4s';
    el.style.opacity    = '0';
    el.style.transform  = 'translateX(100%)';
    setTimeout(function () { el.remove(); }, 400);
  }

  // ----- Password visibility toggle -----
  document.querySelectorAll('.pwd-toggle').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var input = btn.previousElementSibling;
      if (!input) return;
      if (input.type === 'password') {
        input.type = 'text';
        btn.innerHTML = '<i class="bi bi-eye-slash"></i>';
      } else {
        input.type = 'password';
        btn.innerHTML = '<i class="bi bi-eye"></i>';
      }
    });
  });

  // ----- Active nav link -----
  var path = window.location.pathname;
  document.querySelectorAll('.nav-links a').forEach(function (a) {
    if (a.getAttribute('href') && path.startsWith(a.getAttribute('href')) && a.getAttribute('href') !== '/') {
      a.classList.add('active');
    }
  });

});

// Transport cost calculator
function calcTransportCost() {
  var from = document.getElementById('tc_from').value;
  var to   = document.getElementById('tc_to').value;
  var qty  = document.getElementById('tc_qty').value;
  var mode = document.getElementById('tc_mode').value;
  var out  = document.getElementById('tc_result');

  out.innerHTML = '<p style="font-size:.82rem;color:var(--muted);margin-top:8px;">Calculating...</p>';

  fetch('/api/transport_cost?from_city=' + encodeURIComponent(from) +
        '&to_city=' + encodeURIComponent(to) +
        '&quantity_tons=' + qty +
        '&mode=' + encodeURIComponent(mode))
    .then(function (r) { return r.json(); })
    .then(function (d) {
      out.innerHTML =
        '<div style="margin-top:14px;background:var(--bg);border:1px solid var(--border);' +
        'border-radius:10px;overflow:hidden;">' +

        // Header
        '<div style="background:var(--green-dark);color:#fff;padding:10px 14px;' +
        'font-size:.8rem;font-weight:700;display:flex;justify-content:space-between;align-items:center;">' +
          '<span>Cost Breakdown · ' + d.mode + '</span>' +
          '<span>' + d.distance_km + ' km · ' + d.trips + ' trip' + (d.trips>1?'s':'') +
          ' · ' + d.capacity_ton + 't/trip</span>' +
        '</div>' +

        // Breakdown rows
        '<div style="padding:12px 14px;display:flex;flex-direction:column;gap:7px;">' +
          row('⛽ Fuel / Fodder',       d.fuel_cost) +
          row('📦 Loading & Unloading', d.loading_cost) +
          (d.toll_cost > 0 ? row('🛣️ Toll / Road Tax', d.toll_cost) : '') +
          (d.driver_cost > 0 ? row('👤 Driver Allowance', d.driver_cost) : '') +
        '</div>' +

        // Total
        '<div style="border-top:2px solid var(--border);padding:12px 14px;' +
        'display:flex;justify-content:space-between;align-items:center;">' +
          '<span style="font-weight:700;font-size:.9rem;">Total Cost</span>' +
          '<span style="font-family:\'Playfair Display\',serif;font-size:1.4rem;' +
          'font-weight:700;color:var(--green-dark);">₹' + fmt(d.total_cost) + '</span>' +
        '</div>' +

        // Per-ton rate
        '<div style="padding:6px 14px 12px;font-size:.75rem;color:var(--muted);">' +
          '₹' + fmt(Math.round(d.total_cost / d.quantity_tons)) + ' per ton &nbsp;·&nbsp; ' +
          '₹' + fmt(Math.round(d.total_cost / d.distance_km)) + ' per km' +
        '</div>' +

        '</div>';
    })
    .catch(function () {
      out.innerHTML = '<p class="text-red mt-8" style="font-size:.85rem">Could not fetch — check connection.</p>';
    });
}

function row(label, amount) {
  return '<div style="display:flex;justify-content:space-between;font-size:.83rem;">' +
         '<span style="color:var(--muted);">' + label + '</span>' +
         '<span style="font-weight:600;">₹' + fmt(amount) + '</span>' +
         '</div>';
}

function mkStat(val, label) {
  return '<div class="stat-box"><div class="stat-box-num" style="font-size:1.3rem;">' + val + '</div>' +
         '<div class="stat-box-label">' + label + '</div></div>';
}

function fmt(n) { return Number(n).toLocaleString('en-IN'); }

// Weather loader
function loadWeather(city, id) {
  var el = document.getElementById(id);
  if (!el) return;
  fetch('/api/weather?city=' + encodeURIComponent(city))
    .then(function (r) { return r.json(); })
    .then(function (d) {
      var rainy = d.rain_probability > 60;
      el.innerHTML =
        '<span class="weather-tag ' + (rainy ? 'rainy' : '') + '">' +
          '<i class="bi bi-' + (rainy ? 'cloud-rain' : 'sun') + '-fill"></i> ' +
          d.rain_probability + '% rain · ' + d.max_temp + '°C' +
        '</span>' +
        '<p style="font-size:.8rem;color:var(--muted);margin-top:6px;">' + d.description + '</p>';
    })
    .catch(function () {
      el.innerHTML = '<span style="font-size:.82rem;color:var(--muted)">Weather unavailable</span>';
    });
}

// Crop filter
function filterCrops(name) {
  document.querySelectorAll('[data-crop]').forEach(function (el) {
    el.style.display = (!name || el.dataset.crop === name) ? '' : 'none';
  });
  document.querySelectorAll('.filter-btn').forEach(function (btn) {
    btn.classList.toggle('btn-primary', btn.dataset.filter === name || (!name && btn.dataset.filter === ''));
    btn.classList.toggle('btn-outline',  !(btn.dataset.filter === name || (!name && btn.dataset.filter === '')));
  });
}
