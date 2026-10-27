(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const bulan = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];

  function relatif(d) {
    const menit = Math.floor((Date.now() - d.getTime()) / 60000);
    if (menit < 1) return 'baru';
    if (menit < 60) return menit + ' mnt';
    const jam = Math.floor(menit / 60);
    if (jam < 24) return jam + ' j';
    const hari = Math.floor(jam / 24);
    if (hari < 30) return hari + ' h';
    return d.getDate() + ' ' + bulan[d.getMonth()] + ' ' + d.getFullYear();
  }

  $$('.box time[datetime]').forEach((t) => {
    const d = new Date(t.getAttribute('datetime'));
    if (!isNaN(d)) {
      t.title = d.toLocaleString('id-ID');
      t.textContent = relatif(d);
    }
  });

  const cari = $('#cari');
  const tombol = $$('.lang button');
  let bahasa = 'all';
  try { bahasa = localStorage.getItem('wartahayati.bahasa') || 'all'; } catch (e) { /* penyimpanan tidak tersedia */ }

  const normal = (s) => s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');

  function terapkan() {
    const q = normal(cari.value.trim());
    tombol.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.lang === bahasa)));
    $$('.box').forEach((box) => {
      let tampak = 0;
      $$('li', box).forEach((li) => {
        const cocok = !q || normal(li.textContent).includes(q);
        li.hidden = !cocok;
        if (cocok) tampak++;
      });
      box.hidden = (bahasa !== 'all' && box.dataset.lang !== bahasa) || (q !== '' && tampak === 0);
    });
    $$('section.topik').forEach((s) => { s.hidden = $$('.box:not([hidden])', s).length === 0; });
    const ada = $$('.box:not([hidden])').length > 0 || $$('.box').length === 0;
    const pesan = $('#tidak-ada');
    if (pesan) pesan.hidden = ada;
  }

  tombol.forEach((b) => b.addEventListener('click', () => {
    bahasa = b.dataset.lang;
    try { localStorage.setItem('wartahayati.bahasa', bahasa); } catch (e) { /* abaikan */ }
    terapkan();
  }));
  cari.addEventListener('input', terapkan);
  terapkan();
})();
