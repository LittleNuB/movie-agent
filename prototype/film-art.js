// Original procedural illustration and synthesized ambience for this UI demo.
// This is not generated footage, a model adapter, or a film-quality sample.
const W = 1200, H = 750;
const stars = Array.from({ length: 260 }, (_, i) => ({
  x: ((Math.sin(i * 12.9898 + 1) * 43758.5453) % 1 + 1) % 1 * W,
  y: ((Math.sin(i * 7.135 + 8) * 23421.42) % 1 + 1) % 1 * H,
  r: i % 8 === 0 ? 1.1 : .55,
}));

function ellipse(ctx, x, y, rx, ry, color) {
  ctx.fillStyle = color; ctx.beginPath(); ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2); ctx.fill();
}

function path(ctx, d, fill, stroke, width = 1) {
  const p = new Path2D(d);
  if (fill) { ctx.fillStyle = fill; ctx.fill(p); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke(p); }
}

export function drawFilm(canvas, seconds = 42, treatment = 'quiet', visual = false) {
  if (!canvas) return;
  if (canvas.width !== W) { canvas.width = W; canvas.height = H; }
  const c = canvas.getContext('2d');
  const shift = Math.sin(seconds / 25) * 12;
  const sunrise = Math.min(1, .32 + seconds / 130);
  const space = c.createLinearGradient(0, 0, W, H);
  space.addColorStop(0, '#031017'); space.addColorStop(.5, '#15252d'); space.addColorStop(1, '#1c303a');
  c.fillStyle = space; c.fillRect(0, 0, W, H);
  for (const s of stars) { c.globalAlpha = .3 + (s.r / 2); ellipse(c, s.x + shift, s.y, s.r, s.r, '#c6d4db'); }
  c.globalAlpha = 1;

  // A huge offset planet, its atmosphere and thin sunlit cloud bands.
  c.save(); c.translate(680 + shift, 990); c.rotate(-.17);
  c.shadowColor = '#5cacda'; c.shadowBlur = 48;
  ellipse(c, 0, 0, 1010, 704, '#6cbbdd'); c.shadowBlur = 0;
  ellipse(c, 0, 9, 1007, 705, '#488bad');
  const ocean = c.createLinearGradient(0, -650, 0, 0);
  ocean.addColorStop(0, '#698999'); ocean.addColorStop(.12, '#456b81'); ocean.addColorStop(.5, '#19374f'); ocean.addColorStop(1, '#071a27');
  ellipse(c, 0, 22, 1008, 706, ocean);
  c.beginPath(); c.ellipse(0, 22, 1008, 706, 0, 0, Math.PI * 2); c.clip();
  for (let i = 0; i < 50; i++) {
    c.strokeStyle = `rgba(177,196,198,${.02 + (i % 4) * .01})`; c.lineWidth = 4 + i % 11;
    c.beginPath(); c.moveTo(-950, -645 + i * 12);
    c.bezierCurveTo(-330, -610 + i * 10, 390, -740 + i * 8, 1150, -530 + i * 10); c.stroke();
  }
  for (let i = 0; i < 60; i++) {
    c.fillStyle = `rgba(173,157,107,${.04 + (i % 3) * .025})`;
    c.fillRect(Math.sin(i * 2) * 870, -530 + Math.cos(i * 7) * 70, 3, 1.5);
  }
  c.restore();

  const glow = c.createRadialGradient(990, 334, 2, 990, 334, 375);
  glow.addColorStop(0, `rgba(255,240,200,${sunrise})`);
  glow.addColorStop(.05, 'rgba(255,226,171,.88)'); glow.addColorStop(.25, 'rgba(236,173,91,.21)'); glow.addColorStop(1, 'rgba(241,180,90,0)');
  c.fillStyle = glow; c.fillRect(0, 0, W, H);
  c.fillStyle = 'rgba(255,239,200,.65)'; c.fillRect(800, 333, 390, 1);

  // Observatory frame: understated industrial scale rather than an effects overlay.
  const wall = c.createLinearGradient(0, 0, W, 0);
  wall.addColorStop(0, '#080f13'); wall.addColorStop(.5, '#0a151b'); wall.addColorStop(1, '#17242b');
  path(c, 'M0 0H1200V90L1080 54H160L65 170V660L0 750Z', wall, '#314047', 2);
  path(c, 'M0 0H146L70 170V750H0Z', '#0b1318', '#35444b', 2);
  path(c, 'M1170 0H1200V750H1100L1140 200Z', '#09141a', '#34434a', 2);
  path(c, 'M390 55L404 55L370 672L347 681Z', '#132129', '#43535a', 1);
  path(c, 'M0 700L1200 601V750H0Z', '#0a151b', '#4b5050', 2);
  path(c, 'M0 710L1200 615', null, '#28373b', 4);
  for (let i = 0; i < 10; i++) {
    c.fillStyle = '#26343a'; c.fillRect(16, 65 + i * 58, 28, 1);
    ellipse(c, 28, 60 + i * 58, 2, 2, '#546168');
  }
  // A lone astronaut from behind, with a warm reflected rim.
  c.save(); c.translate(470, 385 + Math.sin(seconds * .8) * 1.4);
  const suit = c.createLinearGradient(-140, 0, 130, 0);
  suit.addColorStop(0, '#17262f'); suit.addColorStop(.6, '#2a3840'); suit.addColorStop(.91, '#566064'); suit.addColorStop(1, '#a09075');
  path(c, 'M-82 33Q-126 54-139 142L-162 223Q-155 244-133 232L-94 159L-83 289L66 289L83 148L101 223Q115 240 128 222L116 128Q105 52 59 33Z', suit, '#4b565a', 1);
  path(c, 'M-66 72Q-70 37-65 11H47Q56 28 60 76Z', '#17272d', '#637277', 1.5);
  const helmet = c.createLinearGradient(-78, -95, 70, 50);
  helmet.addColorStop(0, '#15272f'); helmet.addColorStop(.6, '#344750'); helmet.addColorStop(.9, '#576767'); helmet.addColorStop(1, '#c9b694');
  ellipse(c, -6, -7, 79, 88, helmet);
  ellipse(c, -11, -17, 65, 65, '#15252e');
  path(c, 'M-71-28Q-40-88 39-55Q65-40 62-9', null, '#6d7777', 3);
  path(c, 'M-74 33Q-17 79 56 39L51 53Q-18 91-72 48Z', '#9d9c8d');
  const pack = c.createLinearGradient(-72, 60, 55, 200);
  pack.addColorStop(0, '#435159'); pack.addColorStop(1, '#192a32');
  path(c, 'M-76 69Q-8 49 57 72L67 206Q-1 231-77 212Z', pack, '#667073', 2);
  path(c, 'M-55 83L37 81L46 148L-58 154Z', '#253740', '#72807f', 1);
  path(c, 'M-58 164L48 161L50 193L-58 198Z', '#2b3c43', '#566468', 1);
  c.fillStyle = '#b6aaa0'; c.fillRect(-45, 100, 44, 5);
  c.fillStyle = '#7e9798'; c.fillRect(-45, 110, 25, 2);
  ellipse(c, 35, 181, 3, 3, '#e5b76e');
  path(c, 'M-92 100L-107 126M85 96L97 126M-105 144L-119 173', null, '#617174', 6);
  path(c, 'M-83 255L66 249L75 368H6L-9 294L-20 368H-91Z', '#192b34', '#34454c', 2);
  c.restore();

  // Small practical lamp and control desk.
  path(c, 'M740 624L1127 591L1173 687L759 731Z', '#14262e', '#4d595a', 2);
  path(c, 'M790 629L924 616L943 652L805 667Z', '#213c45', '#5c787c', 1);
  c.font = '9px monospace'; c.fillStyle = '#829c9b'; c.fillText(seconds > 75 ? 'SIGNAL RECEIVED' : 'AWAITING SIGNAL', 811, 640);
  path(c, 'M1015 616L1004 541L975 519', null, '#978d74', 4);
  path(c, 'M938 531L976 505L1009 526Z', '#cab187');
  const lamp = c.createRadialGradient(975, 532, 1, 975, 532, 76);
  lamp.addColorStop(0, 'rgba(245,192,111,.23)'); lamp.addColorStop(1, 'rgba(245,192,111,0)'); c.fillStyle = lamp; c.fillRect(890, 500, 160, 160);

  const vignette = c.createRadialGradient(650, 350, 180, 600, 375, 780);
  vignette.addColorStop(0, 'rgba(0,0,0,0)'); vignette.addColorStop(1, 'rgba(0,3,7,.62)'); c.fillStyle = vignette; c.fillRect(0, 0, W, H);
  if (!visual) {
    c.fillStyle = '#020608'; c.fillRect(0, 0, W, 45); c.fillRect(0, H - 45, W, 45);
    if (seconds > 75 && seconds < 90) {
      c.font = '20px "Microsoft YaHei", sans-serif'; c.textAlign = 'center'; c.fillStyle = '#e8e8df';
      c.fillText('妈妈看见了。', W / 2, H - 73); c.textAlign = 'left';
    }
  }
}

export class DemoSound {
  constructor() { this.context = null; this.nodes = []; this.active = false; }
  async start() {
    if (!this.context) this.context = new AudioContext();
    await this.context.resume();
    if (this.active) return;
    this.active = true;
    for (const [freq, gain] of [[55, .025], [82.4, .012], [164.8, .006]]) {
      const oscillator = this.context.createOscillator(); const volume = this.context.createGain();
      oscillator.frequency.value = freq; volume.gain.value = gain;
      oscillator.connect(volume).connect(this.context.destination); oscillator.start();
      this.nodes.push(oscillator);
    }
  }
  stop() { this.nodes.forEach(n => n.stop()); this.nodes = []; this.active = false; }
}
