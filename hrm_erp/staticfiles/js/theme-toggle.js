// Theme Toggle Logic
document.addEventListener('DOMContentLoaded', () => {
  const themeToggle = document.getElementById('theme-toggle-btn');
  const themeIcon = document.getElementById('theme-toggle-icon');
  
  // Check persisted theme or system default
  const savedTheme = localStorage.getItem('theme');
  const userPrefersLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
  
  let currentTheme = savedTheme || (userPrefersLight ? 'light' : 'dark');
  
  // Set theme on HTML tag
  document.documentElement.setAttribute('data-theme', currentTheme);
  updateThemeUI(currentTheme);
  
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', currentTheme);
      localStorage.setItem('theme', currentTheme);
      updateThemeUI(currentTheme);
    });
  }
  
  function updateThemeUI(theme) {
    if (!themeIcon) return;
    if (theme === 'light') {
      themeIcon.textContent = '🌙'; // Icon to change to Dark
    } else {
      themeIcon.textContent = '☀️'; // Icon to change to Light
    }
  }
});
