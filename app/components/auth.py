"""
Componentes de Autenticacion para Streamlit

Cloud Migration - Fase 5

Este modulo contiene componentes de UI para autenticacion:
- render_login_page: Pagina de login completa
- render_user_info: Info del usuario en sidebar
- check_authentication: Verificar y mostrar login si necesario

Uso:
    from app.components.auth import check_authentication, render_user_info

    # En main.py - verificar auth al inicio
    if not check_authentication():
        st.stop()

    # En sidebar - mostrar info del usuario
    render_user_info()
"""

import streamlit as st
from src.services.auth_service import AuthService
from src.core.environment import is_cloud_environment


def render_login_page() -> bool:
    """
    Renderiza la pagina de login.

    Returns:
        True si el usuario se autentico exitosamente, False si no
    """
    st.set_page_config(
        page_title="Investment Tracker - Login",
        page_icon="🔐",
        layout="centered",
        initial_sidebar_state="collapsed"
    )

    # CSS para ocultar completamente el sidebar y la navegacion
    st.markdown("""
        <style>
            /* Ocultar sidebar completo */
            [data-testid="stSidebar"] {
                display: none;
            }
            /* Ocultar boton de expandir sidebar */
            [data-testid="collapsedControl"] {
                display: none;
            }
            /* Ocultar navegacion de paginas en header */
            [data-testid="stSidebarNavItems"] {
                display: none;
            }
            /* Centrar contenido */
            .block-container {
                max-width: 400px;
                padding-top: 5rem;
            }
        </style>
    """, unsafe_allow_html=True)

    st.title("🔐 Investment Tracker")
    st.markdown("---")

    # Formulario de login
    with st.form("login_form", clear_on_submit=False):
        st.subheader("Iniciar Sesion")

        username = st.text_input(
            "Usuario",
            placeholder="Introduce tu usuario",
            key="login_username"
        )

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Introduce tu password",
            key="login_password"
        )

        col1, col2 = st.columns([1, 2])
        with col1:
            submitted = st.form_submit_button("Entrar", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Por favor, introduce usuario y password")
                return False

            # Verificar credenciales
            user_info = AuthService.verify_credentials(username, password)

            if user_info:
                # Login exitoso
                AuthService.login(st.session_state, user_info)
                st.success(f"Bienvenido, {username}!")
                st.rerun()
                return True
            else:
                st.error("Usuario o password incorrectos")
                return False

    # Info adicional
    st.markdown("---")
    st.caption("Investment Tracker - Cloud Version")

    return False


def render_login_form_compact() -> bool:
    """
    Renderiza un formulario de login compacto (para sidebar o modal).

    Returns:
        True si autenticado, False si no
    """
    with st.form("login_compact", clear_on_submit=False):
        username = st.text_input("Usuario", key="compact_user")
        password = st.text_input("Password", type="password", key="compact_pass")
        submitted = st.form_submit_button("Entrar")

        if submitted and username and password:
            user_info = AuthService.verify_credentials(username, password)
            if user_info:
                AuthService.login(st.session_state, user_info)
                st.rerun()
                return True
            else:
                st.error("Credenciales incorrectas")

    return AuthService.is_authenticated(st.session_state)


def render_user_info() -> None:
    """
    Renderiza informacion del usuario en el sidebar.

    Muestra:
    - Nombre de usuario
    - Nombre del portfolio
    - Boton de cerrar sesion
    """
    if not AuthService.is_authenticated(st.session_state):
        return

    user = AuthService.get_current_user(st.session_state)
    if not user:
        return

    st.sidebar.markdown("---")

    # Info del usuario
    username = user.get('username', 'Usuario')
    portfolio_name = user.get('portfolio_name') or f"Portfolio {user.get('portfolio_id')}"

    st.sidebar.markdown(f"**Usuario:** {username}")
    st.sidebar.markdown(f"**Cartera:** {portfolio_name}")

    # Boton de logout
    if st.sidebar.button("Cerrar Sesion", use_container_width=True):
        AuthService.logout(st.session_state)
        st.rerun()


def render_portfolio_selector_or_info(profile_manager) -> None:
    """
    Renderiza selector de portfolio (local) o info fija (cloud).

    En modo local: Muestra selector de carteras
    En modo cloud: Muestra solo el nombre de la cartera asignada

    Args:
        profile_manager: LocalProfileManager o CloudProfileManager
    """
    if profile_manager.can_switch_portfolio():
        # Modo local: selector de carteras
        portfolios = profile_manager.get_profile_names()
        current = profile_manager.get_default_profile()

        if portfolios:
            selected = st.sidebar.selectbox(
                "Cartera",
                portfolios,
                index=portfolios.index(current) if current in portfolios else 0
            )
            return selected
    else:
        # Modo cloud: solo mostrar info
        portfolio_name = profile_manager.get_portfolio_name()
        st.sidebar.info(f"📁 {portfolio_name}")
        return portfolio_name

    return None


def check_authentication() -> bool:
    """
    Verifica autenticacion y muestra login si es necesario.

    Esta funcion debe llamarse al inicio de main.py.
    - En modo local: Siempre retorna True (no requiere auth)
    - En modo cloud: Muestra login si no autenticado

    Returns:
        True si puede continuar, False si debe detenerse

    Uso:
        if not check_authentication():
            st.stop()
    """
    # En modo local, no se requiere autenticacion
    if not is_cloud_environment():
        return True

    # En modo cloud, verificar si esta autenticado
    if AuthService.is_authenticated(st.session_state):
        return True

    # No autenticado - mostrar pagina de login
    render_login_page()
    return False


def init_session_state() -> None:
    """
    Inicializa las variables de session_state necesarias.

    Debe llamarse al inicio de la app.
    """
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False

    if 'username' not in st.session_state:
        st.session_state['username'] = None

    if 'portfolio_id' not in st.session_state:
        st.session_state['portfolio_id'] = None

    if 'portfolio_name' not in st.session_state:
        st.session_state['portfolio_name'] = None


def require_auth(page_title: str, page_icon: str, layout: str = "wide") -> bool:
    """
    Configura la pagina y verifica autenticacion.

    Esta funcion DEBE llamarse al inicio de cada pagina en app/pages/.
    Combina st.set_page_config con la verificacion de autenticacion.

    Args:
        page_title: Titulo de la pagina
        page_icon: Icono de la pagina
        layout: Layout de la pagina (default: "wide")

    Returns:
        True si puede continuar, False si debe detenerse (st.stop())

    Uso:
        from app.components.auth import require_auth

        if not require_auth("Dashboard", "📊"):
            st.stop()

        # Resto de la pagina...
    """
    init_session_state()

    # En modo local, no requiere autenticacion
    if not is_cloud_environment():
        st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)
        return True

    # En modo cloud, verificar si esta autenticado
    if AuthService.is_authenticated(st.session_state):
        st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)
        return True

    # No autenticado - mostrar pagina de login
    render_login_page()
    return False
