import re
from pathlib import Path

from core.version import VERSION


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_legacy_router_uses_allowlisted_route_resolution() -> None:
    router_js = (REPO_ROOT / "core" / "ui" / "js" / "router.js").read_text(encoding="utf-8")

    assert "const routes = Object.create(null);" in router_js
    assert "Object.prototype.hasOwnProperty.call(routes, path)" in router_js
    assert "const handler = resolveRoute(path);" in router_js
    assert "typeof handler === 'function'" in router_js
    assert "routes[path] || routes['/home']" not in router_js


def test_shell_still_uses_app_js_as_canonical_router() -> None:
    shell_html = (REPO_ROOT / "core" / "ui" / "shell.html").read_text(encoding="utf-8")

    assert '<script type="module" src="/ui/app.js' in shell_html


def test_shell_assets_use_current_version_cache_token() -> None:
    shell_html = (REPO_ROOT / "core" / "ui" / "shell.html").read_text(encoding="utf-8")

    assert f'href="/ui/css/app.css?v=buscore-{VERSION}"' in shell_html
    assert f'src="/ui/app.js?v=buscore-{VERSION}"' in shell_html


def test_native_launcher_opens_versioned_shell_url() -> None:
    launcher_py = (REPO_ROOT / "launcher.py").read_text(encoding="utf-8")

    assert "/ui/shell.html?v=buscore-{CURRENT_VERSION}" in launcher_py


def test_shell_exposes_auth_and_security_mount_points() -> None:
    shell_html = (REPO_ROOT / "core" / "ui" / "shell.html").read_text(encoding="utf-8")

    assert 'data-role="auth-banner"' in shell_html
    assert 'data-role="auth-gate-screen"' in shell_html
    assert 'data-role="sidebar-auth-zone"' in shell_html
    assert 'href="#/security"' in shell_html
    assert 'data-role="security-root"' in shell_html


def test_auth_client_does_not_use_localstorage_for_authority() -> None:
    auth_js = (REPO_ROOT / "core" / "ui" / "js" / "auth.js").read_text(encoding="utf-8")

    assert "localStorage" not in auth_js
    for name in (
        "getAuthState",
        "setupOwner",
        "recoverAccount",
        "regenerateRecoveryCodes",
        "login",
        "logout",
        "getMe",
        "listUsers",
        "createUser",
        "updateUser",
        "disableUser",
        "enableUser",
        "resetPassword",
        "listRoles",
        "setUserRoles",
        "listSessions",
        "revokeSession",
        "listAudit",
    ):
        assert f"function {name}" in auth_js


def test_auth_ui_modules_do_not_store_secrets_or_authority() -> None:
    sensitive_terms = ("password", "recovery", "session", "token", "permission", "auth")
    for relative in (
        ("core", "ui", "app.js"),
        ("core", "ui", "js", "auth.js"),
        ("core", "ui", "js", "auth-ui.js"),
        ("core", "ui", "js", "security.js"),
    ):
        source = (REPO_ROOT / Path(*relative)).read_text(encoding="utf-8")
        for line in source.splitlines():
            if "localStorage" in line or "sessionStorage" in line:
                lowered = line.lower()
                assert not any(term in lowered for term in sensitive_terms), line


def test_recovery_codes_are_rendered_once_without_storage() -> None:
    auth_ui_js = (REPO_ROOT / "core" / "ui" / "js" / "auth-ui.js").read_text(encoding="utf-8")

    assert "renderRecoveryCodes" in auth_ui_js
    assert "result?.recovery_codes" in auth_ui_js
    assert "onContinue?.();" in auth_ui_js
    assert "localStorage" not in auth_ui_js
    assert "sessionStorage" not in auth_ui_js


def test_login_screen_includes_recovery_entry_point_and_generic_recovery_flow() -> None:
    auth_js = (REPO_ROOT / "core" / "ui" / "js" / "auth.js").read_text(encoding="utf-8")
    auth_ui_js = (REPO_ROOT / "core" / "ui" / "js" / "auth-ui.js").read_text(encoding="utf-8")

    assert "function recoverAccount" in auth_js
    assert "authRequest('/auth/recover', 'POST', payload)" in auth_js
    assert "Forgot password?" in auth_ui_js
    assert "data-action=\"recover-account\"" in auth_ui_js
    assert "data-form=\"recover-account\"" in auth_ui_js
    assert "recovery_code" in auth_ui_js
    assert "new_password" in auth_ui_js
    assert "confirm_password" in auth_ui_js
    assert "Passwords do not match." in auth_ui_js
    assert "Unable to recover account. Check the recovery information and try again." in auth_ui_js
    assert "Password reset. Sign in with your new password." in auth_ui_js
    assert "renderLogin(root, { ...options, loginMessage:" in auth_ui_js


