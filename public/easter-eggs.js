// sanctum.run — easter eggs
// Nothing here changes what the site *does*. Everything here changes what
// the site *feels like* if you wander the right way.
//
// Triggers:
//   1. Konami Code (↑ ↑ ↓ ↓ ← → ← → B A) — Matrix digital rain + a Zelda
//      "It's dangerous to go alone" flash card.
//   2. DevTools open — green console greeting with a hint.
//   3. Type the word "neo" anywhere — short glitch on the nearest heading.
//   4. /redpill/  — hidden page, Matrix-themed, not in the sidebar.

(function () {
  'use strict';

  // ───────────────────────────── console greeting ───────────────────────
  const greet = [
    '%c       _   _            _    _                _    _               _       _\n' +
    '%c      | | / /           | |  ( )              | |  ( )             | |     | |\n' +
    '%c      | |/ / _ __   ___ | |_ |/  ___          | |_ |/ ___   ___    | |__   | | __\n' +
    '%c      |   \\ | \\__\\ / _ \\| \\__\\  / __|          \\__\\  / _ \\ / _ \\   | \\__\\  | |/ /\n' +
    '%c      | |\\ \\| | | | (_) | |_     (__           _ | | (_) | (_) |  | |_    |   <\n' +
    '%c      \\_| \\_|_| |_|\\___/ \\__|   \\___|         \\__||_|\\___/ \\___/   \\__|   |_|\\_\\',
  ];
  const line = (t) =>
    console.log(
      '%c' + t,
      'color:#39ff14;font-family:ui-monospace,Menlo,monospace;font-size:13px;text-shadow:0 0 6px #39ff14'
    );
  line('Knock knock, Neo.');
  line('Follow the white rabbit.  →  /redpill/');
  line('Konami is the key.');

  // ───────────────────────────── konami sequence ────────────────────────
  const KONAMI = [
    'ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown',
    'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight',
    'b', 'a',
  ];
  let cursor = 0;
  let running = false;

  window.addEventListener('keydown', (e) => {
    const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
    if (key === KONAMI[cursor]) {
      cursor++;
      if (cursor === KONAMI.length) {
        cursor = 0;
        if (!running) matrixRain();
      }
    } else {
      cursor = key === KONAMI[0] ? 1 : 0;
    }
  }, { passive: true });

  // ───────────────────────────── matrix rain + zelda flash ──────────────
  function matrixRain() {
    running = true;
    const c = document.createElement('canvas');
    Object.assign(c.style, {
      position: 'fixed', inset: '0', zIndex: '2147483646',
      pointerEvents: 'none', transition: 'opacity 800ms ease-out', opacity: '1',
    });
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    c.width = window.innerWidth * dpr;
    c.height = window.innerHeight * dpr;
    c.style.width = window.innerWidth + 'px';
    c.style.height = window.innerHeight + 'px';
    document.body.appendChild(c);
    const ctx = c.getContext('2d');
    ctx.scale(dpr, dpr);

    const cellW = 16;
    const cols = Math.ceil(window.innerWidth / cellW);
    const drops = Array.from({ length: cols }, () => Math.random() * -40);
    const glyphs =
      'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロ0123456789ΣΔΩ<>/\\:;.';

    const flash = document.createElement('div');
    flash.textContent = "It's dangerous to go alone. Take this.";
    Object.assign(flash.style, {
      position: 'fixed', top: '50%', left: '50%',
      transform: 'translate(-50%,-50%)',
      color: '#39ff14', fontFamily: 'ui-monospace,Menlo,monospace',
      fontSize: 'clamp(18px, 2.6vw, 30px)', letterSpacing: '0.08em',
      textShadow: '0 0 14px #39ff14, 0 0 28px rgba(57,255,20,0.5)',
      zIndex: '2147483647', pointerEvents: 'none',
      opacity: '0', transition: 'opacity 900ms ease',
    });
    document.body.appendChild(flash);
    requestAnimationFrame(() => (flash.style.opacity = '1'));

    const started = performance.now();
    const DURATION = 7500;

    function frame(now) {
      const elapsed = now - started;
      ctx.fillStyle = 'rgba(0,0,0,0.08)';
      ctx.fillRect(0, 0, window.innerWidth, window.innerHeight);
      ctx.font = '15px ui-monospace, Menlo, monospace';
      for (let i = 0; i < drops.length; i++) {
        const y = drops[i] * 16;
        const ch = glyphs[(Math.random() * glyphs.length) | 0];
        ctx.fillStyle = y < 18 ? '#ccffcc' : '#39ff14';
        ctx.fillText(ch, i * cellW, y);
        if (y > window.innerHeight && Math.random() > 0.975) drops[i] = 0;
        drops[i]++;
      }
      if (elapsed < DURATION) {
        requestAnimationFrame(frame);
      } else {
        c.style.opacity = '0';
        flash.style.opacity = '0';
        setTimeout(() => {
          c.remove(); flash.remove(); running = false;
        }, 900);
      }
    }
    requestAnimationFrame(frame);
  }

  // ───────────────────────────── neo / zelda word triggers ──────────────
  let buffer = '';
  const WORD_TRIGGERS = {
    neo:   () => glitchNearestHeading('#39ff14'),
    zelda: () => glitchNearestHeading('#ffd700'),
  };
  window.addEventListener('keydown', (e) => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key.length !== 1) { buffer = ''; return; }
    buffer = (buffer + e.key.toLowerCase()).slice(-8);
    for (const word in WORD_TRIGGERS) {
      if (buffer.endsWith(word)) { WORD_TRIGGERS[word](); buffer = ''; return; }
    }
  }, { passive: true });

  function glitchNearestHeading(color) {
    const h = document.querySelector('h1, h2, h3');
    if (!h) return;
    const orig = h.textContent;
    const chars = orig.split('');
    const glyphs = 'アイウエオ0123456789<>/\\:;.';
    let i = 0;
    const id = setInterval(() => {
      const out = chars.map((c, j) =>
        j < i ? c : (c === ' ' ? ' ' : glyphs[(Math.random() * glyphs.length) | 0])
      ).join('');
      h.textContent = out;
      i++;
      if (i > chars.length) {
        clearInterval(id);
        h.textContent = orig;
        h.style.transition = 'color 400ms';
        const was = getComputedStyle(h).color;
        h.style.color = color;
        setTimeout(() => (h.style.color = was), 700);
      }
    }, 30);
  }
})();
