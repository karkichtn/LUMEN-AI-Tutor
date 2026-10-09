/**
 * LUMEN — Conversational AI Application Controller
 * Minimalist ChatGPT-inspired Architecture with Real Auth,
 * Persistent Chat History, Multilingual Tutoring, and Plus UPI Payment System.
 */

(function () {
  'use strict';

  // ==========================================================================
  // Application State
  // ==========================================================================
  const state = {
    token: localStorage.getItem('lumen_auth_token') || null,
    user: null, // { id, email, display_name, plan, role }
    activeConversationId: null,
    conversations: [],
    selectedLanguage: 'auto',
    lastJsonResponse: null,
    isProcessing: false,
    soundEnabled: localStorage.getItem('lumen_sound_enabled') === 'true',
    jsonInspectorOpen: false
  };

  // ==========================================================================
  // DOM Elements
  // ==========================================================================
  // Layout & Sidebar
  const sidebar = document.getElementById('sidebar');
  const sidebarBackdrop = document.getElementById('sidebarBackdrop');
  const mobileMenuBtn = document.getElementById('mobileMenuBtn');
  const sidebarCollapseBtn = document.getElementById('sidebarCollapseBtn');
  const newChatBtn = document.getElementById('newChatBtn');
  const conversationSearchInput = document.getElementById('conversationSearchInput');

  // Groups
  const itemsToday = document.getElementById('itemsToday');
  const itemsYesterday = document.getElementById('itemsYesterday');
  const itemsPrevious7 = document.getElementById('itemsPrevious7');
  const itemsOlder = document.getElementById('itemsOlder');
  const emptyConversationsState = document.getElementById('emptyConversationsState');
  const groupToday = document.getElementById('groupToday');
  const groupYesterday = document.getElementById('groupYesterday');
  const groupPrevious7 = document.getElementById('groupPrevious7');
  const groupOlder = document.getElementById('groupOlder');

  // Account
  const accountCardBtn = document.getElementById('accountCardBtn');
  const accountAvatar = document.getElementById('accountAvatar');
  const accountName = document.getElementById('accountName');
  const accountEmail = document.getElementById('accountEmail');
  const accountPlanBadge = document.getElementById('accountPlanBadge');
  const accountMenu = document.getElementById('accountMenu');
  const menuUserName = document.getElementById('menuUserName');
  const menuUserPlan = document.getElementById('menuUserPlan');
  const menuUpgradeBtn = document.getElementById('menuUpgradeBtn');
  const menuUpgradeLabel = document.getElementById('menuUpgradeLabel');
  const menuAdminBtn = document.getElementById('menuAdminBtn');
  const menuSettingsBtn = document.getElementById('menuSettingsBtn');
  const menuAuthBtn = document.getElementById('menuAuthBtn');
  const menuAuthLabel = document.getElementById('menuAuthLabel');
  const topAuthBtn = document.getElementById('topAuthBtn');
  const modelTierBadge = document.getElementById('modelTierBadge');

  // Chat Area
  const chatViewport = document.getElementById('chatViewport');
  const welcomeContainer = document.getElementById('welcomeContainer');
  const messagesStream = document.getElementById('messagesStream');
  const scrollAnchor = document.getElementById('scrollAnchor');
  const chatForm = document.getElementById('chatForm');
  const messageInput = document.getElementById('messageInput');
  const sendBtn = document.getElementById('sendBtn');
  const voiceBtn = document.getElementById('voiceBtn');
  const attachmentBtn = document.getElementById('attachmentBtn');
  const languageSelect = document.getElementById('languageSelect');
  const audioToggleBtn = document.getElementById('audioToggleBtn');
  const audioStatusText = document.getElementById('audioStatusText');

  // JSON Drawer
  const jsonInspectorToggleBtn = document.getElementById('jsonInspectorToggleBtn');
  const jsonDrawer = document.getElementById('jsonDrawer');
  const closeJsonDrawerBtn = document.getElementById('closeJsonDrawerBtn');
  const jsonPreCode = document.getElementById('jsonPreCode');
  const jsonMeta = document.getElementById('jsonMeta');
  const copyJsonBtn = document.getElementById('copyJsonBtn');

  // Modals
  // 1. Auth Modal
  const authModalBackdrop = document.getElementById('authModalBackdrop');
  const closeAuthModalBtn = document.getElementById('closeAuthModalBtn');
  const authTabLogin = document.getElementById('authTabLogin');
  const authTabRegister = document.getElementById('authTabRegister');
  const nameFormGroup = document.getElementById('nameFormGroup');
  const confirmPasswordGroup = document.getElementById('confirmPasswordGroup');
  const authForm = document.getElementById('authForm');
  const authNameInput = document.getElementById('authNameInput');
  const authEmailInput = document.getElementById('authEmailInput');
  const authPasswordInput = document.getElementById('authPasswordInput');
  const authConfirmPasswordInput = document.getElementById('authConfirmPasswordInput');
  const pwToggleBtn = document.getElementById('pwToggleBtn');
  const authAlert = document.getElementById('authAlert');
  const authSubmitBtn = document.getElementById('authSubmitBtn');
  let authMode = 'login'; // 'login' | 'register'

  // 2. Plus Modal
  const plusModalBackdrop = document.getElementById('plusModalBackdrop');
  const closePlusModalBtn = document.getElementById('closePlusModalBtn');
  const paymentStatusBanner = document.getElementById('paymentStatusBanner');
  const paymentSubmissionForm = document.getElementById('paymentSubmissionForm');
  const utrInput = document.getElementById('utrInput');
  const screenshotInput = document.getElementById('screenshotInput');
  const submitPaymentBtn = document.getElementById('submitPaymentBtn');

  // 3. Admin Modal
  const adminModalBackdrop = document.getElementById('adminModalBackdrop');
  const closeAdminModalBtn = document.getElementById('closeAdminModalBtn');
  const adminRequestsList = document.getElementById('adminRequestsList');

  // 4. Settings Modal
  const settingsModalBackdrop = document.getElementById('settingsModalBackdrop');
  const closeSettingsModalBtn = document.getElementById('closeSettingsModalBtn');
  const settingsSoundToggle = document.getElementById('settingsSoundToggle');
  const settingsJsonToggle = document.getElementById('settingsJsonToggle');
  const settingsPlanDesc = document.getElementById('settingsPlanDesc');
  const settingsPlanBadge = document.getElementById('settingsPlanBadge');

  // ==========================================================================
  // Configure Marked & Highlight.js
  // ==========================================================================
  if (window.marked) {
    marked.setOptions({
      breaks: true,
      gfm: true,
      highlight: function (code, lang) {
        if (window.hljs) {
          const validLang = lang && hljs.getLanguage(lang) ? lang : 'plaintext';
          return hljs.highlight(code, { language: validLang }).value;
        }
        return code;
      }
    });
  }

  // ==========================================================================
  // Helper Utilities
  // ==========================================================================
  function escapeHtml(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function getInitials(name) {
    if (!name) return 'U';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return parts[0].substring(0, 2).toUpperCase();
  }

  function scrollToBottom() {
    if (scrollAnchor) {
      scrollAnchor.scrollIntoView({ behavior: 'smooth' });
    }
  }

  async function apiFetch(url, options = {}) {
    options.headers = options.headers || {};
    if (state.token) {
      options.headers['Authorization'] = `Bearer ${state.token}`;
    }
    const res = await fetch(url, options);
    return res;
  }

  // ==========================================================================
  // Audio Controller
  // ==========================================================================
  function updateAudioUI() {
    if (audioStatusText) {
      audioStatusText.textContent = state.soundEnabled ? 'Audio On' : 'Audio Off';
    }
    if (settingsSoundToggle) {
      settingsSoundToggle.textContent = state.soundEnabled ? 'On' : 'Off';
    }
  }

  if (audioToggleBtn) {
    audioToggleBtn.addEventListener('click', () => {
      state.soundEnabled = !state.soundEnabled;
      localStorage.setItem('lumen_sound_enabled', state.soundEnabled);
      if (window.audioManager) window.audioManager.enabled = state.soundEnabled;
      updateAudioUI();
    });
  }

  if (settingsSoundToggle) {
    settingsSoundToggle.addEventListener('click', () => {
      state.soundEnabled = !state.soundEnabled;
      localStorage.setItem('lumen_sound_enabled', state.soundEnabled);
      if (window.audioManager) window.audioManager.enabled = state.soundEnabled;
      updateAudioUI();
    });
  }

  // ==========================================================================
  // Authentication & User Session
  // ==========================================================================
  async function checkCurrentUser() {
    if (!state.token) {
      renderUserGuest();
      return;
    }

    try {
      const res = await apiFetch('/api/auth/me');
      if (res.ok) {
        const data = await res.json();
        state.user = data.user;
        renderUserLoggedIn(state.user);
        loadConversations();
      } else {
        // Token expired or invalid
        localStorage.removeItem('lumen_auth_token');
        state.token = null;
        state.user = null;
        renderUserGuest();
      }
    } catch (e) {
      console.warn('Network issue fetching user profile', e);
      renderUserGuest();
    }
  }

  function renderUserLoggedIn(user) {
    accountAvatar.textContent = getInitials(user.display_name || user.email);
    accountName.textContent = user.display_name || user.email.split('@')[0];
    accountEmail.textContent = user.email;
    
    const isPlus = user.plan === 'plus';
    accountPlanBadge.textContent = isPlus ? 'Plus' : 'Free';
    accountPlanBadge.className = isPlus ? 'plan-badge plus' : 'plan-badge';

    modelTierBadge.textContent = isPlus ? 'Plus Priority' : 'Standard';
    if (isPlus) {
      modelTierBadge.style.color = '#e5b869';
    } else {
      modelTierBadge.style.color = '#888888';
    }

    menuUserName.textContent = user.display_name || user.email.split('@')[0];
    menuUserPlan.textContent = isPlus ? 'LUMEN PLUS — ACTIVE (Lifetime)' : 'Lumen Free Plan';

    menuUpgradeLabel.textContent = isPlus ? 'Manage Plus Plan' : 'Upgrade to Plus (₹699)';
    menuAuthLabel.textContent = 'Log Out';
    
    topAuthBtn.style.display = 'none';

    // Admin Access
    if (user.role === 'admin') {
      menuAdminBtn.style.display = 'flex';
    } else {
      menuAdminBtn.style.display = 'none';
    }

    // Settings Modal
    if (settingsPlanDesc) settingsPlanDesc.textContent = isPlus ? 'Permanent Plus Entitlement' : 'Free Account (Standard limits)';
    if (settingsPlanBadge) {
      settingsPlanBadge.textContent = isPlus ? 'Plus' : 'Free';
      settingsPlanBadge.className = isPlus ? 'plan-badge plus' : 'plan-badge';
    }
  }

  function renderUserGuest() {
    accountAvatar.textContent = 'G';
    accountName.textContent = 'Guest User';
    accountEmail.textContent = 'Sign in to save history';
    accountPlanBadge.textContent = 'Free';
    accountPlanBadge.className = 'plan-badge';
    modelTierBadge.textContent = 'Standard';
    modelTierBadge.style.color = '#888888';

    menuUserName.textContent = 'Guest Session';
    menuUserPlan.textContent = 'Conversations saved temporarily';
    menuUpgradeLabel.textContent = 'Upgrade to Plus (₹699)';
    menuAuthLabel.textContent = 'Log In / Register';
    menuAdminBtn.style.display = 'none';
    topAuthBtn.style.display = 'block';

    if (settingsPlanDesc) settingsPlanDesc.textContent = 'Guest Account';
    if (settingsPlanBadge) {
      settingsPlanBadge.textContent = 'Free';
      settingsPlanBadge.className = 'plan-badge';
    }
  }

  // ==========================================================================
  // Auth Modal Handlers
  // ==========================================================================
  function openAuthModal(mode = 'login') {
    authMode = mode;
    authAlert.style.display = 'none';
    authAlert.textContent = '';
    
    if (authMode === 'login') {
      authTabLogin.classList.add('active');
      authTabRegister.classList.remove('active');
      nameFormGroup.style.display = 'none';
      confirmPasswordGroup.style.display = 'none';
      authSubmitBtn.textContent = 'Log In';
    } else {
      authTabRegister.classList.add('active');
      authTabLogin.classList.remove('active');
      nameFormGroup.style.display = 'flex';
      confirmPasswordGroup.style.display = 'flex';
      authSubmitBtn.textContent = 'Create Account';
    }

    authModalBackdrop.classList.add('open');
    closeAccountMenu();
  }

  function closeAuthModal() {
    authModalBackdrop.classList.remove('open');
  }

  authTabLogin.addEventListener('click', () => openAuthModal('login'));
  authTabRegister.addEventListener('click', () => openAuthModal('register'));
  closeAuthModalBtn.addEventListener('click', closeAuthModal);
  authModalBackdrop.addEventListener('click', (e) => {
    if (e.target === authModalBackdrop) closeAuthModal();
  });

  pwToggleBtn.addEventListener('click', () => {
    const isPw = authPasswordInput.type === 'password';
    authPasswordInput.type = isPw ? 'text' : 'password';
    if (authConfirmPasswordInput) authConfirmPasswordInput.type = isPw ? 'text' : 'password';
  });

  authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    authAlert.style.display = 'none';

    const email = authEmailInput.value.trim();
    const password = authPasswordInput.value;
    const name = authNameInput.value.trim();
    const confirmPassword = authConfirmPasswordInput.value;

    if (!email || !password) {
      showAuthError('Email and password are required.');
      return;
    }

    if (authMode === 'register') {
      if (password.length < 8) {
        showAuthError('Password must be at least 8 characters.');
        return;
      }
      if (password !== confirmPassword) {
        showAuthError('Passwords do not match.');
        return;
      }
    }

    authSubmitBtn.disabled = true;
    authSubmitBtn.textContent = authMode === 'login' ? 'Logging in...' : 'Creating account...';

    try {
      const endpoint = authMode === 'login' ? '/api/auth/login' : '/api/auth/register';
      const bodyPayload = authMode === 'login' 
        ? { email, password }
        : { email, password, display_name: name || email.split('@')[0] };

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bodyPayload)
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Authentication failed. Please verify your details.');
      }

      // Success
      state.token = data.token;
      state.user = data.user;
      localStorage.setItem('lumen_auth_token', state.token);
      renderUserLoggedIn(state.user);
      closeAuthModal();
      loadConversations();

      // Clear form
      authPasswordInput.value = '';
      if (authConfirmPasswordInput) authConfirmPasswordInput.value = '';

    } catch (err) {
      showAuthError(err.message);
    } finally {
      authSubmitBtn.disabled = false;
      authSubmitBtn.textContent = authMode === 'login' ? 'Log In' : 'Create Account';
    }
  });

  function showAuthError(msg) {
    authAlert.textContent = msg;
    authAlert.style.display = 'block';
  }

  // Account Menu Interactions
  function toggleAccountMenu() {
    accountMenu.classList.toggle('open');
  }
  function closeAccountMenu() {
    accountMenu.classList.remove('open');
  }

  accountCardBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleAccountMenu();
  });

  document.addEventListener('click', (e) => {
    if (!accountMenu.contains(e.target) && !accountCardBtn.contains(e.target)) {
      closeAccountMenu();
    }
  });

  menuAuthBtn.addEventListener('click', () => {
    if (state.user) {
      // Logout
      apiFetch('/api/auth/logout', { method: 'POST' });
      localStorage.removeItem('lumen_auth_token');
      state.token = null;
      state.user = null;
      state.activeConversationId = null;
      renderUserGuest();
      clearChatViewport();
      renderConversationsList([]);
      closeAccountMenu();
    } else {
      openAuthModal('login');
    }
  });

  topAuthBtn.addEventListener('click', () => openAuthModal('login'));

  // ==========================================================================
  // Conversations History Management (Grouped by Date)
  // ==========================================================================
  async function loadConversations() {
    if (!state.token) {
      renderConversationsList([]);
      return;
    }

    try {
      const res = await apiFetch('/api/conversations');
      if (res.ok) {
        const data = await res.json();
        state.conversations = data.conversations || [];
        renderConversationsList(state.conversations);
      }
    } catch (e) {
      console.warn('Failed loading conversations', e);
    }
  }

  function renderConversationsList(conversations) {
    itemsToday.innerHTML = '';
    itemsYesterday.innerHTML = '';
    itemsPrevious7.innerHTML = '';
    itemsOlder.innerHTML = '';

    const filterText = conversationSearchInput.value.toLowerCase().trim();
    const filtered = conversations.filter(c => c.title.toLowerCase().includes(filterText));

    if (filtered.length === 0) {
      emptyConversationsState.style.display = 'block';
      groupToday.style.display = 'none';
      groupYesterday.style.display = 'none';
      groupPrevious7.style.display = 'none';
      groupOlder.style.display = 'none';
      return;
    }

    emptyConversationsState.style.display = 'none';

    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const startOfYesterday = new Date(startOfToday.getTime() - 24 * 60 * 60 * 1000);
    const startOf7Days = new Date(startOfToday.getTime() - 7 * 24 * 60 * 60 * 1000);

    let countToday = 0;
    let countYesterday = 0;
    let count7Days = 0;
    let countOlder = 0;

    filtered.forEach(conv => {
      const convDate = new Date(conv.updated_at || conv.created_at);
      const itemEl = createConversationElement(conv);

      if (convDate >= startOfToday) {
        itemsToday.appendChild(itemEl);
        countToday++;
      } else if (convDate >= startOfYesterday) {
        itemsYesterday.appendChild(itemEl);
        countYesterday++;
      } else if (convDate >= startOf7Days) {
        itemsPrevious7.appendChild(itemEl);
        count7Days++;
      } else {
        itemsOlder.appendChild(itemEl);
        countOlder++;
      }
    });

    groupToday.style.display = countToday > 0 ? 'flex' : 'none';
    groupYesterday.style.display = countYesterday > 0 ? 'flex' : 'none';
    groupPrevious7.style.display = count7Days > 0 ? 'flex' : 'none';
    groupOlder.style.display = countOlder > 0 ? 'flex' : 'none';
  }

  function createConversationElement(conv) {
    const el = document.createElement('div');
    el.className = 'conversation-item' + (conv.id === state.activeConversationId ? ' active' : '');
    el.dataset.id = conv.id;

    el.innerHTML = `
      <span class="conv-title-text" title="${escapeHtml(conv.title)}">${escapeHtml(conv.title)}</span>
      <button class="icon-btn conv-actions-btn" title="Options">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="1"></circle>
          <circle cx="19" cy="12" r="1"></circle>
          <circle cx="5" cy="12" r="1"></circle>
        </svg>
      </button>
    `;

    // Click on item loads conversation
    el.addEventListener('click', (e) => {
      if (e.target.closest('.conv-actions-btn')) return;
      openConversation(conv.id);
    });

    // Options menu (Rename / Delete)
    const actionBtn = el.querySelector('.conv-actions-btn');
    actionBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      showConversationContextMenu(e, conv);
    });

    return el;
  }

  function showConversationContextMenu(e, conv) {
    const action = prompt(`Options for "${conv.title}":\nType "rename" to change title\nType "delete" to remove conversation`, 'rename');
    if (!action) return;

    if (action.toLowerCase().trim() === 'rename') {
      const newTitle = prompt('Enter new conversation title:', conv.title);
      if (newTitle && newTitle.trim()) {
        renameConversation(conv.id, newTitle.trim());
      }
    } else if (action.toLowerCase().trim() === 'delete') {
      if (confirm(`Are you sure you want to delete "${conv.title}"?`)) {
        deleteConversation(conv.id);
      }
    }
  }

  async function renameConversation(convId, newTitle) {
    try {
      const res = await apiFetch(`/api/conversations/${convId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle })
      });
      if (res.ok) {
        loadConversations();
      }
    } catch (err) {
      console.warn('Rename error', err);
    }
  }

  async function deleteConversation(convId) {
    try {
      const res = await apiFetch(`/api/conversations/${convId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        if (state.activeConversationId === convId) {
          clearChatViewport();
        }
        loadConversations();
      }
    } catch (err) {
      console.warn('Delete error', err);
    }
  }

  async function openConversation(convId) {
    state.activeConversationId = convId;
    closeMobileSidebar();

    try {
      const res = await apiFetch(`/api/conversations/${convId}`);
      if (!res.ok) return;

      const data = await res.json();
      renderConversationHistory(data.messages || []);
      highlightActiveConversation(convId);
    } catch (e) {
      console.warn('Failed opening conversation', e);
    }
  }

  function highlightActiveConversation(convId) {
    document.querySelectorAll('.conversation-item').forEach(el => {
      if (el.dataset.id === convId) {
        el.classList.add('active');
      } else {
        el.classList.remove('active');
      }
    });
  }

  function clearChatViewport() {
    state.activeConversationId = null;
    messagesStream.innerHTML = '';
    welcomeContainer.style.display = 'flex';
    messageInput.value = '';
    highlightActiveConversation(null);
  }

  newChatBtn.addEventListener('click', () => {
    clearChatViewport();
    closeMobileSidebar();
    messageInput.focus();
  });

  conversationSearchInput.addEventListener('input', () => {
    renderConversationsList(state.conversations);
  });

  // ==========================================================================
  // Render Conversation Messages (Persistent & Live)
  // ==========================================================================
  function renderConversationHistory(messages) {
    messagesStream.innerHTML = '';
    if (messages.length === 0) {
      welcomeContainer.style.display = 'flex';
      return;
    }

    welcomeContainer.style.display = 'none';

    messages.forEach(msg => {
      if (msg.role === 'user') {
        appendUserMessageToDOM(msg.content, false);
      } else {
        let rawJson = null;
        if (msg.raw_json) {
          try {
            rawJson = typeof msg.raw_json === 'string' ? JSON.parse(msg.raw_json) : msg.raw_json;
          } catch (e) {}
        }
        if (rawJson) {
          appendAssistantResponseToDOM(rawJson, false);
        } else {
          appendAssistantResponseToDOM({
            mode: msg.mode || 'direct_answer',
            message: { text: msg.content },
            language: 'en'
          }, false);
        }
      }
    });

    scrollToBottom();
  }

  function appendUserMessageToDOM(text, shouldScroll = true) {
    welcomeContainer.style.display = 'none';

    const row = document.createElement('div');
    row.className = 'message-row user';
    row.innerHTML = `
      <div class="user-bubble">${escapeHtml(text)}</div>
    `;

    messagesStream.appendChild(row);
    if (shouldScroll) scrollToBottom();
  }

  function showTypingIndicator() {
    const id = 'typing-' + Date.now();
    const row = document.createElement('div');
    row.className = 'message-row assistant';
    row.id = id;

    row.innerHTML = `
      <div class="assistant-avatar">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="5"></circle>
          <line x1="12" y1="1" x2="12" y2="3"></line>
          <line x1="12" y1="21" x2="12" y2="23"></line>
        </svg>
      </div>
      <div class="assistant-content">
        <div class="typing-row">
          <div class="typing-dots">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </div>
          <span>Thinking...</span>
        </div>
      </div>
    `;

    messagesStream.appendChild(row);
    scrollToBottom();
    return id;
  }

  function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function appendAssistantResponseToDOM(data, shouldScroll = true) {
    updateJsonInspector(data);

    if (state.soundEnabled && window.audioManager) {
      if (data.safety && data.safety.urgent) {
        window.audioManager.playEmergency();
      } else {
        window.audioManager.playReceive();
      }
    }

    const row = document.createElement('div');
    row.className = 'message-row assistant';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'assistant-content';

    // 1. Emergency Banner
    if (data.safety && data.safety.urgent) {
      const emergencyEl = document.createElement('div');
      emergencyEl.className = 'emergency-alert-card';
      emergencyEl.innerHTML = `
        <div class="emergency-header">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <span>Emergency Medical Notice</span>
        </div>
        <div class="emergency-body">${escapeHtml(data.safety.message || 'Please seek urgent in-person medical care or call local emergency services immediately.')}</div>
      `;
      contentDiv.appendChild(emergencyEl);
    }

    // 2. Primary Text Message (Markdown Rendered)
    const textMsg = (data.message && data.message.text) ? data.message.text : '';
    const textWrapper = document.createElement('div');
    if (window.marked) {
      textWrapper.innerHTML = marked.parse(textMsg);
      // Code Block copy buttons
      textWrapper.querySelectorAll('pre code').forEach((codeBlock) => {
        const pre = codeBlock.parentElement;
        const container = document.createElement('div');
        container.className = 'code-block-container';
        
        const header = document.createElement('div');
        header.className = 'code-header';
        header.innerHTML = `
          <span>code</span>
          <button type="button" class="copy-code-btn">Copy code</button>
        `;

        header.querySelector('.copy-code-btn').addEventListener('click', function () {
          navigator.clipboard.writeText(codeBlock.innerText).then(() => {
            this.textContent = 'Copied!';
            setTimeout(() => { this.textContent = 'Copy code'; }, 2000);
          });
        });

        pre.parentNode.insertBefore(container, pre);
        container.appendChild(header);
        container.appendChild(pre);
      });
    } else {
      textWrapper.innerHTML = `<p>${escapeHtml(textMsg)}</p>`;
    }
    contentDiv.appendChild(textWrapper);

    // 3. Survey Card (Conversational Health / Assessment)
    if (data.survey && data.survey.active && data.survey.question) {
      const surveyCard = document.createElement('div');
      surveyCard.className = 'survey-card';

      const cur = (data.survey.progress && data.survey.progress.current) || 1;
      const tot = (data.survey.progress && data.survey.progress.estimated_total) || 4;

      let optionsHtml = '';
      if (Array.isArray(data.survey.options) && data.survey.options.length > 0) {
        optionsHtml = `
          <div class="survey-options-grid">
            ${data.survey.options.map(opt => `
              <button type="button" class="survey-opt-chip" data-ans="${escapeHtml(opt)}">${escapeHtml(opt)}</button>
            `).join('')}
          </div>
        `;
      }

      surveyCard.innerHTML = `
        <div class="survey-header-row">
          <span>Health Evaluation Step</span>
          <span>Question ${cur} of ${tot}</span>
        </div>
        <div class="survey-question">${escapeHtml(data.survey.question)}</div>
        ${optionsHtml}
        <div class="survey-custom-row">
          <input type="text" class="survey-custom-input" placeholder="Type your response here...">
          <button type="button" class="survey-continue-btn">Continue</button>
        </div>
      `;

      // Handle Option Click
      surveyCard.querySelectorAll('.survey-opt-chip').forEach(btn => {
        btn.addEventListener('click', () => {
          submitMessage(btn.dataset.ans);
        });
      });

      // Handle Custom Text Continue
      const customInput = surveyCard.querySelector('.survey-custom-input');
      const continueBtn = surveyCard.querySelector('.survey-continue-btn');
      const submitCustom = () => {
        const val = customInput.value.trim();
        if (val) submitMessage(val);
      };
      continueBtn.addEventListener('click', submitCustom);
      customInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') submitCustom();
      });

      contentDiv.appendChild(surveyCard);
    }

    // 4. Assessment Synthesis Card
    if (data.assessment && (data.assessment.completed || (data.assessment.action_steps && data.assessment.action_steps.length > 0))) {
      const assessCard = document.createElement('div');
      assessCard.className = 'assessment-card';

      let html = `<div class="assessment-title">Guidance & Observations</div>`;

      if (data.assessment.summary) {
        html += `<div class="assessment-section"><strong>Summary</strong><p>${escapeHtml(data.assessment.summary)}</p></div>`;
      }

      if (Array.isArray(data.assessment.possibilities) && data.assessment.possibilities.length > 0) {
        html += `
          <div class="assessment-section">
            <strong>Potential Considerations</strong>
            <ul>${data.assessment.possibilities.map(p => `<li>${escapeHtml(p)}</li>`).join('')}</ul>
          </div>
        `;
      }

      if (Array.isArray(data.assessment.action_steps) && data.assessment.action_steps.length > 0) {
        html += `
          <div class="assessment-section">
            <strong>Care & Practical Steps</strong>
            <ul>${data.assessment.action_steps.map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ul>
          </div>
        `;
      }

      if (Array.isArray(data.assessment.when_to_seek_doctor) && data.assessment.when_to_seek_doctor.length > 0) {
        html += `
          <div class="assessment-section">
            <strong style="color: #f87171;">When to Consult a Physician</strong>
            <ul>${data.assessment.when_to_seek_doctor.map(w => `<li>${escapeHtml(w)}</li>`).join('')}</ul>
          </div>
        `;
      }

      if (data.assessment.disclaimer) {
        html += `<div class="assessment-disclaimer">${escapeHtml(data.assessment.disclaimer)}</div>`;
      }

      assessCard.innerHTML = html;
      contentDiv.appendChild(assessCard);
    }

    // 5. Follow-up Suggestions Chips
    if (Array.isArray(data.suggestions) && data.suggestions.length > 0) {
      const suggBox = document.createElement('div');
      suggBox.className = 'assistant-suggestions';
      data.suggestions.forEach(sugg => {
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'suggestion-pill';
        chip.textContent = sugg;
        chip.addEventListener('click', () => {
          submitMessage(sugg);
        });
        suggBox.appendChild(chip);
      });
      contentDiv.appendChild(suggBox);
    }

    // Assemble row
    row.innerHTML = `
      <div class="assistant-avatar">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="5"></circle>
          <line x1="12" y1="1" x2="12" y2="3"></line>
          <line x1="12" y1="21" x2="12" y2="23"></line>
        </svg>
      </div>
    `;
    row.appendChild(contentDiv);
    messagesStream.appendChild(row);

    if (shouldScroll) scrollToBottom();
  }

  // ==========================================================================
  // Chat Submission Flow
  // ==========================================================================
  async function submitMessage(text) {
    if (!text || !text.trim() || state.isProcessing) return;
    const cleanText = text.trim();

    state.isProcessing = true;
    sendBtn.disabled = true;

    // Reset textarea height
    messageInput.value = '';
    messageInput.style.height = 'auto';

    // 1. Add User Message to Viewport
    appendUserMessageToDOM(cleanText);

    // 2. Typing indicator
    const typingId = showTypingIndicator();

    try {
      const payload = {
        conversation_id: state.activeConversationId,
        message: cleanText,
        language: state.selectedLanguage
      };

      const res = await apiFetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      removeTypingIndicator(typingId);

      if (res.status === 429) {
        const errData = await res.json();
        alert(errData.detail || 'Free plan message limit reached. Upgrade to Plus for unlimited messages.');
        openPlusModal();
        return;
      }

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'AI service temporarily unavailable. Please try again.');
      }

      const botResponse = await res.json();

      // Update active conversation ID if newly created
      if (!state.activeConversationId && botResponse) {
        // Will be refreshed from database
        loadConversations();
      }

      appendAssistantResponseToDOM(botResponse);

      // Refresh conversations list to update order/title
      loadConversations();

    } catch (err) {
      removeTypingIndicator(typingId);
      appendAssistantResponseToDOM({
        mode: 'direct_answer',
        message: { text: `⚠️ Error: ${err.message}` }
      });
    } finally {
      state.isProcessing = false;
      sendBtn.disabled = false;
      messageInput.focus();
    }
  }

  // Chat Form Listeners
  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    submitMessage(messageInput.value);
  });

  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitMessage(messageInput.value);
    }
  });

  // Auto-resize composer textarea
  messageInput.addEventListener('input', () => {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 180) + 'px';
  });

  // Language selector change
  languageSelect.addEventListener('change', () => {
    state.selectedLanguage = languageSelect.value;
  });

  // Welcome prompt chips
  document.querySelectorAll('.prompt-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const promptText = chip.getAttribute('data-prompt');
      if (promptText) submitMessage(promptText);
    });
  });

  // Attachment button info
  if (attachmentBtn) {
    attachmentBtn.addEventListener('click', () => {
      alert('Context attachment will be available in the next release.');
    });
  }

  // Voice Input (Web Speech Recognition)
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition && voiceBtn) {
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
      voiceBtn.style.color = '#ef4444';
    };
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      messageInput.value = transcript;
      messageInput.dispatchEvent(new Event('input'));
    };
    recognition.onend = () => {
      voiceBtn.style.color = '';
    };
    recognition.onerror = () => {
      voiceBtn.style.color = '';
    };

    voiceBtn.addEventListener('click', () => {
      try {
        recognition.start();
      } catch (e) {
        recognition.stop();
      }
    });
  } else if (voiceBtn) {
    voiceBtn.style.display = 'none';
  }

  // ==========================================================================
  // Structured JSON Inspector Drawer
  // ==========================================================================
  function updateJsonInspector(data) {
    state.lastJsonResponse = data;
    jsonPreCode.textContent = JSON.stringify(data, null, 2);
    if (window.hljs) {
      hljs.highlightElement(jsonPreCode);
    }
    jsonMeta.textContent = `Mode: ${escapeHtml((data.mode || 'direct_answer').replace('_', ' '))} | Lang: ${(data.language || 'en').toUpperCase()}`;
  }

  function toggleJsonDrawer() {
    state.jsonInspectorOpen = !state.jsonInspectorOpen;
    if (state.jsonInspectorOpen) {
      jsonDrawer.classList.add('open');
    } else {
      jsonDrawer.classList.remove('open');
    }
  }

  jsonInspectorToggleBtn.addEventListener('click', toggleJsonDrawer);
  closeJsonDrawerBtn.addEventListener('click', toggleJsonDrawer);

  copyJsonBtn.addEventListener('click', () => {
    if (!state.lastJsonResponse) return;
    navigator.clipboard.writeText(JSON.stringify(state.lastJsonResponse, null, 2)).then(() => {
      copyJsonBtn.textContent = 'Copied!';
      setTimeout(() => { copyJsonBtn.textContent = 'Copy'; }, 1800);
    });
  });

  // ==========================================================================
  // Upgrade to Plus & UPI QR Payment Modal (₹699)
  // ==========================================================================
  async function openPlusModal() {
    closeAccountMenu();
    plusModalBackdrop.classList.add('open');
    paymentStatusBanner.style.display = 'none';

    // If user is logged in, check active plan and pending payment request
    if (state.token) {
      try {
        const res = await apiFetch('/api/billing/plan');
        if (res.ok) {
          const data = await res.json();
          if (data.plan === 'plus') {
            paymentStatusBanner.style.display = 'block';
            paymentStatusBanner.className = 'payment-status-banner';
            paymentStatusBanner.innerHTML = '<strong>LUMEN PLUS — ACTIVE</strong><br>Lifetime unlimited access is unlocked on your account.';
            paymentSubmissionForm.style.display = 'none';
            return;
          }

          if (data.pending_request) {
            paymentStatusBanner.style.display = 'block';
            paymentStatusBanner.className = 'payment-status-banner';
            paymentStatusBanner.innerHTML = `
              <strong>Verification Pending</strong><br>
              Reference No. <code>${escapeHtml(data.pending_request.utr_number)}</code> submitted on ${data.pending_request.created_at.substring(0, 10)}. Plus entitlement will activate upon confirmation.
            `;
          } else {
            paymentSubmissionForm.style.display = 'block';
          }
        }
      } catch (e) {
        console.warn('Billing check error', e);
      }
    } else {
      // Guest prompt
      paymentStatusBanner.style.display = 'block';
      paymentStatusBanner.innerHTML = '<strong>Please Log In First:</strong> Sign in or create an account so your Plus lifetime entitlement is linked to your user profile.';
    }
  }

  function closePlusModal() {
    plusModalBackdrop.classList.remove('open');
  }

  menuUpgradeBtn.addEventListener('click', openPlusModal);
  closePlusModalBtn.addEventListener('click', closePlusModal);
  plusModalBackdrop.addEventListener('click', (e) => {
    if (e.target === plusModalBackdrop) closePlusModal();
  });

  // Submit UPI Payment Verification Form
  paymentSubmissionForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!state.token) {
      alert('Please log in or register first before submitting payment verification.');
      openAuthModal('login');
      return;
    }

    const utr = utrInput.value.trim();
    if (!utr || utr.length < 6) {
      alert('Please enter a valid UPI Transaction Reference / UTR number.');
      return;
    }

    submitPaymentBtn.disabled = true;
    submitPaymentBtn.textContent = 'Submitting verification...';

    const formData = new FormData();
    formData.append('utr_number', utr);
    formData.append('amount', '699.00');

    if (screenshotInput.files && screenshotInput.files[0]) {
      formData.append('screenshot', screenshotInput.files[0]);
    }

    try {
      const res = await apiFetch('/api/billing/submit-payment', {
        method: 'POST',
        body: formData
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Payment submission failed.');
      }

      paymentStatusBanner.style.display = 'block';
      paymentStatusBanner.className = 'payment-status-banner';
      paymentStatusBanner.innerHTML = `
        <strong>Submission Received!</strong><br>
        Your UTR <code>${escapeHtml(utr)}</code> is under review. Status: <strong>Pending Verification</strong>. Plus will activate upon admin approval.
      `;

      paymentSubmissionForm.reset();
      paymentSubmissionForm.style.display = 'none';

    } catch (err) {
      alert(err.message);
    } finally {
      submitPaymentBtn.disabled = false;
      submitPaymentBtn.textContent = 'Submit Payment for Verification';
    }
  });

  // ==========================================================================
  // Admin Verification Portal (Approve / Reject UPI Requests)
  // ==========================================================================
  async function openAdminModal() {
    closeAccountMenu();
    adminModalBackdrop.classList.add('open');
    adminRequestsList.innerHTML = '<div class="empty-conversations">Loading requests...</div>';

    try {
      const res = await apiFetch('/api/billing/admin/requests');
      if (!res.ok) {
        throw new Error('Unauthorized');
      }

      const data = await res.json();
      const requests = data.requests || [];

      if (requests.length === 0) {
        adminRequestsList.innerHTML = '<div class="empty-conversations">No payment verification requests found.</div>';
        return;
      }

      adminRequestsList.innerHTML = '';
      requests.forEach(req => {
        const card = document.createElement('div');
        card.className = 'admin-req-card';

        let screenshotLink = '';
        if (req.screenshot_url) {
          screenshotLink = `<a href="${escapeHtml(req.screenshot_url)}" target="_blank" style="color: #60a5fa; text-decoration: underline;">View Screenshot</a>`;
        }

        card.innerHTML = `
          <div class="admin-req-header">
            <div>
              <div class="admin-req-user">${escapeHtml(req.user_name || req.user_email)}</div>
              <div class="admin-req-email">${escapeHtml(req.user_email)}</div>
            </div>
            <span class="plan-badge ${req.status === 'approved' ? 'plus' : ''}">${escapeHtml(req.status.toUpperCase())}</span>
          </div>
          <div class="admin-req-details">
            <span>UTR: <span class="admin-req-utr">${escapeHtml(req.utr_number)}</span></span>
            <span>Amount: ₹${escapeHtml(req.amount)}</span>
            <span>${screenshotLink}</span>
          </div>
          ${req.status === 'pending' ? `
            <div class="admin-req-actions">
              <button class="admin-btn-reject" data-id="${req.id}">Reject</button>
              <button class="admin-btn-approve" data-id="${req.id}">Approve (Grant Plus)</button>
            </div>
          ` : `
            <div style="font-size: 11.5px; color: #888;">Reviewed at ${req.reviewed_at || 'N/A'}</div>
          `}
        `;

        if (req.status === 'pending') {
          card.querySelector('.admin-btn-approve').addEventListener('click', () => reviewPayment(req.id, 'approved'));
          card.querySelector('.admin-btn-reject').addEventListener('click', () => reviewPayment(req.id, 'rejected'));
        }

        adminRequestsList.appendChild(card);
      });

    } catch (e) {
      adminRequestsList.innerHTML = '<div class="empty-conversations" style="color: #ef4444;">Access denied or error loading requests.</div>';
    }
  }

  async function reviewPayment(requestId, decision) {
    const adminNotes = decision === 'rejected' ? (prompt('Reason for rejection:') || 'Invalid payment reference') : 'Verified UPI credit';
    try {
      const res = await apiFetch('/api/billing/admin/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          request_id: requestId,
          status: decision,
          admin_notes: adminNotes
        })
      });

      if (res.ok) {
        openAdminModal(); // Reload list
        checkCurrentUser(); // In case admin upgraded themselves
      }
    } catch (e) {
      alert('Error updating payment status');
    }
  }

  menuAdminBtn.addEventListener('click', openAdminModal);
  closeAdminModalBtn.addEventListener('click', () => adminModalBackdrop.classList.remove('open'));
  adminModalBackdrop.addEventListener('click', (e) => {
    if (e.target === adminModalBackdrop) adminModalBackdrop.classList.remove('open');
  });

  // ==========================================================================
  // Settings Modal
  // ==========================================================================
  function openSettingsModal() {
    closeAccountMenu();
    settingsModalBackdrop.classList.add('open');
    updateAudioUI();
    if (settingsJsonToggle) {
      settingsJsonToggle.textContent = state.jsonInspectorOpen ? 'On' : 'Off';
    }
  }

  menuSettingsBtn.addEventListener('click', openSettingsModal);
  closeSettingsModalBtn.addEventListener('click', () => settingsModalBackdrop.classList.remove('open'));
  settingsModalBackdrop.addEventListener('click', (e) => {
    if (e.target === settingsModalBackdrop) settingsModalBackdrop.classList.remove('open');
  });

  if (settingsJsonToggle) {
    settingsJsonToggle.addEventListener('click', () => {
      toggleJsonDrawer();
      settingsJsonToggle.textContent = state.jsonInspectorOpen ? 'On' : 'Off';
    });
  }

  // ==========================================================================
  // Mobile Sidebar Toggle
  // ==========================================================================
  function openMobileSidebar() {
    sidebar.classList.add('open');
    sidebarBackdrop.classList.add('active');
  }

  function closeMobileSidebar() {
    sidebar.classList.remove('open');
    sidebarBackdrop.classList.remove('active');
  }

  if (mobileMenuBtn) mobileMenuBtn.addEventListener('click', openMobileSidebar);
  if (sidebarCollapseBtn) sidebarCollapseBtn.addEventListener('click', closeMobileSidebar);
  if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeMobileSidebar);

  // ==========================================================================
  // Initialize Application
  // ==========================================================================
  updateAudioUI();
  checkCurrentUser();

})();
