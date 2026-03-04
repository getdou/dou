/**
 * dòu — open douyin client
 * vanilla JS, zero dependencies
 */

const API = window.location.origin + '/api';

const state = {
    feed: 'trending',
    cursor: 0,
    loading: false,
    hasMore: true,
    query: '',
};

// DOM refs
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const feedEl = $('#feed');
const loadingEl = $('#loading');
const emptyEl = $('#empty');
const hotTagsEl = $('#hot-tags');
const searchInput = $('#search-input');
const searchBtn = $('#search-btn');
const modal = $('#video-modal');
const modalVideo = $('#modal-video');
const modalInfo = $('#modal-info');
const modalComments = $('#modal-comments');

// utils
function fmt(n) {
    if (!n || n === 0) return '0';
    if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
    if (n >= 1e4) return (n / 1e4).toFixed(1) + 'W';
    if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
    return String(n);
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function timeAgo(ts) {
    if (!ts) return '';
    const diff = Date.now() / 1000 - ts;
    if (diff < 60) return 'just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    if (diff < 2592000) return Math.floor(diff / 86400) + 'd ago';
    return new Date(ts * 1000).toLocaleDateString();
}

// card builder
function createCard(aweme) {
    const card = document.createElement('div');
    card.className = 'video-card';

    const video = aweme.video || {};
    const author = aweme.author || {};
    const stats = aweme.statistics || {};

    const cover = video.cover?.url_list?.[0]
        || video.dynamic_cover?.url_list?.[0]
        || '';
    const descEn = aweme.desc_translated || '';
    const descCn = aweme.desc || '';
    const nick = author.nickname || '';

    card.innerHTML = `
        ${cover
            ? `<img class="thumb" src="${cover}" loading="lazy" alt="" onerror="this.style.display='none'">`
            : '<div class="thumb"></div>'}
        <div class="info">
            <div class="desc">${escapeHtml(descEn || descCn)}</div>
            ${descEn && descCn !== descEn ? `<div class="desc-cn">${escapeHtml(descCn)}</div>` : ''}
            <div class="meta">
                <span class="author">@${escapeHtml(nick)}</span>
                <span class="stats">
                    <span>${fmt(stats.digg_count)} ♥</span>
                    <span>${fmt(stats.comment_count)} 💬</span>
                </span>
            </div>
        </div>
    `;

    card.addEventListener('click', () => openModal(aweme));
    return card;
}

// feed loading
async function loadFeed(append = false) {
    if (state.loading || (!append && false)) return;
    if (append && !state.hasMore) return;

    state.loading = true;
    loadingEl.style.display = 'flex';
    emptyEl.style.display = 'none';

    if (!append) {
        feedEl.innerHTML = '';
        state.cursor = 0;
        state.hasMore = true;
    }

    try {
        let url;
        switch (state.feed) {
            case 'trending':
                url = `${API}/feed/trending?count=20&cursor=${state.cursor}`;
                break;
            case 'search':
                url = `${API}/feed/search?q=${encodeURIComponent(state.query)}&count=20&cursor=${state.cursor}`;
                break;
            case 'hot':
                url = `${API}/feed/hot`;
                break;
        }

        const resp = await fetch(url);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        if (state.feed === 'hot') {
            renderHotSearch(data);
        } else {
            const items = data.aweme_list || [];
            if (items.length === 0 && !append) {
                emptyEl.style.display = 'block';
            }
            items.forEach(item => feedEl.appendChild(createCard(item)));
            state.cursor = data.max_cursor || state.cursor + 20;
            state.hasMore = data.has_more !== false && items.length > 0;
        }
    } catch (err) {
        console.error('Feed error:', err);
        if (!append) emptyEl.style.display = 'block';
    }

    state.loading = false;
    loadingEl.style.display = 'none';
}

function renderHotSearch(data) {
    const words = data?.data?.word_list || data?.word_list || [];
    hotTagsEl.style.display = 'flex';
    feedEl.style.display = 'none';

    hotTagsEl.innerHTML = words.map((w, i) => {
        const word = w.word_translated || w.word || '';
        const cn = w.word || '';
        return `<a href="#" class="hot-tag" data-query="${escapeHtml(cn)}">
            <span class="rank">${i + 1}</span>
            ${escapeHtml(word)}
            ${w.word_translated ? ` <span style="color:var(--text-faint)">${escapeHtml(cn)}</span>` : ''}
        </a>`;
    }).join('');

    hotTagsEl.querySelectorAll('.hot-tag').forEach(tag => {
        tag.addEventListener('click', (e) => {
            e.preventDefault();
            const q = tag.dataset.query;
            searchInput.value = q;
            state.feed = 'search';
            state.query = q;
            hotTagsEl.style.display = 'none';
            feedEl.style.display = 'grid';
            $$('.nav-link').forEach(l => l.classList.remove('active'));
            loadFeed();
        });
    });
}

// modal
async function openModal(aweme) {
    const video = aweme.video || {};
    const author = aweme.author || {};
    const stats = aweme.statistics || {};
    const id = aweme.aweme_id || '';

    // video
    const playUrl = video.play_addr?.url_list?.slice(-1)[0] || '';
    if (playUrl) {
        modalVideo.src = playUrl;
        modalVideo.style.display = 'block';
    } else {
        modalVideo.style.display = 'none';
    }

    const descEn = aweme.desc_translated || '';
    const descCn = aweme.desc || '';

    modalInfo.innerHTML = `
        <div class="desc-en">${escapeHtml(descEn || descCn)}</div>
        ${descEn && descCn !== descEn ? `<div class="desc-cn-modal">${escapeHtml(descCn)}</div>` : ''}
        <div class="author-line">@${escapeHtml(author.nickname || '')}</div>
        <div class="stats-line">
            ${fmt(stats.digg_count)} likes · ${fmt(stats.comment_count)} comments · ${fmt(stats.share_count)} shares
            ${aweme.create_time ? ' · ' + timeAgo(aweme.create_time) : ''}
        </div>
        ${id ? `<a href="${API}/video/${id}/download" class="download-btn" target="_blank" rel="noopener">download (no watermark)</a>` : ''}
    `;

    // comments
    modalComments.innerHTML = '<div style="padding:12px 0;color:var(--text-faint);font-size:12px;">loading comments...</div>';

    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';

    if (id) {
        try {
            const resp = await fetch(`${API}/video/${id}/comments?count=15`);
            const data = await resp.json();
            const comments = data.comments || [];

            if (comments.length === 0) {
                modalComments.innerHTML = '<div style="padding:12px 0;color:var(--text-faint);font-size:12px;">no comments</div>';
            } else {
                modalComments.innerHTML = comments.map(c => {
                    const textEn = c.text_translated || '';
                    const textCn = c.text || '';
                    return `<div class="comment">
                        <span class="c-author">@${escapeHtml(c.user?.nickname || '')}</span>
                        <div class="c-text">${escapeHtml(textEn || textCn)}</div>
                        ${textEn && textCn !== textEn ? `<div class="c-original">${escapeHtml(textCn)}</div>` : ''}
                    </div>`;
                }).join('');
            }
        } catch (e) {
            modalComments.innerHTML = '';
        }
    }
}

function closeModal() {
    modal.style.display = 'none';
    modalVideo.pause();
    modalVideo.removeAttribute('src');
    modalVideo.load();
    document.body.style.overflow = '';
}

// events
searchBtn.addEventListener('click', () => {
    const q = searchInput.value.trim();
    if (!q) return;
    state.feed = 'search';
    state.query = q;
    hotTagsEl.style.display = 'none';
    feedEl.style.display = 'grid';
    $$('.nav-link').forEach(l => l.classList.remove('active'));
    loadFeed();
});

searchInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') searchBtn.click();
});

$$('.nav-link').forEach(link => {
    link.addEventListener('click', e => {
        e.preventDefault();
        $$('.nav-link').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        state.feed = link.dataset.feed;
        hotTagsEl.style.display = 'none';
        feedEl.style.display = 'grid';
        loadFeed();
    });
});

$('.logo').addEventListener('click', () => {
    state.feed = 'trending';
    searchInput.value = '';
    hotTagsEl.style.display = 'none';
    feedEl.style.display = 'grid';
    $$('.nav-link').forEach(l => l.classList.remove('active'));
    $$('.nav-link')[0]?.classList.add('active');
    loadFeed();
});

$('.modal-close').addEventListener('click', closeModal);
$('.modal-backdrop').addEventListener('click', closeModal);
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// infinite scroll
let scrollTimeout;
window.addEventListener('scroll', () => {
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(() => {
        if (state.feed !== 'hot' &&
            window.innerHeight + window.scrollY >= document.body.offsetHeight - 600) {
            loadFeed(true);
        }
    }, 100);
});

// init
loadFeed();
