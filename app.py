"""
app.py - the main file of the website
=====================================
Run it with:

    streamlit run app.py

The login / sign-up screen below uses the uploaded reference design. When
nobody is logged in it is the whole page; once someone signs in it hands over
to the rest of the website - the sidebar menu and the page modules in `views/`.
"""

from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from config import settings
from database.connection import ensure_daily_attendance_unique_index, get_session, test_connection
from services import auth_service, settings_service, student_service
from ui import auth_guard, components
from views import (
    attendance,
    classes,
    dashboard,
    kiosk,
    kiosk_management,
    qr_codes,
    reports,
    settings_page,
    students,
    users,
)

# `set_page_config` must be the very first Streamlit command that runs.
st.set_page_config(
    page_title="Student Attendance System",
    page_icon="\U0001F393",
    layout="wide",
    initial_sidebar_state="expanded",
)


BASE_DIR = Path(__file__).resolve().parent

SCHOOL_NAME = "Tanza National Trade School"
ADDRESS = "Tanza - Trece Martires Road, Tanza, Cavite"
PHONE = "+63 46 419 1010"
EMAIL = "tnts.shs@gmail.com"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@st.cache_resource(show_spinner=False)
def logo_data_uri() -> str:
    """Return the shared trade-logo image for the login page."""
    return components.brand_logo_data_uri()