def test_security_ui_regenerates_recovery_codes_once_without_storage() -> None:
    auth_js = (REPO_ROOT / "core" / "ui" / "js" / "auth.js").read_text(encoding="utf-8")
    security_js = (REPO_ROOT / "core" / "ui" / "js" / "security.js").read_text(encoding="utf-8")

    assert "function regenerateRecoveryCodes" in auth_js
    assert "authRequest('/auth/recovery-codes/regenerate', 'POST', payload)" in auth_js
    assert "Regenerate recovery codes" in security_js
    assert "This invalidates unused old recovery codes." in security_js
    assert "await regenerateRecoveryCodes({});" in security_js
    assert "result?.recovery_codes" in security_js
    assert "I saved these codes" in security_js
    assert "target.innerHTML = '';" in security_js
    assert "await refreshAfterSecurityMutation(root);" in security_js
    assert "localStorage" not in security_js
    assert "sessionStorage" not in security_js


def test_app_boot_checks_auth_state_before_protected_mount() -> None:
    app_js = (REPO_ROOT / "core" / "ui" / "app.js").read_text(encoding="utf-8")

    assert "await refreshAuthState();\n    if (!canMountNormalApp())" in app_js
    assert "bindSidebarUpdateControls();\n    mountBackupExport();\n    maybeRunStartupUpdateCheck();\n    await refreshAuthState();" in app_js
    assert "await maybeRunStartupUpdateCheck();" not in app_js
    assert "showLoginGate();" in app_js
    assert "openClaimScreen" in app_js
    assert "#/security" in app_js


def test_startup_update_check_uses_public_path_without_auth_boot_dependencies() -> None:
    update_js = (REPO_ROOT / "core" / "ui" / "js" / "update-check.js").read_text(encoding="utf-8")

    startup_section = update_js.split("export async function maybeRunStartupUpdateCheck()", 1)[1]
    assert "startupCheckDone = true" in startup_section
    assert "executeCheck({ manual: false })" in startup_section
    assert "ensureToken" not in startup_section
    assert "/app/config" not in startup_section
    assert "apiGet" not in startup_section


def test_lazorallthecore_pass1_ui_polish_is_scoped() -> None:
    app_js = (REPO_ROOT / "core" / "ui" / "app.js").read_text(encoding="utf-8")
    backup_js = (REPO_ROOT / "core" / "ui" / "js" / "cards" / "backup.js").read_text(encoding="utf-8")
    finance_js = (REPO_ROOT / "core" / "ui" / "js" / "cards" / "finance.js").read_text(encoding="utf-8")
    inventory_js = (REPO_ROOT / "core" / "ui" / "js" / "cards" / "inventory.js").read_text(encoding="utf-8")
    manufacturing_js = (REPO_ROOT / "core" / "ui" / "js" / "cards" / "manufacturing.js").read_text(encoding="utf-8")
    recipes_js = (REPO_ROOT / "core" / "ui" / "js" / "cards" / "recipes.js").read_text(encoding="utf-8")
    settings_js = (REPO_ROOT / "core" / "ui" / "js" / "cards" / "settings.js").read_text(encoding="utf-8")

    assert "Output Product" in recipes_js
    assert "Product is the inventory item you build or sell." in recipes_js
    assert "If the product is not listed, create it in Inventory first." in recipes_js
    assert "Create output product" not in recipes_js

    assert "Usual product price:" in inventory_js
    assert "Below usual product price" in inventory_js
    assert "priceText !== ''" in inventory_js
    assert "below-cost" not in inventory_js.lower()

    assert "Not enough ${name}: need" in manufacturing_js
    assert "Run #${rid}" in manufacturing_js
    assert "notes" not in manufacturing_js.split("function loadRecentRuns30d", 1)[1]

    for preset in ("Last 30 days", "This month", "Last month", "This quarter", "Last quarter", "This year"):
        assert preset in finance_js

    assert "Demo data stays separate." in app_js
    assert "Settings > Administration > Backup Export" in app_js
    assert "Enable automatic update checks" not in settings_js
    assert "Startup checks run once per launch." in settings_js

    assert "/app/backup" not in backup_js
    assert "/app.db" not in backup_js
    assert "Settings > Administration > Backup Export" in backup_js


def test_legacy_home_transaction_loader_is_not_mounted() -> None:
    app_js = (REPO_ROOT / "core" / "ui" / "app.js").read_text(encoding="utf-8")

    assert not (REPO_ROOT / "core" / "ui" / "js" / "cards" / "home_donuts.js").exists()
    assert "home_donuts" not in app_js


