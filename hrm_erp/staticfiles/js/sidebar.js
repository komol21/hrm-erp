// Sidebar toggling for mobile layout
document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('app-sidebar');
  const mobileToggle = document.getElementById('mobile-menu-toggle');
  const closeSidebarBtn = document.getElementById('close-sidebar-btn');
  
  if (mobileToggle && sidebar) {
    mobileToggle.addEventListener('click', () => {
      sidebar.classList.toggle('active');
    });
  }
  
  if (closeSidebarBtn && sidebar) {
    closeSidebarBtn.addEventListener('click', () => {
      sidebar.classList.remove('active');
    });
  }
  
  // Close sidebar on window resize if larger than tablet breakpoint
  window.addEventListener('resize', () => {
    if (window.innerWidth > 1024 && sidebar) {
      sidebar.classList.remove('active');
    }
  });
});