def login_page_css() -> None:
    """Apply a closer recreation of the reference login screenshots."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=League+Spartan:wght@600;700;800&display=swap');

        :root {
            --tnts-maroon: #61000f;
            --tnts-ivory: #f7f7f7;
            --tnts-page: #ececec;
            --tnts-shadow: 0 16px 30px rgba(0, 0, 0, 0.2);
            --card-width: min(556px, calc(100vw - 36px));
            --card-padding: 30px;
            --field-width: calc(var(--card-width) - 60px);
        }

        html, body, .stApp, .stApp *:not([data-testid="stIconMaterial"]) {
            font-family: 'League Spartan', sans-serif;
        }

        .stApp [data-testid="stIconMaterial"] {
            font-family: 'Material Symbols Rounded' !important;
            font-weight: 400 !important;
            font-style: normal !important;
            letter-spacing: normal !important;
            text-transform: none !important;
            white-space: nowrap !important;
            word-wrap: normal !important;
            direction: ltr !important;
            font-feature-settings: 'liga' !important;
            -webkit-font-smoothing: antialiased !important;
        }

        html, body, .stApp, [data-testid="stAppViewContainer"] {
            background: var(--tnts-page) !important;
        }

        #MainMenu,
        header[data-testid="stHeader"],
        footer,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"] {
            display: none !important;
        }

        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background: transparent !important;
        }

        [data-testid="stMainBlockContainer"] {
            position: relative !important;
            z-index: 1;
            max-width: 100% !important;
            min-height: 100vh !important;
            padding: 0 0 220px 0 !important;
        }

        [data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }

        .login-header {
            position: relative;
            z-index: 2;
            display: flex;
            align-items: center;
            gap: 18px;
            padding: 14px 30px;
            min-height: 82px;
            box-sizing: border-box;
            background: linear-gradient(180deg, #76000f 0%, #4b0009 100%);
            border-radius: 16px;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18);
        }

        .login-header img {
            width: 54px;
            height: 54px;
            object-fit: contain;
            flex: 0 0 auto;
        }

        .login-header .school-name {
            color: #f6e7da;
            font-family: 'Cinzel', serif !important;
            font-size: clamp(1.2rem, 2.1vw, 1.85rem);
            font-weight: 700;
            letter-spacing: 0.01em;
            text-transform: none;
            line-height: 1.1;
            max-width: calc(100vw - 150px);
        }

        .st-key-auth_spacer {
            height: 72px;
        }

        .st-key-login_card,
        .st-key-signup_card {
            position: static !important;
            width: var(--card-width);
            margin: 0 auto !important;
            overflow: visible;
            z-index: 2;
        }

        .st-key-login_card {
            height: 348px;
            border-radius: 16px;
        }

        .st-key-signup_card {
            min-height: 518px;
            padding-bottom: 32px;
            border-radius: 16px;
        }

        .page-auth-shell {
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            top: 88px;
            width: var(--card-width);
            z-index: 1;
            pointer-events: none;
        }

        .page-auth-shell.login {
            height: 348px;
        }

        .page-auth-shell.signup {
            height: 518px;
        }

        .auth-shell {
            position: absolute;
            inset: 0;
            pointer-events: none;
            z-index: 1;
        }

        .card-panel {
            position: absolute;
            inset: 0;
            background: var(--tnts-ivory);
            box-shadow: var(--tnts-shadow);
            border-radius: 16px;
            z-index: 0;
        }

        .card-panel-block {
            width: 100%;
            background: var(--tnts-ivory);
            box-shadow: var(--tnts-shadow);
            border-radius: 16px;
        }

        .login-card-panel-block {
            height: 348px;
            border-radius: 16px;
        }

        .signup-card-panel-block {
            height: 518px;
            border-radius: 16px;
        }

        .auth-tabs {
            position: absolute;
            left: 0;
            top: -40px;
            display: flex;
            align-items: end;
        }

        .auth-tabs a {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            height: 40px;
            padding: 0 18px;
            font-size: 1.05rem;
            font-weight: 800;
            text-transform: none;
            text-decoration: none !important;
            pointer-events: auto;
        }

        .auth-tabs a.active {
            background: var(--tnts-ivory);
            color: #111 !important;
            border-radius: 16px;
        }

        .auth-tabs a.idle {
            background: var(--tnts-maroon);
            color: #fff !important;
            border-radius: 16px;
        }

        .welcome-mark {
            position: absolute;
            right: 24px;
            top: 12px;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 0;
            color: #57000d;
        }

        .welcome-mark .line-1 {
            display: flex;
            align-items: center;
            gap: 7px;
            font-family: 'Cinzel', serif !important;
            font-size: clamp(1.6rem, 3vw, 2.1rem);
            text-transform: none;
            line-height: 1;
        }

        .welcome-mark .line-1 img {
            width: 20px;
            height: 20px;
            object-fit: contain;
        }

        .welcome-mark .line-2 {
            display: flex;
            align-items: center;
            gap: 10px;
            font-family: 'Cinzel', serif !important;
            font-size: 0.88rem;
            text-transform: none;
            line-height: 1;
        }

        .welcome-mark .line-2::before {
            content: "";
            width: 82px;
            height: 1px;
            background: #5f5f5f;
        }

        .card-label {
            position: absolute;
            left: var(--card-padding);
            color: #111;
            font-size: 1.08rem;
            font-weight: 700;
            line-height: 1;
            z-index: 2;
        }

        .login-user-label { top: 114px; }
        .login-pass-label { top: 207px; }
        .signup-name-label { top: 78px; }
        .signup-user-label { top: 157px; }
        .signup-email-label { top: 236px; }
        .signup-pass-label { top: 315px; }
        .signup-confirm-label { top: 394px; }

        .submit-bar {
            position: absolute;
            left: 0;
            right: 0;
            height: 28px;
            background: var(--tnts-maroon);
            border-radius: 16px;
            z-index: 1;
        }

        .login-submit-bar { top: 279px; }
        .signup-submit-bar { top: 476px; }

        .st-key-login_username,
        .st-key-login_password,
        .st-key-signup_full_name,
        .st-key-signup_username,
        .st-key-signup_email,
        .st-key-signup_password,
        .st-key-signup_confirm,
        .st-key-login_submit,
        .st-key-signup_submit {
            position: absolute !important;
            left: var(--card-padding);
            width: var(--field-width);
            z-index: 2;
        }

        .st-key-login_username { top: 224px; }
        .st-key-login_password { top: 317px; }
        .st-key-signup_full_name { top: 186px; }
        .st-key-signup_username { top: 265px; }
        .st-key-signup_email { top: 344px; }
        .st-key-signup_password { top: 423px; }
        .st-key-signup_confirm { top: 502px; }

        .st-key-login_submit,
        .st-key-signup_submit {
            left: 50%;
            width: 190px;
            transform: translateX(-50%);
        }

        .st-key-login_submit { top: 350px; }
        .st-key-signup_submit { top: 546px; }

        [data-testid="stTextInput"] label {
            display: none !important;
        }

        [data-testid="stTextInput"] > div {
            width: 100% !important;
        }

        [data-testid="stTextInput"] [data-testid="stTextInputRootElement"] {
            background: var(--tnts-maroon) !important;
            border: none !important;
            border-radius: 999px !important;
            min-height: 45px !important;
            height: 45px !important;
            box-shadow: none !important;
        }

        .st-key-login_submit button {
            box-shadow: 0 10px 24px rgba(72, 0, 12, 0.32) !important;
            transition: box-shadow 160ms ease, transform 160ms ease;
        }

        .st-key-login_submit button:hover {
            box-shadow: 0 13px 28px rgba(72, 0, 12, 0.4) !important;
            transform: translateY(-1px);
        }

        [data-testid="stTextInput"] input,
        [data-testid="stTextInput"] input[data-testid="stTextInputField"] {
            height: 45px !important;
            padding: 0 18px !important;
            background: transparent !important;
            color: #fff !important;
            -webkit-text-fill-color: #fff !important;
            caret-color: #fff !important;
            font-size: 1rem !important;
            border: none !important;
        }

        [data-testid="stTextInput"] [data-testid="stTextInputRootElement"]:focus-within {
            box-shadow: 0 0 0 3px rgba(120, 0, 24, 0.22) !important;
        }

        [data-testid="stTextInput"] button {
            position: relative !important;
            background: transparent !important;
            color: transparent !important;
            font-size: 0 !important;
            min-width: 34px !important;
            width: 34px !important;
            padding: 0 !important;
            margin-right: 8px !important;
            text-shadow: none !important;
            overflow: hidden !important;
        }

        [data-testid="stTextInput"] button::before {
            content: "";
            display: block;
            width: 18px;
            height: 18px;
            margin: 0 auto;
            background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z'/%3E%3Ccircle cx='12' cy='12' r='3'/%3E%3C/svg%3E") center / contain no-repeat;
        }

        [data-testid="stTextInput"] button svg {
            display: none !important;
        }

        .st-key-login_submit button,
        .st-key-signup_submit button {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            width: 100%;
            height: 60px;
            background: var(--tnts-maroon) !important;
            border: none !important;
            border-radius: 999px !important;
            color: #fff !important;
            box-shadow: none !important;
        }

        .st-key-login_submit button p,
        .st-key-signup_submit button p {
            position: relative;
            top: 3px;
            margin: 0 !important;
            line-height: 1 !important;
            font-size: 1.8rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.03em !important;
            color: #fff !important;
        }

        .st-key-login_submit button:hover,
        .st-key-signup_submit button:hover {
            background: #770014 !important;
            color: #fff !important;
        }

        .st-key-login_message,
        .st-key-signup_message,
        .st-key-login_db_message {
            width: var(--card-width);
            margin: 14px auto 0 auto !important;
            position: relative;
            z-index: 2;
        }

        .login-footer {
            position: fixed;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 4;
            background: rgba(236, 236, 236, 0.88);
            border-radius: 16px;
        }

        .login-footer .footer-row {
            display: flex;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
            gap: 14px;
            padding: 12px 18px 14px;
            color: #2b2b2b;
            font-size: 0.96rem;
            font-weight: 600;
        }

        .login-footer .footer-item {
            display: inline-flex;
            align-items: center;
            gap: 10px;
        }

        .login-footer .icon-circle {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: var(--tnts-maroon);
            color: #fff;
            flex: 0 0 auto;
        }

        .login-footer .sep {
            width: 2px;
            height: 26px;
            background: #262626;
        }

        .login-footer .footer-strip {
            height: 26px;
            background: var(--tnts-maroon);
            border-radius: 16px;
        }

        @media (max-width: 640px) {
            :root {
                --card-width: calc(100vw - 24px);
                --card-padding: 18px;
                --field-width: calc(var(--card-width) - 36px);
            }

            .login-header {
                padding-inline: 16px;
                gap: 12px;
            }

            .login-header img {
                width: 44px;
                height: 44px;
            }

            .login-header .school-name {
                font-size: 1.02rem;
            }

            .welcome-mark {
                right: 18px;
                top: 14px;
            }

            .welcome-mark .line-1 {
                font-size: 1.28rem;
            }

            .welcome-mark .line-2 {
                font-size: 0.76rem;
            }

            .welcome-mark .line-2::before {
                width: 54px;
            }

            .login-footer .sep {
                display: none;
            }

            .login-footer .footer-row {
                gap: 10px;
                font-size: 0.84rem;
            }

            .login-footer .footer-strip {
                height: 20px;
            }
        }

        /* Stable flow overrides for the actual Streamlit widgets */
        .page-auth-shell {
            display: none !important;
        }

        .st-key-auth_spacer {
            height: 132px;
        }

        .st-key-login_card,
        .st-key-signup_card {
            position: relative !important;
            background: var(--tnts-ivory);
            box-shadow: var(--tnts-shadow);
            border-radius: 16px;
            margin-top: 72px !important;
            padding: 22px 28px 34px !important;
            min-height: auto !important;
            height: auto !important;
        }

        .st-key-login_username,
        .st-key-login_password,
        .st-key-signup_full_name,
        .st-key-signup_username,
        .st-key-signup_email,
        .st-key-signup_password,
        .st-key-signup_confirm {
            position: static !important;
            left: auto !important;
            top: auto !important;
            width: 100% !important;
            transform: none !important;
            margin: 0 0 18px 0 !important;
        }

        .st-key-login_submit,
        .st-key-signup_submit {
            position: static !important;
            left: auto !important;
            top: auto !important;
            width: 100% !important;
            transform: none !important;
            margin: 0 !important;
        }

        .card-heading-inline {
            position: relative;
            height: 96px;
            margin-bottom: 16px;
        }

        .card-heading-inline .auth-tabs {
            top: -52px;
            left: -28px;
        }

        .card-heading-inline .welcome-mark {
            top: 0;
            left: 0;
            right: 0;
            width: 100%;
            min-height: 78px;
            box-sizing: border-box;
            align-items: center;
            justify-content: center;
            padding: 8px 18px;
            background: #f0e3e5;
            border-radius: 16px;
            box-shadow: 0 8px 18px rgba(0, 0, 0, 0.12);
            text-align: center;
        }

        .card-heading-inline .welcome-mark .line-1 {
            justify-content: center;
            gap: 10px;
            font-size: clamp(2rem, 5vw, 2.8rem);
        }

        .card-heading-inline .welcome-mark .line-1 img {
            width: 30px;
            height: 30px;
        }

        .card-heading-inline .welcome-mark .line-2 {
            justify-content: center;
            gap: 14px;
            font-size: 1.12rem;
            letter-spacing: 0.12em;
        }

        .card-heading-inline .welcome-mark .line-2::before,
        .card-heading-inline .welcome-mark .line-2::after {
            content: "";
            width: clamp(52px, 12vw, 110px);
            height: 2px;
            background: #7b4850;
        }

        .field-label-inline {
            display: block;
            position: relative;
            z-index: 3;
            margin: 0 0 15px;
            color: #111;
            font-size: 1.1rem;
            font-weight: 700;
            line-height: 1.25;
        }

        .button-bar-inline {
            height: 28px;
            background: var(--tnts-maroon);
            margin: 18px -28px -44px;
        }

        .st-key-login_submit,
        .st-key-signup_submit {
            width: 190px !important;
            margin: 0 auto !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        components.website_background_css("rgba(255, 255, 255, .18)"),
        unsafe_allow_html=True,
    )


def login_header_html(school_name: str, logo_uri: str) -> str:
    return dedent(
        f"""
        <div class="login-header">
            <img src="{logo_uri}" alt="TNTS Logo">
            <div class="school-name">{school_name}</div>
        </div>
        """
    ).strip()


def footer_html() -> str:
    return dedent(
        f"""
        <div class="login-footer">
          <div class="footer-row">
            <div class="footer-item">
              <svg viewBox="0 0 24 24" width="24" height="24" fill="#56000d"><path d="M12 2C8.1 2 5 5.1 5 9c0 5.2 7 13 7 13s7-7.8 7-13c0-3.9-3.1-7-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg>
              <span>{ADDRESS}</span>
            </div>
            <div class="sep"></div>
            <div class="footer-item">
              <span class="icon-circle"><svg viewBox="0 0 24 24" width="20" height="20" fill="#fff"><path d="M6.6 10.8c1.4 2.8 3.8 5.1 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1C10.6 21 3 13.4 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1L6.6 10.8z"/></svg></span>
              <span>{PHONE}</span>
            </div>
            <div class="sep"></div>
            <div class="footer-item">
              <svg viewBox="0 0 24 24" width="30" height="30" fill="#56000d"><path d="M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zm0 4-8 5-8-5V6l8 5 8-5v2z"/></svg>
              <span>{EMAIL}</span>
            </div>
          </div>
          <div class="footer-strip"></div>
        </div>
        """
    ).strip()


def auth_shell_html(mode: str, small_logo_uri: str) -> str:
    login_class = "active" if mode == "login" else "idle"
    signup_class = "active" if mode == "signup" else "idle"
    return dedent(
        f"""
        <div class="auth-shell">
          <div class="card-panel"></div>
          <div class="auth-tabs">
            <a class="{login_class}" href="?mode=login" target="_self">Log In</a>
            <a class="{signup_class}" href="?mode=signup" target="_self">Sign Up</a>
          </div>
          <div class="welcome-mark">
            <div class="line-1">Welcome <img src="{small_logo_uri}" alt=""></div>
            <div class="line-2">to TNTS</div>
          </div>
        </div>
        """
    ).strip()


def login_shell_html(small_logo_uri: str) -> str:
    return (
        auth_shell_html("login", small_logo_uri)
        + dedent(
            """
            <div class="card-label login-user-label">Username:</div>
            <div class="card-label login-pass-label">Password:</div>
            <div class="submit-bar login-submit-bar"></div>
            """
        ).strip()
    )


def signup_shell_html(small_logo_uri: str) -> str:
    return (
        auth_shell_html("signup", small_logo_uri)
        + dedent(
            """
            <div class="card-label signup-name-label">Full Name:</div>
            <div class="card-label signup-user-label">Username:</div>
            <div class="card-label signup-email-label">Email:</div>
            <div class="card-label signup-pass-label">Password:</div>
            <div class="card-label signup-confirm-label">Re-enter Password:</div>
            <div class="submit-bar signup-submit-bar"></div>
            """
        ).strip()
    )


def page_auth_shell_html(mode: str, small_logo_uri: str) -> str:
    shell = signup_shell_html(small_logo_uri) if mode == "signup" else login_shell_html(small_logo_uri)
    return dedent(
        f"""
        <div class="page-auth-shell {mode}">
          {shell}
        </div>
        """
    ).strip()


def card_heading_html(mode: str, small_logo_uri: str) -> str:
    login_class = "active" if mode == "login" else "idle"
    signup_class = "active" if mode == "signup" else "idle"
    return dedent(
        f"""
        <div class="card-heading-inline">
          <div class="auth-tabs">
            <a class="{login_class}" href="?mode=login" target="_self">Log In</a>
            <a class="{signup_class}" href="?mode=signup" target="_self">Sign Up</a>
          </div>
          <div class="welcome-mark">
            <div class="line-1">Welcome <img src="{small_logo_uri}" alt=""></div>
            <div class="line-2">to TNTS</div>
          </div>
        </div>
        """
    ).strip()


def login_form(database_ok: bool, small_logo_uri: str) -> None:
    with st.container(key="login_card"):
        st.markdown(card_heading_html("login", small_logo_uri), unsafe_allow_html=True)
        st.markdown('<div class="field-label-inline">Username:</div>', unsafe_allow_html=True)
        username = st.text_input("Username", key="login_username", label_visibility="collapsed")
        st.markdown('<div class="field-label-inline">Password:</div>', unsafe_allow_html=True)
        password = st.text_input("Password", key="login_password", type="password", label_visibility="collapsed")
        st.markdown('<div class="button-bar-inline"></div>', unsafe_allow_html=True)
        clicked = st.button("Log In", key="login_submit")

    with st.container(key="login_message"):
        if not clicked:
            return
        if not username or not password:
            st.warning("Please enter both your username and password.")
        elif not database_ok:
            st.error("No database connection, so the login cannot be checked.")
        elif auth_guard.login(username, password):
            st.session_state["auth_transition_loading"] = True
            st.session_state["auth_transition_ticks_remaining"] = 2
            st.rerun()
        else:
            problem = auth_guard.login_problem(username, password)
            if problem == "pending":
                st.info(
                    "Your account was created, but an administrator has not verified it yet. "
                    "You can log in as soon as your account is approved."
                )
            elif problem == "blocked":
                st.error("This account has been switched off by an administrator.")
            else:
                st.error("Incorrect username or password.")


def signup_form(database_ok: bool, small_logo_uri: str) -> None:
    """Create adviser accounts while preserving the live project auth flow."""
    with st.container(key="signup_card"):
        st.markdown(card_heading_html("signup", small_logo_uri), unsafe_allow_html=True)
        st.markdown('<div class="field-label-inline">Full Name:</div>', unsafe_allow_html=True)
        full_name = st.text_input("Full Name", key="signup_full_name", label_visibility="collapsed")
        st.markdown('<div class="field-label-inline">Username:</div>', unsafe_allow_html=True)
        username = st.text_input("Username", key="signup_username", label_visibility="collapsed")
        st.markdown('<div class="field-label-inline">Email:</div>', unsafe_allow_html=True)
        email = st.text_input("Email", key="signup_email", label_visibility="collapsed")
        st.markdown('<div class="field-label-inline">Password:</div>', unsafe_allow_html=True)
        password = st.text_input("Password", key="signup_password", type="password", label_visibility="collapsed")
        st.markdown('<div class="field-label-inline">Re-enter Password:</div>', unsafe_allow_html=True)
        confirm = st.text_input(
            "Re-enter Password",
            key="signup_confirm",
            type="password",
            label_visibility="collapsed",
        )
        st.markdown('<div class="button-bar-inline"></div>', unsafe_allow_html=True)
        clicked = st.button("Sign Up", key="signup_submit")

    with st.container(key="signup_message"):
        if not clicked:
            return
        if not full_name.strip() or not username.strip() or not password or not confirm:
            st.warning("Please fill in all required fields.")
        elif email.strip() and not EMAIL_RE.match(email.strip()):
            st.warning("Please enter a valid email address.")
        elif not database_ok:
            st.error("No database connection, so the account cannot be created.")
        elif len(password) < 6:
            st.warning("Your password must be at least 6 characters long.")
        elif password != confirm:
            st.error("Passwords do not match. Please re-enter your password.")
        else:
            try:
                with get_session() as session:
                    auth_service.register_adviser(
                        session,
                        username=username,
                        password=password,
                        full_name=full_name,
                        email=email,
                    )
            except ValueError as error:
                st.error(str(error))
                return
            st.success(
                "Your account has been created. An administrator must verify it before you can log in. "
                "Please wait for approval."
            )


@st.fragment
def render_login_page() -> None:
    """Show the TNTS auth page until a user successfully signs in."""
    database_ok, database_message = test_connection()
    try:
        with get_session() as session:
            school_name = settings_service.school_name(session)
    except Exception:
        school_name = settings.school_name

    logo_uri = logo_data_uri()
    small_logo_uri = logo_uri
    mode = st.query_params.get("mode", "login")
    mode = mode if mode in {"login", "signup"} else "login"

    login_page_css()
    st.markdown(login_header_html(school_name, logo_uri), unsafe_allow_html=True)
    st.container(key="auth_spacer")

    if not database_ok:
        with st.container(key="login_db_message"):
            st.error(
                "The system cannot reach the PostgreSQL database, so logging in is not possible yet.\n\n"
                f"Details: {database_message}\n\n"
                "Check the DB_* values in your .env file, make sure the PostgreSQL service is running, "
                "then run `python setup_db.py` once to create the tables."
            )

    if mode == "signup":
        signup_form(database_ok, small_logo_uri)
    else:
        login_form(database_ok, small_logo_uri)

    st.markdown(footer_html(), unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Menu
# ----------------------------------------------------------------------
def build_navigation(user: dict):
    """
    Create the sidebar menu.

    Advisers get the monitoring pages only. Administrators get an extra
    "Administration" section at the bottom, which also holds the gate scanner
    (the device at the entrance belongs to the administrative department).
    """
    monitoring = [
        st.Page(st.fragment(dashboard.render), title="Dashboard", icon="\U0001F4CA", url_path="dashboard", default=True),
        st.Page(st.fragment(students.render), title="Students", icon="\U0001F393", url_path="students"),
        st.Page(st.fragment(attendance.render), title="Attendance", icon="\U0001F5D3\uFE0F", url_path="attendance"),
        st.Page(st.fragment(qr_codes.render), title="QR Codes & ID Cards", icon="\U0001F533", url_path="qr-codes"),
        st.Page(st.fragment(reports.render), title="Reports", icon="\U0001F4C8", url_path="reports"),
    ]

    if user["role"] != "admin":
        return st.navigation({"Monitoring": monitoring})

    administration = [
        st.Page(st.fragment(classes.render), title="Classes & Advisers", icon="\U0001F3EB", url_path="classes"),
        st.Page(st.fragment(users.render), title="Users & Accounts", icon="\U0001F465", url_path="users"),
        st.Page(kiosk.render, title="Gate Scanner", icon="\U0001F4F7", url_path="kiosk"),
        st.Page(
            st.fragment(kiosk_management.render),
            title="Kiosk Management",
            icon="\U0001F5A5\uFE0F",
            url_path="kiosk-management",
        ),
        st.Page(st.fragment(settings_page.render), title="System Settings", icon="\u2699\uFE0F", url_path="settings"),
    ]

    return st.navigation({"Monitoring": monitoring, "Administration": administration})


# ----------------------------------------------------------------------
# Start
# ----------------------------------------------------------------------
def main() -> None:
    if not st.session_state.get("_daily_attendance_limit_ready"):
        database_ok, _ = test_connection()
        if database_ok:
            try:
                ensure_daily_attendance_unique_index()
            except (SQLAlchemyError, RuntimeError) as error:
                st.error(f"Could not enforce the one-record-per-student-per-day rule: {error}")
                st.stop()
            st.session_state["_daily_attendance_limit_ready"] = True

    migration_version = st.session_state.get("_qr_token_migration_version")
    current_qr_key_fingerprint = student_service.current_qr_signing_key_fingerprint()
    if migration_version != current_qr_key_fingerprint:
        database_ok, _ = test_connection()
        if database_ok:
            try:
                with get_session() as session:
                    migration_version = student_service.ensure_current_qr_tokens(session)
            except (SQLAlchemyError, RuntimeError) as error:
                st.error(f"Could not initialize secure student QR codes: {error}")
                st.stop()

            if migration_version != st.session_state.get("_qr_token_migration_version"):
                st.session_state.pop("qr_zip", None)
                st.session_state.pop("all_student_qr_reissue_zip", None)
            st.session_state["_qr_token_migration_version"] = migration_version

    if st.session_state.get("auth_transition_loading"):
        components.auth_loading_screen()
        components.finish_auth_transition()
        st.stop()

    if not auth_guard.is_logged_in():
        render_login_page()
        st.stop()

    user = auth_guard.current_user()
    navigation = build_navigation(user)
    components.sidebar_user_panel()
    navigation.run()


main()
