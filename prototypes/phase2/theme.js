// Add a theme by copying a themes/*.css file and registering its name here.
(() => {
  const themes = {storybook: 'Storybook', gothic: 'Gothic', cyberpunk: 'Cyberpunk', noir: 'Noir', medieval: 'Medieval'};
  const key = 'story-atlas-phase2-theme';
  let current = 'storybook';
  try { const stored = localStorage.getItem(key); if (Object.hasOwn(themes, stored)) current = stored; } catch {}
  const apply = name => {
    document.querySelector('#theme-stylesheet').href = `themes/${name}.css?v=15`;
    document.documentElement.dataset.theme = name;
  };
  apply(current);
  document.addEventListener('DOMContentLoaded', () => {
    const select = document.querySelector('#theme-select');
    for (const [value, label] of Object.entries(themes)) select.add(new Option(label, value));
    select.value = current;
    select.addEventListener('change', () => {
      apply(select.value);
      try { localStorage.setItem(key, select.value); } catch { /* Theme remains usable for this session. */ }
    });
  });
})();
