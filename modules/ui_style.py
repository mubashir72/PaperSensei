"""Shared presentation helpers; user content is always HTML-escaped."""
from html import escape
from urllib.parse import urlparse
import streamlit as st


def apply_style():
    st.html('''<style>
    .stApp { background: #f8fafb; }
    .stMainBlockContainer { max-width: 1120px; padding-top: 2.8rem; }
    h1 { letter-spacing: -0.045em; font-weight: 750 !important; }
    h2, h3 { letter-spacing: -0.025em; }
    [data-testid="stSidebar"] { background: #fff; border-right: 1px solid #e5eceb; }
    [data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top: 1rem; }
    [data-testid="stSidebar"] [role="radiogroup"] { gap: .3rem; }
    [data-testid="stSidebar"] [role="radiogroup"] label {
      padding: .55rem .8rem; border-radius: 10px; width: 100%; transition: background .15s;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover { background: #f1f7f6; }
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
      background: #e6f3ef; color: #086454; font-weight: 600;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display: none; }
    [data-testid="stSidebar"] [role="radiogroup"] label:focus-within { outline: 2px solid #0f766e; }
    [data-testid="stButton"] button, [data-testid="stPopover"] button { border-radius: 10px; }
    [data-testid="stMetric"] { background: white; border: 1px solid #e5eceb; border-radius: 16px; padding: 1.2rem; }
    [data-testid="stForm"] { background: white; border-radius: 16px; }
    .ps-brand { display: flex; align-items: center; gap: 10px; margin: 0 0 1.5rem; }
    .ps-mark { background: #0f766e; color: white; border-radius: 12px; padding: 8px 12px; font-size: 23px; }
    .ps-brand strong { font-size: 23px; letter-spacing: -.7px; }
    .ps-brand small { display: block; color: #77858c; font-size: 12px; }
    .ps-avatar { width: 46px; height: 46px; border-radius: 50%; object-fit: cover;
      background: #dcefe8; color: #11644e; display: flex; align-items: center; justify-content: center;
      font-size: 18px; font-weight: 700; border: 2px solid white; box-shadow: 0 0 0 1px #dce7e3; }
    .ps-hero { background: linear-gradient(115deg,#e7f4ee,#f0f5fc); border: 1px solid #dbe9e2;
      border-radius: 22px; padding: 2rem; margin-bottom: 1.7rem; }
    .ps-eyebrow { color: #08715f; font-size: 12px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }
    .ps-hero h1 { margin: .6rem 0; max-width: 700px; font-size: clamp(28px,4vw,42px); }
    .ps-hero p { color: #5c6c76; max-width: 620px; margin-bottom: 0; }
    .ps-step { background: white; border: 1px solid #e3eae8; border-radius: 16px; padding: 1.4rem; min-height: 180px; }
    .ps-step span { color: #0f766e; font-size: 13px; font-weight: 700; }
    .ps-step h3 { font-size: 19px; margin: .7rem 0; }
    .ps-step p { color: #65747e; font-size: 15px; }
    @media(max-width:640px) { .stMainBlockContainer { padding-top: 1.4rem; } .ps-hero { padding: 1.3rem; } }
    </style>''')


def avatar(auth):
    name = auth.get("display_name") or auth.get("email", "Student").split("@")[0]
    initials = "".join(part[0] for part in name.split()[:2]).upper() or "S"
    photo = auth.get("photo_url", "")
    if urlparse(photo).scheme == "https" and urlparse(photo).hostname:
        st.html(f'<img class="ps-avatar" src="{escape(photo, quote=True)}" alt="Profile picture" referrerpolicy="no-referrer">')
    else:
        st.html(f'<div class="ps-avatar" role="img" aria-label="Profile initials">{escape(initials)}</div>')
