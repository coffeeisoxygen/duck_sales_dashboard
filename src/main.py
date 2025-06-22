"""Business Dashboard - Main Streamlit Application.

Handles authentication, navigation, and core app initialization.
"""

import streamlit as st

from m_logg import logger, setup_logging


def setup_app_state() -> None:
    """Set up the initial state of the Streamlit app.

    This function initializes the session state variables used for
    logging and user authentication.
    """
    if "log_configured" not in st.session_state:
        setup_logging()
        st.session_state.log_configured = True
        logger.info("🚀 App started")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    # # Force database initialization on app start
    # if "db_initialized" not in st.session_state:
    #     if initialize_database():
    #         st.session_state.db_initialized = True
    #         logger.info("✅ Database initialized on app start")
    #     else:
    #         logger.error("❌ Database initialization failed")
    #         st.error("❌ Database not available. Please contact admin.")
    #         st.stop()


# =============================================================================
# AUTH
# =============================================================================


def login_form() -> None:
    """Display the login form for the Business Dashboard.

    This form allows users to log in to the dashboard.
    """
    st.title("🔐 Business Dashboard Login")
    if st.button("Log in", type="primary", use_container_width=True):
        st.session_state.logged_in = True
        logger.info("👤 User logged in")
        st.rerun()


def logout_button() -> None:
    """Display the logout button for the Business Dashboard.

    This button allows users to log out of the dashboard.
    """
    if st.sidebar.button("🚪 Log out", type="secondary"):
        st.session_state.logged_in = False
        logger.info("👤 User logged out")
        st.rerun()


# =============================================================================
# NAVIGATION
# =============================================================================


def create_navigation():
    """Create navigation structure based on login status."""
    if not st.session_state.logged_in:
        return st.navigation([st.Page(login_form, title="Login", icon="🔐")])

    return st.navigation(
        {
            "Overview": [
                st.Page(
                    "pages/reports/dashboard.py",
                    title="Dashboard",
                    icon=":material/dashboard:",
                    default=True,
                ),
            ],
            "Analysis": [
                st.Page(
                    "pages/masters/transactions.py",
                    title="Transactions",
                    icon=":material/award_star:",
                ),
                st.Page(
                    "pages/masters/rgu.py", title="RGU", icon=":material/sim_card:"
                ),
                st.Page("pages/masters/sellin.py", title="Sell-in", icon="📦"),
                st.Page("pages/masters/tertiary.py", title="Tertiary", icon="⭐"),
            ],
            "Data": [
                st.Page(
                    "pages/masters/organizations.py", title="Organizations", icon="🤝"
                ),
                st.Page("pages/masters/site.py", title="Site", icon="🗼"),
                st.Page("pages/masters/desa.py", title="Desa", icon="🏘️"),
            ],
        }
    )


# =============================================================================
# MAIN ENTRY
# =============================================================================


def main() -> None:
    """Main entry point for the Business Dashboard.

    This function sets up the Streamlit app configuration and initializes
    the application state.
    """
    st.set_page_config("Business Dashboard", ":streamlit:", layout="wide")
    setup_app_state()

    if st.session_state.logged_in:
        logout_button()

    nav = create_navigation()
    nav.run()


if __name__ == "__main__":
    main()