def test_security_ui_refreshes_auth_state_after_permission_sensitive_actions() -> None:
    app_js = (REPO_ROOT / "core" / "ui" / "app.js").read_text(encoding="utf-8")
    security_js = (REPO_ROOT / "core" / "ui" / "js" / "security.js").read_text(encoding="utf-8")

    assert "onAuthRefresh: refreshAuthState" in app_js
    assert "onLoginRequired: showLoginGate" in app_js
    assert "refreshAuthForSecurity" in security_js
    assert "refreshAfterSecurityMutation(root)" in security_js
    assert security_js.count("await refreshAfterSecurityMutation(root);") >= 3
    assert "error?.status === 401" in security_js
    assert "error?.status === 403" in security_js


def test_token_helper_accepts_claimed_mode_login_required() -> None:
    token_js = (REPO_ROOT / "core" / "ui" / "js" / "token.js").read_text(encoding="utf-8")

    assert "body?.error === 'login_required'" in token_js
    assert "_claimedModeNoLegacyToken = true" in token_js


def test_jobs_phase2_ui_route_is_permissioned_and_mounted() -> None:
    app_js = (REPO_ROOT / "core" / "ui" / "app.js").read_text(encoding="utf-8")
    shell_html = (REPO_ROOT / "core" / "ui" / "shell.html").read_text(encoding="utf-8")
    jobs_js = (REPO_ROOT / "core" / "ui" / "js" / "cards" / "jobs.js").read_text(encoding="utf-8")

    assert "import { mountJobs, unmountJobs } from \"./js/cards/jobs.js\";" in app_js
    assert "'#/jobs': showJobs" in app_js
    assert "jobs: ['jobs.read']" in app_js
    assert "async function showJobs()" in app_js
    assert 'href="#/jobs" data-role="nav-link" data-route="jobs"' in shell_html
    sidebar_tools = shell_html.split('<ul class="sidebar-nav">', 1)[1].split('nav-section--system', 1)[0]
    assert re.findall(r'data-route="([^"]+)"', sidebar_tools) == [
        "manufacturing",
        "inventory",
        "contacts",
        "recipes",
        "jobs",
        "invoices",
        "finance",
    ]
    assert 'data-role="jobs-screen"' in shell_html
    assert 'data-role="jobs-root"' in shell_html
    assert "export async function mountJobs()" in jobs_js
    assert "export function unmountJobs()" in jobs_js


def test_invoices_phase1_ui_route_is_permissioned_and_mounted() -> None:
    app_js = (REPO_ROOT / "core" / "ui" / "app.js").read_text(encoding="utf-8")
    shell_html = (REPO_ROOT / "core" / "ui" / "shell.html").read_text(encoding="utf-8")
    invoices_js = (REPO_ROOT / "core" / "ui" / "js" / "cards" / "invoices.js").read_text(encoding="utf-8")

    assert 'import { mountInvoices, unmountInvoices } from "./js/cards/invoices.js";' in app_js
    assert "'#/invoices': showInvoices" in app_js
    assert "invoices: ['invoices.read']" in app_js
    assert "async function showInvoices()" in app_js
    assert 'href="#/invoices" data-role="nav-link" data-route="invoices"' in shell_html
    assert 'data-role="invoices-screen"' in shell_html
    assert 'data-role="invoices-root"' in shell_html
    assert "export async function mountInvoices()" in invoices_js
    assert "export function unmountInvoices()" in invoices_js


def test_jobs_phase2_ui_uses_only_jobs_and_read_lookup_endpoints() -> None:
    jobs_js = (REPO_ROOT / "core" / "ui" / "js" / "cards" / "jobs.js").read_text(encoding="utf-8")

    endpoints = sorted(set(re.findall(r"['`](/app/[^'`]+)", jobs_js)))
    assert endpoints
    allowed_prefixes = ("/app/jobs", "/app/contacts", "/app/items", "/app/recipes")
    for endpoint in endpoints:
        assert endpoint.startswith(allowed_prefixes), endpoint

    forbidden_endpoint_terms = (
        "/app/stock",
        "/app/finance",
        "/app/manufacturing",
        "/app/purchase",
        "/app/payments",
        "/app/reserve",
        "/app/deliver",
    )
    for term in forbidden_endpoint_terms:
        assert term not in jobs_js

    assert "apiPost(`/app/jobs/${job.id}/status`, { status })" in jobs_js
    assert "apiPost(`/app/jobs/${job.id}/lines`, payload)" in jobs_js
    assert "apiPost(`/app/jobs/${job.id}/events`, { event_type: 'note', message: text })" in jobs_js


def test_invoices_phase1_ui_uses_only_invoice_contact_and_job_endpoints() -> None:
    invoices_js = (REPO_ROOT / "core" / "ui" / "js" / "cards" / "invoices.js").read_text(encoding="utf-8")

    endpoints = sorted(set(re.findall(r"['`](/app/[^'`]+)", invoices_js)))
    assert endpoints
    allowed_prefixes = ("/app/invoices", "/app/contacts", "/app/jobs")
    for endpoint in endpoints:
        assert endpoint.startswith(allowed_prefixes), endpoint

    forbidden_endpoint_terms = (
        "/app/stock",
        "/app/finance/export",
        "/app/manufacturing",
        "/app/purchase",
        "/app/payments",
        "/app/accounting",
        "/app/portal",
    )
    for term in forbidden_endpoint_terms:
        assert term not in invoices_js


