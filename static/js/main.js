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

  fetch('/api/transport_cost?from_city=' + encodeURIComponent(from) +
        '&to_city=' + encodeURIComponent(to) +
        '&quantity_tons=' + qty +
        '&mode=' + encodeURIComponent(mode))
    .then(function (r) { return r.json(); })
    .then(function (d) {
      out.innerHTML =
        '<div class="stat-row mt-16">' +
          mkStat(d.distance_km + ' km', 'Distance') +
          mkStat('₹' + d.rate_per_km_ton + '/km/t', 'Rate') +
          mkStat('₹' + fmt(d.total_cost), 'Total Cost') +
        '</div>';
    })
    .catch(function () {
      out.innerHTML = '<p class="text-red mt-8" style="font-size:.85rem">Could not fetch — check connection.</p>';
    });
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
