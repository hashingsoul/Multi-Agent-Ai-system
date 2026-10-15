from __future__ import annotations

import logging
import os
from typing import Any

import bleach
import markdown
from flask import Flask, jsonify, render_template_string, request
from markupsafe import Markup
from src.pipelines.pipeline import run_research_pipeline

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024  # Keep form submissions small.

logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# Markdown is converted to HTML, then sanitized before it is shown in the browser.
ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS) | {
    "p", "h1", "h2", "h3", "h4", "hr", "br", "pre", "code",
    "blockquote", "ul", "ol", "li", "table", "thead", "tbody",
    "tr", "th", "td", "del", "input"
}
ALLOWED_ATTRIBUTES = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "a": ["href", "title", "target", "rel"],
    "th": ["align"],
    "td": ["align"],
    "input": ["type", "checked", "disabled"],
}
ALLOWED_PROTOCOLS = {"http", "https", "mailto"}


def render_markdown(value: Any) -> Markup:
    """Render model Markdown as readable, sanitized HTML."""
    text = str(value or "").strip()
    if not text:
        return Markup("<p>No content was returned.</p>")

    rendered = markdown.markdown(
        text,
        extensions=["extra", "sane_lists", "nl2br", "toc"],
        output_format="html5",
    )
    safe_html = bleach.clean(
        rendered,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    # Open external links in a new tab safely.
    safe_html = safe_html.replace("<a ", '<a target="_blank" rel="noopener noreferrer" ')
    return Markup(safe_html)


PAGE = r"""
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#f7f6f2">
    <title>Stillpoint — AI Research Studio</title>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">

    <style>
        :root {
            --bg: #f7f6f2;
            --surface: #fff;
            --ink: #252923;
            --muted: #777c72;
            --line: #e7e7df;
            --green: #355b45;
            --green-dark: #284735;
            --green-pale: #edf3ed;
            --gold: #bd8b61;
            --red-pale: #fff0eb;
            --red: #8c4935;
            --shadow: 0 16px 50px rgba(35, 45, 35, .055);
            --radius: 20px;
        }
        * { box-sizing: border-box; }
        html { scroll-behavior: smooth; -webkit-text-size-adjust: 100%; }
        img, svg, video { max-width: 100%; height: auto; }
        button, input { max-width: 100%; }
        :focus-visible { outline: 3px solid #a9c2ad; outline-offset: 3px; }
        @keyframes fade-up {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        body {
            margin: 0;
            background:
                radial-gradient(ellipse at 85% 0%, rgba(224, 230, 215, .42), transparent 34rem),
                var(--bg);
            color: var(--ink);
            font: 14px/1.7 "Inter", sans-serif;
        }
        body.is-busy { overflow: hidden; }
        button, input { font: inherit; }
        button, a { -webkit-tap-highlight-color: transparent; }
        .shell { max-width: 1160px; padding: 0 30px; margin: 0 auto; }
        .topbar {
            min-height: 76px; display: flex; align-items: center;
            justify-content: space-between; border-bottom: 1px solid var(--line);
        }
        .brand { display: flex; align-items: center; gap: 11px; font-weight: 700; letter-spacing: -.45px; }
        .brand-mark {
            display: grid; place-items: center; width: 35px; height: 35px;
            border-radius: 12px; background: var(--green); color: white;
            font: 25px/1 "Space Grotesk", Georgia, serif;
        }
        .brand-sub { color: #898d83; font-weight: 400; }
        .top-status { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 12px; }
        .online-dot { width: 7px; height: 7px; background: #6d9875; border-radius: 50%; box-shadow: 0 0 0 4px #e7efe5; }

        .hero { max-width: 790px; padding: 76px 0 35px; animation: fade-up .55s ease both; }
        .eyebrow {
            color: var(--green); text-transform: uppercase; letter-spacing: 2px;
            font-size: 10px; font-weight: 700;
        }
        .hero h1 {
            font: 400 clamp(48px, 7vw, 82px)/.98 "Space Grotesk", Georgia, serif;
            letter-spacing: -2.5px; margin: 17px 0 19px;
        }
        .hero h1 em, .section-heading em { color: var(--green); font-weight: 400; }
        .hero-copy { max-width: 590px; margin: 0; color: var(--muted); font-size: 14px; line-height: 1.95; }

        .search-card {
            animation: fade-up .65s ease both;
            padding: 26px; background: rgba(255,255,255,.92);
            border: 1px solid var(--line); border-radius: var(--radius);
            box-shadow: var(--shadow);
        }
        .field-label {
            display: block; margin-bottom: 12px; color: #52594f;
            font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
        }
        .search-row { display: flex; gap: 11px; }
        .topic-input {
            flex: 1; min-width: 0; padding: 16px 17px;
            background: #fbfbf8; color: var(--ink);
            border: 1px solid #e1e4dc; border-radius: 12px; outline: none;
            transition: border-color .2s, box-shadow .2s;
        }
        .topic-input:focus { border-color: #7c9881; box-shadow: 0 0 0 3px #edf3ed; }
        .topic-input::placeholder { color: #a0a49a; }
        .primary-btn {
            display: inline-flex; align-items: center; justify-content: center; gap: 10px;
            padding: 0 22px; border: 1px solid var(--green); border-radius: 12px;
            background: var(--green); color: white; font-weight: 600; cursor: pointer;
            white-space: nowrap; transition: background .2s, transform .2s;
        }
        .primary-btn:hover { background: var(--green-dark); transform: translateY(-1px); }
        .primary-btn:focus-visible, .copy-btn:focus-visible { outline: 3px solid #b9cbb9; outline-offset: 3px; }
        .form-foot { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-top: 12px; color: #92968c; font-size: 11px; }
        .form-foot strong { color: #697568; font-weight: 600; }

        .workflow { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 20px 0 62px; }
        .agent {
            padding: 17px 18px; min-height: 126px; border: 1px solid var(--line);
            border-radius: 16px; background: rgba(255,255,255,.45);
        }
        .agent-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .agent-num { color: #a1a499; font-size: 10px; letter-spacing: 1px; }
        .agent-icon { display: grid; place-items: center; width: 31px; height: 31px; border-radius: 10px; background: var(--green-pale); color: var(--green); font-size: 15px; }
        .agent h3 { margin: 0 0 3px; font-size: 12px; font-weight: 700; }
        .agent p { margin: 0; color: var(--muted); font-size: 11px; }

        .section-heading { display: flex; justify-content: space-between; align-items: end; gap: 20px; margin: 0 0 20px; }
        .section-heading h2 { margin: 7px 0 0; font: 400 42px/1.1 "Space Grotesk", Georgia, serif; letter-spacing: -.5px; }
        .topic-chip { max-width: 46%; padding: 8px 12px; border-radius: 9px; background: var(--green-pale); color: var(--green); font-size: 11px; overflow-wrap: anywhere; }
        .results { padding-bottom: 58px; }
        .result-card { margin-bottom: 16px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
        .result-card-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 19px 24px; border-bottom: 1px solid #efefe9; }
        .card-title { display: flex; align-items: center; gap: 10px; font-size: 13px; font-weight: 700; }
        .card-kicker { margin-left: 4px; color: #999d93; font-size: 10px; font-weight: 500; }
        .copy-btn { border: 1px solid var(--line); background: white; color: #62685e; border-radius: 9px; padding: 7px 11px; font-size: 11px; cursor: pointer; white-space: nowrap; }
        .copy-btn:hover { background: #f5f7f2; }
        .report-body { padding: 28px clamp(20px, 4vw, 48px) 34px; }
        .markdown-body { max-width: 790px; margin: 0 auto; color: #41463f; font-size: 14px; line-height: 1.9; overflow-wrap: anywhere; }
        .markdown-body h1, .markdown-body h2, .markdown-body h3, .markdown-body h4 {
            color: #272e27; font-family: "Inter", sans-serif; line-height: 1.45;
            letter-spacing: -.3px; font-weight: 700;
        }
        .markdown-body h1 { margin: 0 0 20px; font-size: 25px; }
        .markdown-body h2 { margin: 34px 0 12px; padding-bottom: 9px; border-bottom: 1px solid #eeeee7; font-size: 19px; }
        .markdown-body h3 { margin: 24px 0 8px; font-size: 15px; }
        .markdown-body h4 { margin: 20px 0 7px; font-size: 14px; }
        .markdown-body p { margin: 0 0 16px; }
        .markdown-body ul, .markdown-body ol { padding-left: 25px; margin: 9px 0 20px; }
        .markdown-body li { padding-left: 3px; margin: 6px 0; }
        .markdown-body li::marker { color: #6d896e; }
        .markdown-body strong { color: #2d3d30; font-weight: 700; }
        .markdown-body em { color: #596b58; }
        .markdown-body a { color: #35684a; text-decoration-thickness: 1px; text-underline-offset: 3px; }
        .markdown-body blockquote { margin: 18px 0; padding: 3px 0 3px 17px; border-left: 3px solid #a8bba5; color: #6a7167; }
        .markdown-body hr { border: 0; border-top: 1px solid var(--line); margin: 26px 0; }
        .markdown-body table { display: block; width: 100%; max-width: 100%; overflow-x: auto; border-collapse: collapse; margin: 20px 0; font-size: 12px; -webkit-overflow-scrolling: touch; }
        .markdown-body th, .markdown-body td { padding: 10px 12px; border: 1px solid var(--line); text-align: left; vertical-align: top; }
        .markdown-body th { background: #f3f5f0; color: #344735; }
        .markdown-body code { padding: 2px 5px; border-radius: 5px; background: #f1f3ee; font-size: .92em; }
        .markdown-body pre { overflow-x: auto; padding: 15px; border-radius: 10px; background: #f3f4ef; }
        .markdown-body pre code { padding: 0; background: none; }
        .critic-card { background: #f4f5f0; }
        .critic-card .result-card-header { border-bottom-color: #e5e8df; }
        .critic-card .markdown-body { color: #4b5549; }
        .score-note { padding: 11px 14px; margin-bottom: 20px; border-radius: 10px; background: #e9efe6; color: #38523c; font-size: 12px; }
        .search-details { padding: 18px 24px; }
        .search-details summary { cursor: pointer; font-weight: 700; font-size: 12px; }
        .search-raw { white-space: pre-wrap; overflow-wrap: anywhere; color: var(--muted); font-size: 12px; line-height: 1.8; margin-top: 14px; }
        .error-card { padding: 17px 19px; margin-bottom: 20px; border: 1px solid #f0d3c7; border-radius: 14px; background: var(--red-pale); color: var(--red); overflow-wrap: anywhere; }
        .error-card p { margin: 5px 0 0; }
        .empty-state { margin: 24px 0 58px; padding: 38px 20px; text-align: center; border: 1px dashed #d8dbd1; border-radius: var(--radius); color: var(--muted); }
        .empty-orb { display: grid; place-items: center; width: 46px; height: 46px; margin: 0 auto 14px; border-radius: 16px; background: #eaf0e7; color: var(--green); font-size: 20px; }
        .empty-state strong { display: block; margin-bottom: 7px; color: var(--ink); font: 400 29px/1.2 "Space Grotesk", Georgia, serif; }
        footer { display: flex; justify-content: space-between; gap: 20px; padding: 22px 0 30px; border-top: 1px solid var(--line); color: #969a90; font-size: 11px; }
        footer em { font: 600 13px "Space Grotesk", sans-serif; font-style: normal; color: #667160; }
        .creator-credit { display: inline-flex; align-items: center; gap: 5px; color: #737b70; }
        .creator-credit strong { color: var(--green); font-weight: 700; letter-spacing: .1px; }

        /* An honest, indeterminate loader: it shows that the request is running,
           without pretending to know the exact live agent stage. */
        .loading-overlay {
            position: fixed; inset: 0; z-index: 1000; display: none;
            place-items: center; padding: 22px;
            background: rgba(247, 246, 242, .82); backdrop-filter: blur(8px);
        }
        .loading-overlay.visible { display: grid; }
        .loading-panel {
            width: min(100%, 450px); padding: 32px;
            background: white; border: 1px solid var(--line);
            border-radius: 23px; box-shadow: 0 28px 100px rgba(30, 40, 30, .16);
            text-align: center;
        }
        .loader-ring {
            width: 58px; height: 58px; margin: 0 auto 22px; position: relative;
            border: 3px solid #e8eee6; border-top-color: var(--green);
            border-right-color: #8aa48b; border-radius: 50%;
            animation: spin .95s linear infinite;
        }
        .loader-ring::after {
            content: ""; position: absolute; inset: 9px; border-radius: 50%;
            border: 2px solid #f0e4d7; border-bottom-color: var(--gold);
            animation: spin 1.5s linear infinite reverse;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loading-panel h2 { margin: 0 0 8px; font: 400 34px/1.15 "Space Grotesk", Georgia, serif; }
        .loading-panel h2 em { color: var(--green); }
        .loading-topic { margin: 0 auto 20px; max-width: 340px; color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
        .progress-track { height: 5px; overflow: hidden; border-radius: 20px; background: #edf0e9; }
        .progress-bar { width: 36%; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #78957b, var(--green)); animation: travel 1.7s ease-in-out infinite; }
        @keyframes travel { 0% { transform: translateX(-110%); } 100% { transform: translateX(310%); } }
        .loading-caption { margin: 15px 0 0; color: #777f73; font-size: 11px; }
        .loading-steps { display: flex; justify-content: center; flex-wrap: wrap; gap: 7px; margin-top: 20px; }
        .loading-steps span { padding: 6px 9px; border: 1px solid #e8eae2; border-radius: 8px; color: #858a80; font-size: 10px; }
        .loading-steps span:first-child { background: #edf3ed; color: var(--green); border-color: #dce7dc; }
        @media (max-width: 760px) {
            .shell { width: 100%; padding: 0 19px; }
            .topbar { min-height: 68px; gap: 12px; }
            .brand { min-width: 0; gap: 9px; }
            .top-status { text-align: right; }
            .hero h1 { font-size: clamp(43px, 10vw, 66px); }
            .search-card { padding: 22px; }
            .workflow { gap: 10px; }
            .agent { min-width: 0; }
            .result-card { border-radius: 15px; }
            .markdown-body { font-size: 13px; }
            footer { flex-direction: column; align-items: flex-start; gap: 8px; }
            .hero { padding-top: 52px; }
            .workflow { grid-template-columns: repeat(2, 1fr); margin-bottom: 43px; }
            .search-row { flex-direction: column; }
            .primary-btn { min-height: 49px; }
            .section-heading { align-items: flex-start; flex-direction: column; }
            .section-heading h2 { font-size: 37px; }
            .topic-chip { max-width: 100%; }
            .result-card-header { padding: 16px 18px; }
            .report-body { padding: 23px 19px 28px; }
        }
        @media (max-width: 420px) {
            .shell { padding: 0 14px; }
            .topbar { align-items: center; min-height: 62px; }
            .brand { font-size: 13px; }
            .brand-mark { width: 32px; height: 32px; flex: 0 0 32px; }
            .top-status { max-width: 125px; font-size: 9px; line-height: 1.4; }
            .hero { padding-top: 42px; }
            .hero h1 { font-size: clamp(39px, 11vw, 49px); line-height: 1.03; }
            .hero-copy { font-size: 13px; }
            .search-card { padding: 16px; border-radius: 16px; }
            .topic-input { padding: 14px; font-size: 16px; }
            .primary-btn { width: 100%; padding: 13px 16px; }
            .workflow { gap: 8px; }
            .agent { min-height: 116px; padding: 12px; }
            .agent h3 { font-size: 11px; }
            .agent p { font-size: 10px; line-height: 1.55; }
            .section-heading h2 { font-size: 32px; }
            .result-card-header { align-items: flex-start; gap: 8px; padding: 14px; }
            .card-title { flex-wrap: wrap; font-size: 12px; }
            .copy-btn { padding: 7px 9px; font-size: 10px; }
            .report-body { padding: 18px 14px 22px; }
            .markdown-body h1 { font-size: 22px; }
            .markdown-body h2 { font-size: 17px; }
            .markdown-body th, .markdown-body td { padding: 8px; }
            .search-details { padding: 15px; }
            .loading-panel h2 { font-size: 29px; }
            .loading-steps span { font-size: 9px; }
            .brand-sub { display: none; }
            .hero h1 { letter-spacing: -1.5px; }
            .search-card { padding: 18px; }
            .agent { padding: 14px; }
            .card-kicker { display: none; }
            .loading-panel { padding: 27px 20px; }
        }
        @media (max-width: 340px) {
            .workflow { grid-template-columns: 1fr; }
            .agent { min-height: auto; }
            .top-status { max-width: 95px; }
            .result-card-header { flex-direction: column; }
            .copy-btn { align-self: flex-start; }
        }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; scroll-behavior: auto !important; }
        }
    </style>
</head>
<body>
    <div class="shell">
        <header class="topbar">
            <div class="brand">
                <div class="brand-mark">s.</div>
                <span>stillpoint <span class="brand-sub">/ research studio</span></span>
            </div>
            <div class="top-status"><span class="online-dot"></span><span>Multi-agent workspace</span></div>
        </header>

        <main>
            <section class="hero">
                <div class="eyebrow">Curiosity, with a method</div>
                <h1>Make room for<br><em>better questions.</em></h1>
                <p class="hero-copy">
                    Explore a topic with a team of AI agents. Gather web sources,
                    turn evidence into a structured report, and finish with a critical review.
                </p>
            </section>

            <section class="search-card" aria-labelledby="topic-label">
                <label class="field-label" id="topic-label" for="topic">Start with a research question</label>
                <form method="post" action="/" id="research-form">
                    <div class="search-row">
                        <input class="topic-input" id="topic" name="topic" type="text"
                               placeholder="e.g. Best YouTube channels to learn AI"
                               value="{{ topic }}" maxlength="500" required autocomplete="off">
                        <button class="primary-btn" id="submit-button" type="submit">
                            Begin research <span aria-hidden="true">↗</span>
                        </button>
                    </div>
                    <div class="form-foot">
                        <span><strong>Search</strong> · Extract · Write · Review</span>
                        <span>Research may take a little while</span>
                    </div>
                </form>
            </section>

            <section class="workflow" aria-label="Four steps in the research workflow">
                <article class="agent">
                    <div class="agent-top"><span class="agent-num">STEP 01</span><span class="agent-icon">⌕</span></div>
                    <h3>Discover sources</h3><p>Search the web for useful leads</p>
                </article>
                <article class="agent">
                    <div class="agent-top"><span class="agent-num">STEP 02</span><span class="agent-icon">↗</span></div>
                    <h3>Gather evidence</h3><p>Read relevant web pages</p>
                </article>
                <article class="agent">
                    <div class="agent-top"><span class="agent-num">STEP 03</span><span class="agent-icon">✎</span></div>
                    <h3>Write the report</h3><p>Organise findings into sections</p>
                </article>
                <article class="agent">
                    <div class="agent-top"><span class="agent-num">STEP 04</span><span class="agent-icon">✓</span></div>
                    <h3>Review quality</h3><p>Assess strengths and gaps</p>
                </article>
            </section>

            {% if error %}
            <section class="error-card" role="alert">
                <strong>We couldn't complete this research.</strong>
                <p>{{ error }}</p>
                <p>Check the terminal for the detailed error, then try again.</p>
            </section>
            {% endif %}

            {% if result %}
            <section class="results" id="results">
                <div class="section-heading">
                    <div>
                        <div class="eyebrow">Research desk · Complete</div>
                        <h2>Findings &amp; <em>perspective.</em></h2>
                    </div>
                    <div class="topic-chip">{{ topic }}</div>
                </div>

                {% if result.report %}
                <article class="result-card">
                    <div class="result-card-header">
                        <div class="card-title"><span class="agent-icon">✎</span> Research report <span class="card-kicker">STRUCTURED FINDINGS</span></div>
                        <button class="copy-btn" type="button" data-copy="report-content">Copy report</button>
                    </div>
                    <div class="report-body"><div class="markdown-body" id="report-content">{{ report_html }}</div></div>
                </article>
                {% endif %}

                {% if result.feedback %}
                <article class="result-card critic-card">
                    <div class="result-card-header">
                        <div class="card-title"><span class="agent-icon">✓</span> Critic's review <span class="card-kicker">QUALITY CHECK</span></div>
                        <button class="copy-btn" type="button" data-copy="critic-content">Copy review</button>
                    </div>
                    <div class="report-body"><div class="markdown-body" id="critic-content">{{ feedback_html }}</div></div>
                </article>
                {% endif %}

                {% if result.search_results %}
                <details class="result-card">
                    <summary class="search-details">View original search results</summary>
                    <div class="search-details search-raw">{{ result.search_results }}</div>
                </details>
                {% endif %}
            </section>
            {% else %}
            <section class="empty-state">
                <div class="empty-orb">✳</div>
                <strong>Your next discovery starts here.</strong>
                Enter a topic above. Your report and review will appear in this space.
            </section>
            {% endif %}
        </main>

        <footer>
            <span>Stillpoint <em>— research, with care.</em></span>
            <span>AI-assisted research · Verify important claims at their sources</span>
            <span class="creator-credit">Designed &amp; developed by <strong>Sagnik Sen</strong></span>
        </footer>
    </div>

    <div class="loading-overlay" id="loading-overlay" role="dialog" aria-modal="true"
         aria-labelledby="loading-title" aria-describedby="loading-description" aria-hidden="true">
        <div class="loading-panel">
            <div class="loader-ring" aria-hidden="true"></div>
            <h2 id="loading-title">Research is <em>underway.</em></h2>
            <p class="loading-topic" id="loading-description">Your topic is being passed to the research workflow.</p>
            <div class="progress-track" aria-hidden="true"><div class="progress-bar"></div></div>
            <p class="loading-caption">This can take a minute. Please keep this tab open.</p>
            <div class="loading-steps" aria-label="Workflow stages">
                <span>Discover</span><span>Gather</span><span>Write</span><span>Review</span>
            </div>
        </div>
    </div>

    <script>
        (() => {
            const form = document.getElementById("research-form");
            const input = document.getElementById("topic");
            const overlay = document.getElementById("loading-overlay");
            const description = document.getElementById("loading-description");
            const submitButton = document.getElementById("submit-button");
            let submitting = false;

            form.addEventListener("submit", (event) => {
                if (submitting) {
                    event.preventDefault();
                    return;
                }
                if (!input.value.trim()) {
                    event.preventDefault();
                    input.focus();
                    return;
                }

                submitting = true;
                description.textContent = "Topic: " + input.value.trim();
                overlay.classList.add("visible");
                overlay.setAttribute("aria-hidden", "false");
                document.body.classList.add("is-busy");
                submitButton.disabled = true;
                submitButton.innerHTML = "Researching <span aria-hidden='true'>…</span>";
            });

            document.querySelectorAll("[data-copy]").forEach((button) => {
                button.addEventListener("click", async () => {
                    const target = document.getElementById(button.dataset.copy);
                    if (!target) return;
                    const original = button.textContent;
                    const text = target.innerText;

                    try {
                        await navigator.clipboard.writeText(text);
                        button.textContent = "Copied";
                    } catch (_) {
                        const area = document.createElement("textarea");
                        area.value = text;
                        area.style.position = "fixed";
                        area.style.opacity = "0";
                        document.body.appendChild(area);
                        area.select();
                        const copied = document.execCommand("copy");
                        area.remove();
                        button.textContent = copied ? "Copied" : "Copy unavailable";
                    }
                    window.setTimeout(() => { button.textContent = original; }, 1600);
                });
            });

            // After a completed POST, the new page has loaded and the overlay is gone.
            // Scroll results into view so the user sees the report immediately.
            const results = document.getElementById("results");
            if (results) {
                window.setTimeout(() => results.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
            }
        })();
    </script>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def home():
    topic = ""
    result = None
    error = None
    report_html = ""
    feedback_html = ""

    if request.method == "POST":
        topic = request.form.get("topic", "").strip()

        if not topic:
            error = "Please enter a research topic."
        elif len(topic) > 500:
            error = "Please keep your topic under 500 characters."
        else:
            app.logger.info("Research request started for topic: %s", topic[:160])
            try:
                result = run_research_pipeline(topic)

                if not isinstance(result, dict):
                    raise TypeError("The research pipeline must return a dictionary.")

                report_html = render_markdown(result.get("report", ""))
                feedback_html = render_markdown(result.get("feedback", ""))

                app.logger.info("Research request completed for topic: %s", topic[:160])

            except Exception:
                app.logger.exception("Research pipeline failed")
                result = None
                error = (
                    "The research workflow stopped before it could return a complete report. "
                    "Review the traceback in the terminal; a source URL, API key, rate limit, "
                    "or model request may have failed."
                )

    return render_template_string(
        PAGE,
        topic=topic,
        result=result,
        error=error,
        report_html=report_html,
        feedback_html=feedback_html,
    )


@app.route("/health", methods=["GET"])
def health():
    """Basic liveness check: confirms Flask is responding, not external API health."""
    return jsonify({
        "status": "healthy",
        "service": "Stillpoint AI Research Studio",
        "message": "The Flask application is running.",
    }), 200


if __name__ == "__main__":
    # Debug mode is convenient for local development only.
    app.run(host="127.0.0.1", port=5000, debug=True)
