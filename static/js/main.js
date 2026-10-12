/**
 * Crime Data Analysis Prediction System
 * Main JavaScript - Common utilities and interactive behaviors
 */

'use strict';

// ============================================================
// CSRF Token Helper
// ============================================================
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
const csrfToken = getCookie('csrftoken');

// ============================================================
// Sidebar Toggle (Dashboard)
// ============================================================
function initSidebar() {
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.getElementById('mainContent');
  const hamburgerBtn = document.getElementById('hamburgerBtn');
  const sidebarOverlay = document.getElementById('sidebarOverlay');
  if (!sidebar) return;

  // Mobile: open/close with overlay
  function openSidebar() {
    sidebar.classList.add('mobile-open');
    sidebarOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
  function closeSidebar() {
    sidebar.classList.remove('mobile-open');
    sidebarOverlay.classList.remove('active');
    document.body.style.overflow = '';
  }

  if (hamburgerBtn) {
    hamburgerBtn.addEventListener('click', () => {
      if (window.innerWidth <= 991) {
        if (sidebar.classList.contains('mobile-open')) closeSidebar();
        else openSidebar();
      } else {
        // Desktop: collapse/expand
        sidebar.classList.toggle('collapsed');
        if (mainContent) mainContent.classList.toggle('sidebar-collapsed');
        localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
      }
    });
  }

  if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', closeSidebar);
  }

  // Restore desktop collapse state
  if (window.innerWidth > 991 && localStorage.getItem('sidebarCollapsed') === 'true') {
    sidebar.classList.add('collapsed');
    if (mainContent) mainContent.classList.add('sidebar-collapsed');
  }

  // Handle resize
  window.addEventListener('resize', () => {
    if (window.innerWidth > 991) {
      closeSidebar();
      document.body.style.overflow = '';
    }
  });
}

// ============================================================
// Active Nav Link
// ============================================================
function initActiveNavLink() {
  const currentPath = window.location.pathname;
  document.querySelectorAll('.nav-link-custom').forEach(link => {
    const href = link.getAttribute('href');
    if (href && href !== '/' && currentPath.startsWith(href)) {
      link.classList.add('active');
    } else if (href === '/' && currentPath === '/') {
      link.classList.add('active');
    }
  });
}

// ============================================================
// Public Navbar Scroll Effect
// ============================================================
function initNavbarScroll() {
  const navbar = document.querySelector('.public-navbar');
  if (!navbar) return;
  const onScroll = () => {
    navbar.classList.toggle('scrolled', window.scrollY > 50);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
}

// ============================================================
// Toast Notification System
// ============================================================
const Toast = {
  container: null,

  init() {
    this.container = document.getElementById('toastContainer');
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'toastContainer';
      this.container.className = 'toast-container-custom';
      document.body.appendChild(this.container);
    }
  },

  show(message, type = 'info', duration = 5000) {
    this.init();
    const icons = { success: 'bi-check-circle-fill', error: 'bi-x-circle-fill', warning: 'bi-exclamation-triangle-fill', info: 'bi-info-circle-fill' };
    const toast = document.createElement('div');
    toast.className = `custom-toast ${type}`;
    toast.innerHTML = `
      <i class="bi ${icons[type] || icons.info} toast-icon"></i>
      <div class="flex-grow-1">
        <div class="fw-600 fs-sm">${message}</div>
      </div>
      <button type="button" class="btn-close btn-close-sm ms-2" onclick="this.closest('.custom-toast').remove()"></button>
    `;
    this.container.appendChild(toast);
    if (duration > 0) {
      setTimeout(() => toast.remove(), duration);
    }
  },

  success(msg, d) { this.show(msg, 'success', d); },
  error(msg, d)   { this.show(msg, 'error', d); },
  warning(msg, d) { this.show(msg, 'warning', d); },
  info(msg, d)    { this.show(msg, 'info', d); },
};

// ============================================================
// Auto-dismiss Django Messages
// ============================================================
function initAutoDismissAlerts() {
  document.querySelectorAll('.alert.auto-dismiss').forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.5s ease';
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 500);
    }, 5000);
  });
}

// ============================================================
// Stat Counter Animation (countUp effect)
// ============================================================
function countUp(el, target, duration = 1800) {
  const start = 0;
  const startTime = performance.now();
  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    const current = Math.round(eased * target);
    el.textContent = current.toLocaleString();
    if (progress < 1) requestAnimationFrame(update);
    else el.textContent = target.toLocaleString();
  }
  requestAnimationFrame(update);
}

function initCounters() {
  const counters = document.querySelectorAll('[data-count]');
  if (!counters.length) return;
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && !entry.target.dataset.counted) {
        entry.target.dataset.counted = 'true';
        const target = parseInt(entry.target.dataset.count, 10);
        countUp(entry.target, target);
      }
    });
  }, { threshold: 0.3 });
  counters.forEach(c => observer.observe(c));
}