def test_invoices_phase1_ui_avoids_unsafe_dynamic_html_rendering() -> None:
    invoices_js = (REPO_ROOT / "core" / "ui" / "js" / "cards" / "invoices.js").read_text(encoding="utf-8")

    assert ".innerHTML" not in invoices_js
    for forbidden in ("dangerouslySetInnerHTML", "insertAdjacentHTML"):
        assert forbidden not in invoices_js


def test_jobs_phase2_ui_preserves_backend_quantity_authority() -> None:
    jobs_js = (REPO_ROOT / "core" / "ui" / "js" / "cards" / "jobs.js").read_text(encoding="utf-8")

    assert "payload.quantity_decimal = quantity" in jobs_js
    assert "const uom = normalizeJobUom(data.get('uom'));" in jobs_js
    assert "payload.uom = uom;" in jobs_js
    assert "name: 'quantity_decimal'" in jobs_js
    assert "name: 'uom'" in jobs_js
    for forbidden in (
        "qty_base",
        "normalize_quantity",
        "normalizeQuantity",
        "toMetricBase",
        "DIM_DEFAULTS",
        "unitMultiplier",
        "base_int",
    ):
        assert forbidden not in jobs_js


def test_home_jobs_pressure_board_is_read_only() -> None:
    home_js = (REPO_ROOT / "core" / "ui" / "js" / "cards" / "home.js").read_text(encoding="utf-8")

    assert "function renderJobsPressureBoard" in home_js
    assert "data-role=\"home-jobs-pressure\"" in home_js
    assert "data-role=\"home-jobs-pressure-slot\"" in home_js
    assert "apiGetJson('/app/jobs')" in home_js
    assert "apiGetJson(`/app/jobs/${job.id}`).catch(() => null)" in home_js
    assert "href=\"#/jobs\"" in home_js
    for write_api in ("apiPost", "apiPatch", "apiPut", "apiDelete"):
        assert write_api not in home_js
    for forbidden_endpoint in (
        "/app/stock",
        "/app/finance",
        "/app/manufacturing",
        "/app/purchase",
        "/app/payments",
        "/app/reserve",
        "/app/deliver",
    ):
        assert forbidden_endpoint not in home_js


def test_home_release_polish_keeps_operator_hierarchy_and_links() -> None:
    home_js = (REPO_ROOT / "core" / "ui" / "js" / "cards" / "home.js").read_text(encoding="utf-8")
    app_js = (REPO_ROOT / "core" / "ui" / "app.js").read_text(encoding="utf-8")

    render_markup = home_js.split("root.innerHTML = `", 1)[1]
    assert render_markup.index('data-role="home-alerts"') < render_markup.index('data-role="home-bench"')
    assert render_markup.index('data-role="home-bench"') < render_markup.index('data-role="home-jobs-pressure-slot"')
    assert render_markup.index('data-role="home-jobs-pressure-slot"') < render_markup.index('data-role="home-side-panel"')

    render_bench = home_js.split("function renderBench", 1)[1].split("function buildNotices", 1)[0]
    assert "renderJobsPressureBoard" not in render_bench

    for expected_copy in (
        "Shop Bench",
        "Start your shop setup",
        "Next useful step",
        "What needs attention",
        "No overdue jobs, no blocked jobs, no backup warnings.",
        "Jobs Pressure",
        "Overdue / due soon",
        "No active job pressure.",
        "System Trust",
        "Latest Update",
        "What changed:",
        "Why it matters:",
        "Support Development",
        "Help & Community",
        "Support BUS Core",
        "https://buscore.ca/support",
        "Read full changelog",
        "Bug Report",
        "Discord",
    ):
        assert expected_copy in home_js

    assert "local-owner-missing" not in home_js
    assert "Set local owner" not in home_js
    assert "canonicalHash === '#/home'" in app_js


def test_home_local_storage_is_display_only() -> None:
    home_js = (REPO_ROOT / "core" / "ui" / "js" / "cards" / "home.js").read_text(encoding="utf-8")

    assert "bus.home.dismissedNotices" in home_js
    assert "bus.home.versionNoticeState" in home_js
    sensitive_terms = ("password", "recovery", "session", "token", "permission", "auth")
    for line in home_js.splitlines():
        if "localStorage" in line or "sessionStorage" in line:
            lowered = line.lower()
            assert not any(term in lowered for term in sensitive_terms), line
