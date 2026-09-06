export const STORAGE_KEY = 'movie-agent.prototype.v1';
export const uid = () => globalThis.crypto.randomUUID();
export const clockTime = n => `${String(Math.floor(n / 60)).padStart(2, '0')}:${String(Math.floor(n % 60)).padStart(2, '0')}`;
export const script = `最后一束光

01  轨道中继站 · 观测舱 · 日出前

地球占满观察窗。海岸线沉在黑暗里。林遥用指节敲了敲一盏旧台灯，灯丝短暂地亮起。
控制台提示：返航窗口剩余 100 秒。

林遥（低声）：再等一下。

02  中继站 · 通讯台

一段十年前的语音从噪声里浮出。女儿说，海边的灯塔坏了，今晚她会点一盏灯。
林遥抬头看着地球。系统请求撤离确认。她移开手，把返航舱的备用电源接入发射器。
报警声停止，只剩继电器闭合的轻响。

03  观测舱 · 日出

阳光越过地球边缘，缓慢照亮她的手。屏幕上出现一行字：信号已抵达。
她关掉台灯。遥远海岸上的一点光，刚好亮了起来。

声音：开场保留舱体低鸣与呼吸。收到回执后，三颗疏落的钢琴音进入。最后停留在环境声中。`;

export const proposal = `最后一束光

一位驻守轨道中继站的母亲，在最后一次撤离窗口里，收到女儿十年前留下的语音。她只有一百秒，决定把最后一点电留给返航，还是送出一条迟到的回答。

完整故事

地球的夜面悬在舷窗外。林遥敲亮一盏旧台灯，控制台开始返航倒计时。她收拾好行囊，却在通讯噪声里听见女儿的声音：海边的灯塔坏了，今晚她会点一盏灯。

那是十年前没有送达的语音。她停在撤离确认键前，把行囊放回椅子。中继站的主电源即将切断，备用电源只够再发送一次信号。

林遥拔下返航舱的备用电缆，将它接到发射器。她没有说很多话，只回答：妈妈看见了。等待回执时，太阳越过地球边缘。屏幕终于亮起“信号已抵达”。

她关掉台灯。画面落在遥远的海岸，一点光刚好亮起。我们不说明女儿此刻在哪里，让这次抵达成为结尾。

准备怎样拍

约 100 秒。让人先看到她的手、灯和选择，再看到太空的尺度。冷色舱壁与日出的暖光相遇；大部分时间保留呼吸、机器低鸣和静默。音乐在回执出现后才进入。`;

export const modeLabel = mode => ({ co: '共创', auto: '托管', audio: '共创 · 声音已托管' }[mode]);
export const modeDescription = mode => ({ co: '关键内容由你审核，修改先讨论再执行。', auto: '已授权导演推进示例故事、画面和声音；你可以随时插话或停止。', audio: '声音修改可直接推进；故事与画面继续由你审核。' }[mode]);
export const director = (text, extra = {}) => ({ id: uid(), role: 'director', text, ...extra });
export const user = (text, extra = {}) => ({ id: uid(), role: 'user', text, ...extra });
export const stamp = () => new Date().toISOString();

export function createProject(title, mode = 'co') {
  return {
    id: uid(), title, mode, updated: Date.now(), stage: 'proposal',
    messages: [], proposal, draftScript: script, appliedScript: '', scriptAvailable: false,
    visualReady: false, versions: [], adoptedId: null, pending: null,
    tabs: [], activeTab: null, workOpen: false, manuallyClosed: false,
    composer: '', annotations: [], playheads: {}, draftBackups: [], task: null, pausedTask: null,
  };
}

export function makeReview(p, kind, text, extra = {}) {
  const review = { id: uid(), kind, text, ...extra };
  p.pending = review;
  p.messages.push(director(text, { review: { ...review } }));
  return review;
}

export function openTab(p, kind, id = '', explicit = true) {
  if (!explicit && (p.manuallyClosed || p.activeTab)) return;
  const key = `${kind}:${id}`;
  if (!p.tabs.some(t => t.key === key)) p.tabs.push({ key, kind, id });
  p.activeTab = key; p.workOpen = true;
  if (explicit) p.manuallyClosed = false;
}

export function initialState() {
  const p = createProject('最后一束光');
  p.stage = 'trial'; p.scriptAvailable = true; p.appliedScript = script; p.visualReady = true;
  const v1 = { id: uid(), number: 1, title: '试拍', note: '日出前的等待 · 初次试拍', script, created: stamp(), treatment: 'original' };
  const v2 = { id: uid(), number: 2, title: '试拍', note: '音乐延后进入，保留舱内环境声', script, created: stamp(), treatment: 'quiet', parentId: v1.id };
  p.versions = [v1, v2]; p.adoptedId = v2.id; p.playheads[v2.id] = 42;
  p.messages = [
    user('我想拍一个宇宙里很小的故事。一个人等一束迟来的光，安静一点，最后有一点希望。'),
    director('我们把故事落在一位母亲的选择上：她要放弃的东西越具体，最后的那一点光才越有分量。提案、剧本和视觉方向都可以在作品里查看。', { assets: ['proposal', 'script', 'visual'] }),
    user('我想让这个片段更安静一些。'),
    director('我保留了环境声，让音乐在最后进入。镜头多停留了一会儿，把等待的时间留给她。', { assets: ['video'], versionId: v2.id }),
  ];
  makeReview(p, 'trial', '这版先看画面停留和声音进入的节奏。你认可后，我会沿着这个方向完成影片。', { versionId: v2.id });
  openTab(p, 'script'); openTab(p, 'visual'); openTab(p, 'video', v2.id);
  const second = createProject('深空回响');
  second.messages = [user('如果太空里收到自己的回声，它会说什么？'), director('这个问题很适合从一次误认开始。我们先聊聊：你更希望结尾带来安慰，还是不安？本项目用于演示切换后对话与草稿的保留。')];
  second.composer = '我想要一种温柔的不安。';
  return { schema: 1, activeId: null, theme: 'system', navOpen: true, defaultMode: 'co', configured: false, projects: [p, second], welcomeDraft: '' };
}

export function load() {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (value?.schema === 1 && Array.isArray(value.projects)) {
      // Migrate only the known initial sample message; never guess a history link
      // from whichever version is currently adopted.
      for (const p of value.projects) for (const m of p.messages) {
        if (!m.versionId && m.assets?.includes('video') && m.text === '我保留了环境声，让音乐在最后进入。镜头多停留了一会儿，把等待的时间留给她。') m.versionId = p.versions.find(v => v.number === 2)?.id;
      }
      return value;
    }
  } catch { /* A broken or unavailable browser store must not prevent opening the demo. */ }
  return initialState();
}

export function save(value) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(value)); return true; }
  catch { return false; }
}
