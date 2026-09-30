// Ingen iframe, DNS-prefetch, preconnect eller leverantörsbegäran före valet.
const knapp = document.getElementById('visa-karta');
knapp.hidden = false;
knapp.addEventListener('click', () => {
  const url = new URL(knapp.dataset.kartUrl);
  if (url.protocol !== 'https:') return;
  const karta = document.createElement('iframe');
  karta.title = 'Karta till ' + document.getElementById('adress').textContent;
  karta.width = '600'; karta.height = '350'; karta.style.maxWidth = '100%';
  karta.src = url.href;
  document.getElementById('karta').replaceChildren(karta);
  knapp.disabled = true;
}, { once: true });