// ============================================================
// File Upload Drag-and-Drop
// ============================================================
function initFileUpload() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const previewArea = document.getElementById('filePreview');
  const previewName = document.getElementById('previewName');
  const previewSize = document.getElementById('previewSize');
  if (!dropzone || !fileInput) return;

  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
  }

  function showPreview(file) {
    if (previewArea) {
      previewArea.style.display = 'flex';
      if (previewName) previewName.textContent = file.name;
      if (previewSize) previewSize.textContent = formatBytes(file.size);
      dropzone.classList.add('has-file');
    }
  }

  dropzone.addEventListener('click', () => fileInput.click());
  dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('dragover'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', e => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) { fileInput.files = e.dataTransfer.files; showPreview(file); }
  });
  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) showPreview(fileInput.files[0]);
  });
}

// ============================================================
// Confirm Delete
// ============================================================
function initConfirmDelete() {
  document.querySelectorAll('[data-confirm]').forEach(btn => {
    btn.addEventListener('click', e => {
      const message = btn.dataset.confirm || 'Are you sure you want to delete this?';
      if (!confirm(message)) e.preventDefault();
    });
  });
}

// ============================================================
// Search with Debounce
// ============================================================
function debounce(fn, delay = 300) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
}

function initSearchDebounce() {
  const searchInputs = document.querySelectorAll('.debounce-search');
  searchInputs.forEach(input => {
    const target = input.dataset.target;
    if (!target) return;
    input.addEventListener('input', debounce(() => {
      const form = input.closest('form');
      if (form) form.submit();
    }, 400));
  });
}

// ============================================================
// Scroll-to-top Button
// ============================================================
function initScrollToTop() {
  const btn = document.getElementById('scrollToTop');
  if (!btn) return;
  window.addEventListener('scroll', () => {
    btn.classList.toggle('visible', window.scrollY > 400);
  }, { passive: true });
  btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
}

// ============================================================
// Password Show/Hide Toggle
// ============================================================
function initPasswordToggles() {
  document.querySelectorAll('.password-toggle').forEach(toggle => {
    toggle.addEventListener('click', () => {
      const input = document.getElementById(toggle.dataset.target);
      if (!input) return;
      const isText = input.type === 'text';
      input.type = isText ? 'password' : 'text';
      toggle.querySelector('i').className = isText ? 'bi bi-eye-slash' : 'bi bi-eye';
    });
  });
}

// ============================================================
// Smooth Anchor Scrolling
// ============================================================
function initSmoothAnchors() {
  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', e => {
      const id = link.getAttribute('href').slice(1);
      const target = document.getElementById(id);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
}

// ============================================================
// Tooltip Initialization (Bootstrap)
// ============================================================
function initTooltips() {
  const tooltipEls = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipEls.forEach(el => new bootstrap.Tooltip(el));
}

// ============================================================
// AJAX Helper
// ============================================================
function ajaxPost(url, data, onSuccess, onError) {
  const formData = data instanceof FormData ? data : new FormData();
  if (!(data instanceof FormData)) {
    Object.entries(data).forEach(([k, v]) => formData.append(k, v));
  }
  formData.append('csrfmiddlewaretoken', csrfToken);
  fetch(url, {
    method: 'POST',
    body: formData,
    headers: { 'X-CSRFToken': csrfToken }
  })
    .then(r => r.json())
    .then(onSuccess)
    .catch(onError || (err => console.error('AJAX error:', err)));
}

function ajaxGet(url, onSuccess, onError) {
  fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(r => r.json())
    .then(onSuccess)
    .catch(onError || (err => console.error('AJAX error:', err)));
}

// ============================================================
// Notification Badge (live update)
// ============================================================
function refreshNotificationCount() {
  const badge = document.getElementById('notifBadge');
  if (!badge) return;
  ajaxGet('/notifications/unread-count/', data => {
    if (data.count > 0) {
      badge.textContent = data.count;
      badge.style.display = 'flex';
    } else {
      badge.style.display = 'none';
    }
  });
}

// ============================================================
// DOM Ready — Initialize Everything
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  initSidebar();
  initActiveNavLink();
  initNavbarScroll();
  initAutoDismissAlerts();
  initCounters();
  initFileUpload();
  initConfirmDelete();
  initSearchDebounce();
  initScrollToTop();
  initPasswordToggles();
  initSmoothAnchors();
  initTooltips();

  // Refresh notification count every 60 seconds on dashboard pages
  if (document.getElementById('sidebar')) {
    refreshNotificationCount();
    setInterval(refreshNotificationCount, 60000);
  }
});

// Expose globals
window.Toast = Toast;
window.getCookie = getCookie;
window.csrfToken = csrfToken;
window.ajaxPost = ajaxPost;
window.ajaxGet = ajaxGet;
window.debounce = debounce;
