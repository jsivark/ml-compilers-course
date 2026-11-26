// Progressive enhancements: search, progress, course map state, daily artwork.
// The site works fully without this file.
(function () {
  var root = document.documentElement;
  root.classList.add("js");

  // ---------- animated favicon (Chrome/Safari draw SVG favicons as still frames) ----------
  (function () {
    var link = document.querySelector('link[rel="icon"]');
    if (!link || /firefox/i.test(navigator.userAgent)) return; // Firefox animates the SVG itself
    if (window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    var c = document.createElement("canvas"); c.width = c.height = 64;
    var g = c.getContext("2d"); if (!g) return;
    var INK = "#24489c", PAPER = "#f6f3ec", GOLD = "#ffcf5a";
    var lerp = function (a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]; };
    function along(pts, t) { return t < .5 ? lerp(pts[0], pts[1], t * 2) : lerp(pts[1], pts[2], t * 2 - 1); }
    var L = [[5, 5], [11, 16], [5, 27]], R = [[27, 5], [21, 16], [27, 27]];
    function frame(now) {
      var p = (now % 2000) / 2000, ph = (now % 1000) / 1000 * Math.PI * 2;
      g.setTransform(2, 0, 0, 2, 0, 0); g.clearRect(0, 0, 32, 32);
      g.fillStyle = INK; g.beginPath(); g.roundRect ? g.roundRect(0, 0, 32, 32, 7) : g.rect(0, 0, 32, 32); g.fill();
      g.strokeStyle = PAPER; g.lineWidth = 1.8; g.lineCap = "round";
      [L, R].forEach(function (k) { g.beginPath(); g.moveTo(k[0][0], k[0][1]); g.lineTo(k[1][0], k[1][1]); g.lineTo(k[2][0], k[2][1]); g.stroke(); });
      g.strokeStyle = GOLD; g.beginPath(); // the photon: a travelling wave between the vertices
      for (var x = 11; x <= 21; x += .25) { var y = 16 + 1.8 * Math.sin((x - 11) / 10 * Math.PI * 3 - ph) * Math.sin((x - 11) / 10 * Math.PI); x == 11 ? g.moveTo(x, y) : g.lineTo(x, y); }
      g.stroke();
      g.fillStyle = GOLD; [L, R].forEach(function (k) { var q = along(k, p); g.beginPath(); g.arc(q[0], q[1], 1.6, 0, 7); g.fill(); });
      g.fillStyle = PAPER; [[11, 16], [21, 16]].forEach(function (n) { g.beginPath(); g.arc(n[0], n[1], 1.6, 0, 7); g.fill(); });
      link.href = c.toDataURL("image/png");
    }
    setInterval(function () { if (!document.hidden) frame(performance.now()); }, 80);
  })();
  var base = document.querySelector('meta[name="base"]').content; // "" or "../"
  var store = {
    get: function (k, d) { try { var v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  };

  // ---------- progress ----------
  var done = store.get("done", {});
  // Module 2 (C++) was inserted in Nov 2026: shift progress saved under the old numbering once.
  if (!store.get("numbering41", false)) {
    var moved = {};
    Object.keys(done).forEach(function (k) { var n = +k; moved[n >= 2 ? n + 1 : n] = done[k]; });
    done = moved; store.set("done", done); store.set("numbering41", true);
  }
  function paintProgress() {
    document.querySelectorAll("a[data-mod]").forEach(function (a) {
      a.classList.toggle("done", !!done[a.dataset.mod]);
    });
    var n = Object.keys(done).filter(function (k) { return done[k]; }).length;
    document.querySelectorAll("[data-progress]").forEach(function (el) {
      el.textContent = n ? n + " of 41 modules done" : "";
    });
    document.querySelectorAll("[data-part-progress]").forEach(function (el) {
      var ids = el.dataset.partProgress.split(","), k = ids.filter(function (i) { return done[i]; }).length;
      el.textContent = k ? k + "/" + ids.length : "";
    });
    var b = document.querySelector(".mark");
    if (b) { var on = !!done[b.dataset.mod]; b.classList.toggle("on", on); b.textContent = on ? "✓ Done" : "Mark module done"; }
  }
  document.addEventListener("click", function (e) {
    var b = e.target.closest(".mark");
    if (!b) return;
    done[b.dataset.mod] = !done[b.dataset.mod];
    store.set("done", done);
    paintProgress();
  });
  paintProgress();

  // ---------- phone menu and course-map drawer ----------
  document.addEventListener("click", function (e) {
    if (e.target.closest(".menu-btn")) { document.body.classList.toggle("menu-open"); return; }
    if (e.target.closest(".map-btn")) { document.body.classList.toggle("map-open"); return; }
    if (document.body.classList.contains("map-open") && !e.target.closest(".map")) document.body.classList.remove("map-open");
  });

  // ---------- search (Cmd/Ctrl+K or "/") ----------
  var idx = null, box = null;
  function openSearch() {
    if (!box) {
      box = document.createElement("div");
      box.className = "search";
      box.innerHTML = '<div class="search-panel" role="dialog" aria-label="Search the course"><input type="search" placeholder="Search modules, topics and resources" aria-label="Search"><ol></ol><p class="search-hint">↑ ↓ to move · Enter to open · Esc to close</p></div>';
      document.body.appendChild(box);
      box.addEventListener("click", function (e) { if (e.target === box) closeSearch(); });
      var input = box.querySelector("input"), list = box.querySelector("ol"), sel = 0, hits = [];
      function render() {
        var q = input.value.trim().toLowerCase();
        if (!idx) { list.innerHTML = "<li class='muted'>Loading…</li>"; return; }
        var words = q.split(/\s+/).filter(Boolean);
        hits = !words.length ? idx.filter(function (r) { return r.k === "module"; }) :
          idx.filter(function (r) { var t = r.s; return words.every(function (w) { return t.indexOf(w) >= 0; }); })
             .sort(function (a, b) { return (a.k === "module" ? 0 : 1) - (b.k === "module" ? 0 : 1); });
        hits = hits.slice(0, 40); sel = Math.min(sel, Math.max(hits.length - 1, 0));
        list.innerHTML = hits.length ? hits.map(function (r, i) {
          return '<li' + (i === sel ? ' class="sel"' : "") + '><a href="' + (r.u.indexOf("http") === 0 ? r.u : base + r.u) + '"' + (r.u.indexOf("http") === 0 ? ' target="_blank" rel="noopener"' : "") + '><span class="sk">' + r.k + '</span>' + esc(r.t) + '<span class="sm">' + esc(r.m) + "</span></a></li>";
        }).join("") : "<li class='muted'>No matches</li>";
      }
      input.addEventListener("input", function () { sel = 0; render(); });
      input.addEventListener("keydown", function (e) {
        if (e.key === "ArrowDown") { sel = Math.min(sel + 1, hits.length - 1); render(); e.preventDefault(); }
        else if (e.key === "ArrowUp") { sel = Math.max(sel - 1, 0); render(); e.preventDefault(); }
        else if (e.key === "Enter") { var a = list.querySelectorAll("a")[sel]; if (a) a.click(); }
      });
      box.render = render;
      fetch(base + "search.json").then(function (r) { return r.json(); }).then(function (d) {
        idx = d.map(function (r) { r.s = (r.t + " " + r.m + " " + (r.x || "")).toLowerCase(); return r; }); render();
      }).catch(function () { list.innerHTML = "<li class='muted'>Search is unavailable offline from file://; it works on the website.</li>"; });
    }
    box.classList.add("open");
    var inp = box.querySelector("input"); inp.value = ""; box.render(); inp.focus();
  }
  function closeSearch() { if (box) box.classList.remove("open"); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  document.addEventListener("keydown", function (e) {
    if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && !/input|textarea/i.test(e.target.tagName))) { e.preventDefault(); openSearch(); }
    else if (e.key === "Escape") closeSearch();
  });
  document.querySelectorAll(".search-open").forEach(function (b) { b.addEventListener("click", openSearch); });

  // ---------- daily public-domain artwork (Cleveland Museum of Art open access, CC0) ----------
  // A new random painting each day, fetched live from the museums' open-access APIs.
  if (store.get("art-off", false)) root.classList.add("no-art");
  var today = new Date().toISOString().slice(0, 10);
  var art = store.get("art", null);
  if (art && !art.lic) art = null; // refresh entries saved before credits included date and licence
  function showArt(a) {
    if (!a || !a.img) return;
    var im = new Image();
    im.onload = function () {
      var bg = document.querySelector(".art-bg");
      bg.style.backgroundImage = 'url("' + a.img.replace(/"/g, "") + '")';
      bg.classList.add("on");
      var who = (a.by || "Unknown artist") + (a.date ? ", " + a.date : "");
      var t = a.title.length > 90 ? a.title.slice(0, 88).replace(/\s+\S*$/, "") + "…" : a.title;
      var text = "<i>" + esc(t) + "</i> · " + esc(who) + " · " + esc(a.src) + " (" + esc(a.lic || "public domain") + ")";
      var line = '<a href="' + esc(a.link) + '" target="_blank" rel="noopener" title="View this artwork on the museum website">' + text + " ↗</a>";
      var c = document.querySelector(".art-credit");
      if (c) c.innerHTML = "Background artwork: " + line + ' · <button type="button" class="art-toggle">' + (root.classList.contains("no-art") ? "show art" : "hide art") + "</button>";
      var cap = document.createElement("a");
      cap.className = "art-cap"; cap.href = a.link; cap.target = "_blank"; cap.rel = "noopener";
      cap.title = "View this artwork on the museum website"; cap.innerHTML = text + " ↗";
      document.body.appendChild(cap);
    };
    im.onerror = function () { if (retries++ < 2) fresh(); };
    im.src = a.img;
  }
  // Only CC0 works (free for any use, no restrictions), from a curated museum collection:
  // a third of the time the curators' highlights (paintings, prints, drawings), otherwise any public-domain painting.
  function api(u) { return fetch(u).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }); }
  function fromCleveland() {
    var pool = Math.random() < 0.35 ? "&highlight=1" : "&type=Painting";
    var u = "https://openaccess-api.clevelandart.org/api/artworks/?cc0=1&has_image=1" + pool + "&fields=title,creators,creation_date,images,url,share_license_status&limit=1";
    return api(u + "&skip=0").then(function (d) {
      var n = d.info.total; if (!n) throw new Error("none");
      return api(u + "&skip=" + Math.floor(Math.random() * n));
    }).then(function (d) {
      var o = d.data[0];
      if (o.share_license_status !== "CC0" || !o.images || !o.images.web) throw new Error("not CC0");
      // skip text pages, fragments and very long or thin images (scrolls, strips) that make poor backgrounds
      var w = +o.images.web.width, h = +o.images.web.height;
      if (/\b(text|folio|fragment|leaf|calligraphy|inscription)\b/i.test(o.title) || (w && h && (w / h > 2.2 || w / h < 0.45))) throw new Error("skip");
      return { title: o.title, by: (o.creators[0] && o.creators[0].description || "").replace(/\s*\(.*\)$/, ""), date: (o.creation_date || "").replace(/\s*\(.*$/, ""), img: o.images.web.url, link: o.url, src: "Cleveland Museum of Art", lic: "CC0" };
    });
  }
  var retries = 0;
  function fresh() {
    fromCleveland().catch(fromCleveland).catch(fromCleveland).catch(fromCleveland).catch(fromCleveland).then(function (a) { a.day = today; store.set("art", a); showArt(a); }).catch(function () { if (art) showArt(art); });
  }
  if (art && art.day === today && art.src.indexOf("Cleveland") === 0) showArt(art);
  else {
    fresh();
  }
  document.addEventListener("click", function (e) {
    if (!e.target.classList.contains("art-toggle")) return;
    var off = !root.classList.contains("no-art");
    root.classList.toggle("no-art", off); store.set("art-off", off);
    e.target.textContent = off ? "show art" : "hide art";
  });
})();
