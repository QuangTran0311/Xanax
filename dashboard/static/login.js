  const THEME_ICONS = {
    sun: '<circle cx="12" cy="12" r="4.2"/><path d="M12 3v2.2M12 18.8V21M4.2 12H2M22 12h-2.2M5.6 5.6l1.5 1.5M16.9 16.9l1.5 1.5M18.4 5.6l-1.5 1.5M7.1 16.9l-1.5 1.5"/>',
    moon: '<path d="M20 13.5A8.5 8.5 0 119.7 3.2 6.8 6.8 0 0020 13.5z"/>',
  };

  function applyTheme(theme) {
    document.body.classList.toggle('light', theme === 'light');
    const btn = document.getElementById('theme-toggle-btn');
    if (btn) {
      const iconName = theme === 'light' ? 'moon' : 'sun';
      btn.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true">${THEME_ICONS[iconName]}</svg>`;
      btn.setAttribute('aria-label', theme === 'light' ? 'Chuyển sang giao diện tối' : 'Chuyển sang giao diện sáng');
      btn.title = btn.getAttribute('aria-label');
    }
    localStorage.setItem('hub_theme', theme);
  }

  function toggleTheme() {
    const current = document.body.classList.contains('light') ? 'light' : 'dark';
    applyTheme(current === 'light' ? 'dark' : 'light');
  }

  applyTheme(localStorage.getItem('hub_theme') || 'light');

  let loading = false;
  let showPassword = false;

  if (new URLSearchParams(location.search).get('reason') === 'idle') {
    document.getElementById('error-msg').textContent = 'Phiên làm việc đã hết hạn do không có thao tác. Vui lòng đăng nhập lại.';
    document.getElementById('error-msg').classList.add('visible');
  }

  const usernameEl = document.getElementById('username');
  const passwordEl = document.getElementById('password');
  const submitBtn  = document.getElementById('submit-btn');
  const btnText    = document.getElementById('btn-text');
  const btnArrow   = document.getElementById('btn-arrow');
  const errorEl    = document.getElementById('error-msg');
  const toggleBtn  = document.getElementById('toggle-pw');
  const eyeIcon    = document.getElementById('eye-icon');
  const fieldsEl   = document.getElementById('fields');

  toggleBtn.addEventListener('click', () => {
    showPassword = !showPassword;
    passwordEl.type = showPassword ? 'text' : 'password';
    eyeIcon.innerHTML = showPassword
      ? `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
         <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
         <line x1="1" y1="1" x2="23" y2="23"/>`
      : `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
         <circle cx="12" cy="12" r="3"></circle>`;
  });

  [usernameEl, passwordEl].forEach(el => {
    el.addEventListener('keydown', e => {
      if (e.key === 'Enter') handleLogin();
    });
  });

  function setLoading(val) {
    loading = val;
    submitBtn.disabled = val;
    if (val) {
      btnText.textContent = 'Đang xác thực...';
      btnArrow.style.display = 'none';
      const spinner = document.createElement('div');
      spinner.className = 'spinner';
      spinner.id = 'spinner';
      submitBtn.appendChild(spinner);
    } else {
      btnText.textContent = 'Đăng nhập';
      btnArrow.style.display = '';
      const sp = document.getElementById('spinner');
      if (sp) sp.remove();
    }
  }

  function showError(msg) {
    errorEl.textContent = msg;
    errorEl.classList.add('visible');
    fieldsEl.classList.remove('shake');
    void fieldsEl.offsetWidth;
    fieldsEl.classList.add('shake');
    setTimeout(() => fieldsEl.classList.remove('shake'), 400);
  }

  function clearError() {
    errorEl.classList.remove('visible');
  }

  async function handleLogin() {
    if (loading) return;

    const username = usernameEl.value.trim();
    const password = passwordEl.value;

    if (!username) {
      showError('Vui lòng nhập tài khoản.');
      usernameEl.focus();
      return;
    }
    if (!password) {
      showError('Vui lòng nhập mật khẩu.');
      passwordEl.focus();
      return;
    }

    clearError();
    setLoading(true);

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (res.ok) {
        window.location.href = '/hub';
      } else {
        const data = await res.json().catch(() => ({}));
        showError(data.detail || data.message || 'Tài khoản hoặc mật khẩu không đúng.');
      }
    } catch (err) {
      showError('Không thể kết nối đến máy chủ. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  }
