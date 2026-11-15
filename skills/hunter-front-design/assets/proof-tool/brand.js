(() => {
  const brand = document.querySelector('.header .brand');
  if (brand && !brand.querySelector('.hunter-brand-logo')) {
    const logo = document.createElement('img');
    logo.className = 'hunter-brand-logo';
    logo.src = './brand/hunter-brand-dark.png';
    logo.alt = 'AIGC创意猎人';
    brand.prepend(logo);
  }
  const sidebar = document.querySelector('.sidebar');
  if (!sidebar || sidebar.querySelector('.proof-attribution')) return;
  const controls = document.createElement('div');
  controls.className = 'proof-controls';
  while (sidebar.firstChild) controls.append(sidebar.firstChild);
  sidebar.append(controls);
  sidebar.classList.add('with-attribution');
  const panel = document.createElement('section');
  panel.className = 'proof-attribution';
  panel.setAttribute('aria-label', '公众号二维码与制作署名');
  panel.innerHTML = '<img class="proof-qr" src="./brand/wechat-qr.jpg" width="150" height="150" alt="AIGC创意猎人公众号二维码"><p class="proof-credit">Created by AIGC创意猎人</p>';
  sidebar.append(panel);
})();
