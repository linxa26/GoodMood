document.addEventListener('click', e => {
  const el = e.target.closest('button, a');
  if (!el) return;

  // убираем предыдущий след, если был
  el.classList.remove('dusty');
  void el.offsetWidth; // триггер перерисовки
  el.classList.add('dusty');
});
