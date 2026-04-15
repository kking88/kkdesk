#!/usr/bin/env python3
"""Apply deterministic RustDesk customizations from typed workflow inputs."""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path


ROOT = Path.cwd()


def replace_literal(path: str, old: str, new: str, *, required: bool = False) -> int:
    file_path = ROOT / path
    if not file_path.exists():
        if required:
            raise RuntimeError(f"required file not found: {path}")
        return 0

    content = file_path.read_text(encoding="utf-8")
    count = content.count(old)
    if count == 0:
        if required:
            raise RuntimeError(f"required pattern not found in {path}: {old}")
        return 0
    if old == new:
        return 0

    updated = content.replace(old, new)
    file_path.write_text(updated, encoding="utf-8")
    return count


def ensure_literal(path: str, snippet: str) -> None:
    file_path = ROOT / path
    if not file_path.exists():
        raise RuntimeError(f"required file not found: {path}")
    content = file_path.read_text(encoding="utf-8")
    if snippet not in content:
        raise RuntimeError(f"required snippet not found in {path}: {snippet}")


def replace_glob_literal(pattern: str, old: str, new: str) -> int:
    total = 0
    for file_path in ROOT.glob(pattern):
        if not file_path.is_file():
            continue
        content = file_path.read_text(encoding="utf-8")
        count = content.count(old)
        if count == 0 or old == new:
            continue
        file_path.write_text(content.replace(old, new), encoding="utf-8")
        total += count
    return total


def check_single_line(name: str, value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{name} is required")
    if "\n" in cleaned or "\r" in cleaned:
        raise ValueError(f"{name} cannot contain newline")
    return cleaned


def check_optional_single_line(name: str, value: str) -> str:
    if value is None:
        return ""
    if "\n" in value or "\r" in value:
        raise ValueError(f"{name} cannot contain newline")
    return value


def check_optional_uint(name: str, value: str, min_value: int, max_value: int) -> str:
    cleaned = check_optional_single_line(name, value).strip()
    if not cleaned:
        return ""
    if not cleaned.isdigit():
        raise ValueError(f"{name} must be an integer")
    number = int(cleaned)
    if number < min_value or number > max_value:
        raise ValueError(f"{name} must be between {min_value} and {max_value}")
    return str(number)


def parse_build_targets(value: str) -> str:
    allowed = {"all", "windows", "linux", "android", "macos", "ios"}
    ordered = ["windows", "linux", "android", "macos", "ios"]
    cleaned = check_single_line("build_targets", value).lower().replace(" ", "")
    parts = [token for token in cleaned.split(",") if token]
    if not parts:
        return "all"
    for token in parts:
        if token not in allowed:
            raise ValueError(f"build_targets has invalid token: {token}")
    if "all" in parts:
        return "all"
    deduped = []
    for token in ordered:
        if token in parts and token not in deduped:
            deduped.append(token)
    return ",".join(deduped) if deduped else "all"


def yn(value: bool) -> str:
    return "Y" if value else "N"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-name", required=True)
    parser.add_argument("--exe-name", required=True)
    parser.add_argument("--company-name", required=True)
    parser.add_argument("--rendezvous-server", required=True)
    parser.add_argument("--pub-key", required=True)
    parser.add_argument("--api-server", required=True)
    parser.add_argument("--website-url", required=True)
    parser.add_argument("--download-url", required=True)
    parser.add_argument("--privacy-url", required=True)
    parser.add_argument("--pricing-url", required=True)
    parser.add_argument("--docs-home-url", required=True)
    parser.add_argument("--docs-x11-url", required=True)
    parser.add_argument("--docs-permissions-url", required=True)
    parser.add_argument("--docs-login-screen-url", required=True)
    parser.add_argument("--docs-mac-permission-url", required=True)
    parser.add_argument("--relay-setup-tutorial-url", required=True)
    parser.add_argument("--bundle-id", required=True)
    parser.add_argument("--support-email", required=True)
    parser.add_argument("--slogan-en", required=True)
    parser.add_argument("--slogan-cn", required=True)
    parser.add_argument("--update-check-api-url", required=True)
    parser.add_argument("--auto-update-enabled", required=True, choices=["true", "false"])

    parser.add_argument("--settings-scope", required=True, choices=["default", "override"])
    parser.add_argument("--connection-direction", required=True, choices=["both", "incoming", "outgoing"])
    parser.add_argument("--disable-installation", required=True, choices=["true", "false"])
    parser.add_argument("--disable-settings", required=True, choices=["true", "false"])
    parser.add_argument("--permanent-password", required=False, default="")

    parser.add_argument("--access-mode", required=True, choices=["custom", "full", "view"])
    parser.add_argument("--approve-mode", required=True, choices=["password", "click", "password-click"])
    parser.add_argument(
        "--verification-method",
        required=True,
        choices=["use-temporary-password", "use-permanent-password", "use-both-passwords"],
    )
    parser.add_argument("--allow-numeric-one-time-password", required=True, choices=["true", "false"])
    parser.add_argument("--temporary-password-length", required=True, choices=["6", "8", "10"])

    parser.add_argument("--enable-lan-discovery", required=True, choices=["true", "false"])
    parser.add_argument("--direct-server", required=True, choices=["true", "false"])
    parser.add_argument("--direct-access-port", required=False, default="")
    parser.add_argument("--whitelist", required=False, default="")
    parser.add_argument("--allow-auto-disconnect", required=True, choices=["true", "false"])
    parser.add_argument("--auto-disconnect-timeout", required=False, default="")
    parser.add_argument("--allow-only-conn-window-open", required=True, choices=["true", "false"])
    parser.add_argument("--allow-hide-cm", required=True, choices=["true", "false"])
    parser.add_argument("--allow-auto-record-incoming", required=True, choices=["true", "false"])
    parser.add_argument("--allow-auto-record-outgoing", required=True, choices=["true", "false"])
    parser.add_argument("--enable-abr", required=True, choices=["true", "false"])
    parser.add_argument("--enable-hwcodec", required=True, choices=["true", "false"])
    parser.add_argument("--allow-always-software-render", required=True, choices=["true", "false"])
    parser.add_argument("--allow-linux-headless", required=True, choices=["true", "false"])
    parser.add_argument("--enable-udp-punch", required=True, choices=["true", "false"])
    parser.add_argument("--enable-ipv6-punch", required=True, choices=["true", "false"])
    parser.add_argument("--enable-directx-capture", required=True, choices=["true", "false"])
    parser.add_argument("--enable-trusted-devices", required=True, choices=["true", "false"])
    parser.add_argument("--keep-awake-during-incoming-sessions", required=True, choices=["true", "false"])
    parser.add_argument("--keep-awake-during-outgoing-sessions", required=True, choices=["true", "false"])
    parser.add_argument("--allow-ask-for-note", required=True, choices=["true", "false"])
    parser.add_argument("--allow-websocket", required=True, choices=["true", "false"])
    parser.add_argument("--disable-udp", required=True, choices=["true", "false"])
    parser.add_argument("--allow-insecure-tls-fallback", required=True, choices=["true", "false"])
    parser.add_argument("--fix-third-party-api-latency", required=True, choices=["true", "false"])
    parser.add_argument("--third-party-api-timeout-secs", required=False, default="")
    parser.add_argument("--allow-remove-wallpaper", required=True, choices=["true", "false"])

    parser.add_argument("--enable-keyboard", required=True, choices=["true", "false"])
    parser.add_argument("--enable-clipboard", required=True, choices=["true", "false"])
    parser.add_argument("--enable-file-transfer", required=True, choices=["true", "false"])
    parser.add_argument("--enable-audio", required=True, choices=["true", "false"])
    parser.add_argument("--enable-tunnel", required=True, choices=["true", "false"])
    parser.add_argument("--enable-remote-restart", required=True, choices=["true", "false"])
    parser.add_argument("--enable-record-session", required=True, choices=["true", "false"])
    parser.add_argument("--enable-block-input", required=True, choices=["true", "false"])
    parser.add_argument("--allow-remote-config-modification", required=True, choices=["true", "false"])
    parser.add_argument("--enable-remote-printer", required=True, choices=["true", "false"])
    parser.add_argument("--enable-camera", required=True, choices=["true", "false"])
    parser.add_argument("--enable-terminal", required=True, choices=["true", "false"])

    parser.add_argument("--disable-change-permanent-password", required=True, choices=["true", "false"])
    parser.add_argument("--disable-change-id", required=True, choices=["true", "false"])
    parser.add_argument("--disable-unlock-pin", required=True, choices=["true", "false"])
    parser.add_argument("--custom-rendezvous-server", required=False, default="")
    parser.add_argument("--custom-server-key", required=False, default="")
    parser.add_argument("--relay-server", required=False, default="")
    parser.add_argument("--ice-servers", required=False, default="")
    parser.add_argument("--proxy-url", required=False, default="")
    parser.add_argument("--proxy-username", required=False, default="")
    parser.add_argument("--proxy-password", required=False, default="")
    parser.add_argument("--preset-address-book-name", required=False, default="")
    parser.add_argument("--preset-address-book-tag", required=False, default="")
    parser.add_argument("--preset-address-book-alias", required=False, default="")
    parser.add_argument("--preset-address-book-password", required=False, default="")
    parser.add_argument("--preset-address-book-note", required=False, default="")
    parser.add_argument("--preset-device-username", required=False, default="")
    parser.add_argument("--preset-device-name", required=False, default="")
    parser.add_argument("--preset-note", required=False, default="")
    parser.add_argument(
        "--enable-android-software-encoding-half-scale",
        required=True,
        choices=["true", "false"],
    )
    parser.add_argument("--disable-android-scam-warning", required=True, choices=["true", "false"])
    parser.add_argument("--hide-security-settings", required=True, choices=["true", "false"])
    parser.add_argument("--hide-network-settings", required=True, choices=["true", "false"])
    parser.add_argument("--hide-server-settings", required=True, choices=["true", "false"])
    parser.add_argument("--hide-proxy-settings", required=True, choices=["true", "false"])
    parser.add_argument("--hide-remote-printer-settings", required=True, choices=["true", "false"])
    parser.add_argument("--hide-websocket-settings", required=True, choices=["true", "false"])
    parser.add_argument("--hide-username-on-card", required=True, choices=["true", "false"])
    parser.add_argument("--hide-help-cards", required=True, choices=["true", "false"])
    parser.add_argument("--hide-tray", required=True, choices=["true", "false"])
    parser.add_argument("--remove-preset-password-warning", required=True, choices=["true", "false"])
    parser.add_argument("--default-connect-password", required=False, default="")
    parser.add_argument("--one-way-clipboard-redirection", required=True, choices=["true", "false"])
    parser.add_argument("--one-way-file-transfer", required=True, choices=["true", "false"])
    parser.add_argument("--allow-logon-screen-password", required=True, choices=["true", "false"])
    parser.add_argument("--allow-https-21114", required=True, choices=["true", "false"])
    parser.add_argument("--allow-hostname-as-id", required=True, choices=["true", "false"])
    parser.add_argument("--register-device", required=True, choices=["true", "false"])
    parser.add_argument("--main-window-always-on-top", required=True, choices=["true", "false"])
    parser.add_argument("--file-transfer-max-files", required=False, default="")
    parser.add_argument("--display-name", required=False, default="")
    parser.add_argument("--preset-device-group-name", required=False, default="")
    parser.add_argument("--preset-username", required=False, default="")
    parser.add_argument("--preset-strategy-name", required=False, default="")
    parser.add_argument("--avatar", required=False, default="")
    parser.add_argument("--hide-powered-by", required=True, choices=["true", "false"])
    parser.add_argument(
        "--ui-preset",
        required=True,
        choices=["standard", "mini-host-id-password", "controller-desktop-only"],
    )
    parser.add_argument(
        "--build-targets",
        required=True,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    app_name = check_single_line("app_name", args.app_name)
    exe_name_raw = check_single_line("exe_name", args.exe_name)
    company_name = check_single_line("company_name", args.company_name)
    rendezvous_server = check_single_line("rendezvous_server", args.rendezvous_server)
    pub_key = check_single_line("pub_key", args.pub_key)
    api_server = check_single_line("api_server", args.api_server)
    website_url = check_single_line("website_url", args.website_url)
    download_url = check_single_line("download_url", args.download_url)
    privacy_url = check_single_line("privacy_url", args.privacy_url)
    pricing_url = check_single_line("pricing_url", args.pricing_url)
    docs_home_url = check_single_line("docs_home_url", args.docs_home_url)
    docs_x11_url = check_single_line("docs_x11_url", args.docs_x11_url)
    docs_permissions_url = check_single_line("docs_permissions_url", args.docs_permissions_url)
    docs_login_screen_url = check_single_line("docs_login_screen_url", args.docs_login_screen_url)
    docs_mac_permission_url = check_single_line(
        "docs_mac_permission_url", args.docs_mac_permission_url
    )
    relay_setup_tutorial_url = check_single_line(
        "relay_setup_tutorial_url", args.relay_setup_tutorial_url
    )
    bundle_id = check_single_line("bundle_id", args.bundle_id)
    support_email = check_single_line("support_email", args.support_email)
    slogan_en = check_single_line("slogan_en", args.slogan_en)
    slogan_cn = check_single_line("slogan_cn", args.slogan_cn)
    update_check_api_url = check_single_line("update_check_api_url", args.update_check_api_url)

    auto_update_enabled = args.auto_update_enabled == "true"

    settings_scope = args.settings_scope
    connection_direction = args.connection_direction
    disable_installation = args.disable_installation == "true"
    disable_settings = args.disable_settings == "true"
    permanent_password = check_optional_single_line("permanent_password", args.permanent_password)

    access_mode = args.access_mode
    approve_mode = args.approve_mode
    verification_method = args.verification_method
    allow_numeric_one_time_password = args.allow_numeric_one_time_password == "true"
    temporary_password_length = args.temporary_password_length

    enable_lan_discovery = args.enable_lan_discovery == "true"
    direct_server = args.direct_server == "true"
    direct_access_port = check_optional_uint("direct_access_port", args.direct_access_port, 1, 65535)
    whitelist = check_optional_single_line("whitelist", args.whitelist).strip()
    allow_auto_disconnect = args.allow_auto_disconnect == "true"
    auto_disconnect_timeout = check_optional_uint(
        "auto_disconnect_timeout", args.auto_disconnect_timeout, 0, 65535
    )
    allow_only_conn_window_open = args.allow_only_conn_window_open == "true"
    allow_hide_cm = args.allow_hide_cm == "true"
    allow_auto_record_incoming = args.allow_auto_record_incoming == "true"
    allow_auto_record_outgoing = args.allow_auto_record_outgoing == "true"
    enable_abr = args.enable_abr == "true"
    enable_hwcodec = args.enable_hwcodec == "true"
    allow_always_software_render = args.allow_always_software_render == "true"
    allow_linux_headless = args.allow_linux_headless == "true"
    enable_udp_punch = args.enable_udp_punch == "true"
    enable_ipv6_punch = args.enable_ipv6_punch == "true"
    enable_directx_capture = args.enable_directx_capture == "true"
    enable_trusted_devices = args.enable_trusted_devices == "true"
    keep_awake_during_incoming_sessions = args.keep_awake_during_incoming_sessions == "true"
    keep_awake_during_outgoing_sessions = args.keep_awake_during_outgoing_sessions == "true"
    allow_ask_for_note = args.allow_ask_for_note == "true"
    allow_websocket = args.allow_websocket == "true"
    disable_udp = args.disable_udp == "true"
    allow_insecure_tls_fallback = args.allow_insecure_tls_fallback == "true"
    fix_third_party_api_latency = args.fix_third_party_api_latency == "true"
    third_party_api_timeout_secs_raw = check_optional_uint(
        "third_party_api_timeout_secs", args.third_party_api_timeout_secs, 2, 60
    )
    third_party_api_timeout_secs = (
        int(third_party_api_timeout_secs_raw) if third_party_api_timeout_secs_raw else 6
    )
    third_party_api_probe_timeout_secs = max(2, third_party_api_timeout_secs - 2)
    allow_remove_wallpaper = args.allow_remove_wallpaper == "true"

    enable_keyboard = args.enable_keyboard == "true"
    enable_clipboard = args.enable_clipboard == "true"
    enable_file_transfer = args.enable_file_transfer == "true"
    enable_audio = args.enable_audio == "true"
    enable_tunnel = args.enable_tunnel == "true"
    enable_remote_restart = args.enable_remote_restart == "true"
    enable_record_session = args.enable_record_session == "true"
    enable_block_input = args.enable_block_input == "true"
    allow_remote_config_modification = args.allow_remote_config_modification == "true"
    enable_remote_printer = args.enable_remote_printer == "true"
    enable_camera = args.enable_camera == "true"
    enable_terminal = args.enable_terminal == "true"

    disable_change_permanent_password = args.disable_change_permanent_password == "true"
    disable_change_id = args.disable_change_id == "true"
    disable_unlock_pin = args.disable_unlock_pin == "true"
    custom_rendezvous_server = check_optional_single_line(
        "custom_rendezvous_server", args.custom_rendezvous_server
    ).strip()
    custom_server_key = check_optional_single_line("custom_server_key", args.custom_server_key).strip()
    relay_server = check_optional_single_line("relay_server", args.relay_server).strip()
    ice_servers = check_optional_single_line("ice_servers", args.ice_servers).strip()
    proxy_url = check_optional_single_line("proxy_url", args.proxy_url).strip()
    proxy_username = check_optional_single_line("proxy_username", args.proxy_username).strip()
    proxy_password = check_optional_single_line("proxy_password", args.proxy_password).strip()
    preset_address_book_name = check_optional_single_line(
        "preset_address_book_name", args.preset_address_book_name
    ).strip()
    preset_address_book_tag = check_optional_single_line(
        "preset_address_book_tag", args.preset_address_book_tag
    ).strip()
    preset_address_book_alias = check_optional_single_line(
        "preset_address_book_alias", args.preset_address_book_alias
    ).strip()
    preset_address_book_password = check_optional_single_line(
        "preset_address_book_password", args.preset_address_book_password
    ).strip()
    preset_address_book_note = check_optional_single_line(
        "preset_address_book_note", args.preset_address_book_note
    ).strip()
    preset_device_username = check_optional_single_line(
        "preset_device_username", args.preset_device_username
    ).strip()
    preset_device_name = check_optional_single_line(
        "preset_device_name", args.preset_device_name
    ).strip()
    preset_note = check_optional_single_line("preset_note", args.preset_note).strip()
    enable_android_software_encoding_half_scale = (
        args.enable_android_software_encoding_half_scale == "true"
    )
    disable_android_scam_warning = args.disable_android_scam_warning == "true"
    hide_security_settings = args.hide_security_settings == "true"
    hide_network_settings = args.hide_network_settings == "true"
    hide_server_settings = args.hide_server_settings == "true"
    hide_proxy_settings = args.hide_proxy_settings == "true"
    hide_remote_printer_settings = args.hide_remote_printer_settings == "true"
    hide_websocket_settings = args.hide_websocket_settings == "true"
    hide_username_on_card = args.hide_username_on_card == "true"
    hide_help_cards = args.hide_help_cards == "true"
    hide_tray = args.hide_tray == "true"
    remove_preset_password_warning = args.remove_preset_password_warning == "true"
    default_connect_password = check_optional_single_line(
        "default_connect_password", args.default_connect_password
    ).strip()
    one_way_clipboard_redirection = args.one_way_clipboard_redirection == "true"
    one_way_file_transfer = args.one_way_file_transfer == "true"
    allow_logon_screen_password = args.allow_logon_screen_password == "true"
    allow_https_21114 = args.allow_https_21114 == "true"
    allow_hostname_as_id = args.allow_hostname_as_id == "true"
    register_device = args.register_device == "true"
    main_window_always_on_top = args.main_window_always_on_top == "true"
    file_transfer_max_files = check_optional_uint(
        "file_transfer_max_files", args.file_transfer_max_files, 0, 100000
    )
    display_name = check_optional_single_line("display_name", args.display_name).strip()
    preset_device_group_name = check_optional_single_line(
        "preset_device_group_name", args.preset_device_group_name
    ).strip()
    preset_username = check_optional_single_line("preset_username", args.preset_username).strip()
    preset_strategy_name = check_optional_single_line(
        "preset_strategy_name", args.preset_strategy_name
    ).strip()
    avatar = check_optional_single_line("avatar", args.avatar).strip()
    hide_powered_by = args.hide_powered_by == "true"
    ui_preset = args.ui_preset
    build_targets = parse_build_targets(args.build_targets)

    exe_name = exe_name_raw if exe_name_raw.lower().endswith(".exe") else f"{exe_name_raw}.exe"
    exe_stem = exe_name[:-4] if exe_name.lower().endswith(".exe") else exe_name
    portable_app_prefix = exe_stem.lower()
    service_exe_stem = f"{exe_stem}_service"
    mac_app_bundle = f"{app_name}.app"
    app_description = f"{app_name} Remote Desktop"

    effective_custom_rendezvous_server = custom_rendezvous_server or rendezvous_server
    effective_custom_server_key = custom_server_key or pub_key

    factory_settings = {
        "access-mode": access_mode,
        "approve-mode": approve_mode,
        "verification-method": verification_method,
        "allow-numeric-one-time-password": yn(allow_numeric_one_time_password),
        "temporary-password-length": temporary_password_length,
        "enable-keyboard": yn(enable_keyboard),
        "enable-clipboard": yn(enable_clipboard),
        "enable-file-transfer": yn(enable_file_transfer),
        "enable-audio": yn(enable_audio),
        "enable-tunnel": yn(enable_tunnel),
        "enable-remote-restart": yn(enable_remote_restart),
        "enable-record-session": yn(enable_record_session),
        "enable-block-input": yn(enable_block_input),
        "allow-remote-config-modification": yn(allow_remote_config_modification),
        "enable-remote-printer": yn(enable_remote_printer),
        "enable-camera": yn(enable_camera),
        "enable-terminal": yn(enable_terminal),
        "enable-lan-discovery": yn(enable_lan_discovery),
        "direct-server": yn(direct_server),
        "allow-only-conn-window-open": yn(allow_only_conn_window_open),
        "allow-hide-cm": yn(allow_hide_cm),
        "allow-auto-disconnect": yn(allow_auto_disconnect),
        "allow-auto-record-incoming": yn(allow_auto_record_incoming),
        "allow-auto-record-outgoing": yn(allow_auto_record_outgoing),
        "enable-abr": yn(enable_abr),
        "enable-hwcodec": yn(enable_hwcodec),
        "allow-always-software-render": yn(allow_always_software_render),
        "allow-linux-headless": yn(allow_linux_headless),
        "enable-udp-punch": yn(enable_udp_punch),
        "enable-ipv6-punch": yn(enable_ipv6_punch),
        "enable-directx-capture": yn(enable_directx_capture),
        "enable-trusted-devices": yn(enable_trusted_devices),
        "keep-awake-during-incoming-sessions": yn(keep_awake_during_incoming_sessions),
        "keep-awake-during-outgoing-sessions": yn(keep_awake_during_outgoing_sessions),
        "allow-ask-for-note": yn(allow_ask_for_note),
        "allow-websocket": yn(allow_websocket),
        "disable-udp": yn(disable_udp),
        "allow-insecure-tls-fallback": yn(allow_insecure_tls_fallback),
        "enable-android-software-encoding-half-scale": yn(
            enable_android_software_encoding_half_scale
        ),
        "show-scam-warning": "N" if disable_android_scam_warning else "Y",
        "allow-remove-wallpaper": yn(allow_remove_wallpaper),
        "allow-auto-update": yn(auto_update_enabled),
        "api-server": api_server,
        "custom-rendezvous-server": effective_custom_rendezvous_server,
        "key": effective_custom_server_key,
    }
    if relay_server:
        factory_settings["relay-server"] = relay_server
    if ice_servers:
        factory_settings["ice-servers"] = ice_servers
    if proxy_url:
        factory_settings["proxy-url"] = proxy_url
    if proxy_username:
        factory_settings["proxy-username"] = proxy_username
    if proxy_password:
        factory_settings["proxy-password"] = proxy_password
    if preset_address_book_name:
        factory_settings["preset-address-book-name"] = preset_address_book_name
    if preset_address_book_tag:
        factory_settings["preset-address-book-tag"] = preset_address_book_tag
    if preset_address_book_alias:
        factory_settings["preset-address-book-alias"] = preset_address_book_alias
    if preset_address_book_password:
        factory_settings["preset-address-book-password"] = preset_address_book_password
    if preset_address_book_note:
        factory_settings["preset-address-book-note"] = preset_address_book_note
    if preset_device_username:
        factory_settings["preset-device-username"] = preset_device_username
    if preset_device_name:
        factory_settings["preset-device-name"] = preset_device_name
    if preset_note:
        factory_settings["preset-note"] = preset_note
    if direct_access_port:
        factory_settings["direct-access-port"] = direct_access_port
    if whitelist:
        factory_settings["whitelist"] = whitelist
    if auto_disconnect_timeout:
        factory_settings["auto-disconnect-timeout"] = auto_disconnect_timeout

    factory_hard = {
        "conn-type": connection_direction,
        "disable-installation": yn(disable_installation),
        "disable-settings": yn(disable_settings),
    }
    if permanent_password:
        factory_hard["password"] = permanent_password

    factory_builtin = {
        "hide-powered-by-me": yn(hide_powered_by),
        "disable-change-permanent-password": yn(disable_change_permanent_password),
        "disable-change-id": yn(disable_change_id),
        "disable-unlock-pin": yn(disable_unlock_pin),
        "hide-security-settings": yn(hide_security_settings),
        "hide-network-settings": yn(hide_network_settings),
        "hide-server-settings": yn(hide_server_settings),
        "hide-proxy-settings": yn(hide_proxy_settings),
        "hide-remote-printer-settings": yn(hide_remote_printer_settings),
        "hide-websocket-settings": yn(hide_websocket_settings),
        "hide-username-on-card": yn(hide_username_on_card),
        "hide-help-cards": yn(hide_help_cards),
        "hide-tray": yn(hide_tray),
        "remove-preset-password-warning": yn(remove_preset_password_warning),
        "one-way-clipboard-redirection": yn(one_way_clipboard_redirection),
        "one-way-file-transfer": yn(one_way_file_transfer),
        "allow-logon-screen-password": yn(allow_logon_screen_password),
        "allow-https-21114": yn(allow_https_21114),
        "allow-hostname-as-id": yn(allow_hostname_as_id),
        "register-device": yn(register_device),
        "main-window-always-on-top": yn(main_window_always_on_top),
        "custom-ui-mode": ui_preset,
    }
    if default_connect_password:
        factory_builtin["default-connect-password"] = default_connect_password
    if file_transfer_max_files:
        factory_builtin["file-transfer-max-files"] = file_transfer_max_files
    if display_name:
        factory_builtin["display-name"] = display_name
    if preset_device_group_name:
        factory_builtin["preset-device-group-name"] = preset_device_group_name
    if preset_username:
        factory_builtin["preset-user-name"] = preset_username
    if preset_strategy_name:
        factory_builtin["preset-strategy-name"] = preset_strategy_name
    if avatar:
        factory_builtin["avatar"] = avatar

    settings_json = json.dumps(factory_settings, ensure_ascii=False)
    hard_json = json.dumps(factory_hard, ensure_ascii=False)
    builtin_json = json.dumps(factory_builtin, ensure_ascii=False)
    # Desktop rdgen-compatible custom payload:
    # keep one canonical custom config blob loaded on startup, so runtime behavior
    # stays consistent across platforms and packaging layouts.
    custom_settings = dict(factory_settings)
    custom_settings.update(factory_builtin)
    custom_settings["api-server"] = api_server
    custom_settings["custom-rendezvous-server"] = effective_custom_rendezvous_server
    custom_settings["key"] = effective_custom_server_key
    custom_payload = {"app-name": app_name}
    custom_payload.update(factory_hard)
    if custom_payload.get("conn-type") == "both":
        custom_payload.pop("conn-type", None)
    if custom_payload.get("password", "") == "":
        custom_payload.pop("password", None)
    scope_bucket = "override-settings" if settings_scope == "override" else "default-settings"
    custom_payload[scope_bucket] = custom_settings
    custom_b64 = base64.b64encode(
        json.dumps(custom_payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")

    replacements = [
        (
            "libs/hbb_common/src/config.rs",
            "pub const LINK_HEADLESS_LINUX_SUPPORT: &str =\n    \"https://github.com/rustdesk/rustdesk/wiki/Headless-Linux-Support\";\n\nlazy_static::lazy_static! {\n    pub static ref HELPER_URL: HashMap<&'static str, &'static str> = HashMap::from([\n",
            "pub const LINK_HEADLESS_LINUX_SUPPORT: &str =\n    \"https://github.com/rustdesk/rustdesk/wiki/Headless-Linux-Support\";\n\nfn parse_factory_map(raw: &str) -> HashMap<String, String> {\n    serde_json::from_str(raw).unwrap_or_default()\n}\n\nfn factory_settings_scope() -> &'static str {\n    \"__FACTORY_SETTINGS_SCOPE__\"\n}\n\nfn factory_default_settings() -> HashMap<String, String> {\n    if factory_settings_scope() == \"default\" {\n        parse_factory_map(r#\"__FACTORY_SETTINGS_JSON__\"#)\n    } else {\n        HashMap::new()\n    }\n}\n\nfn factory_overwrite_settings() -> HashMap<String, String> {\n    if factory_settings_scope() == \"override\" {\n        parse_factory_map(r#\"__FACTORY_SETTINGS_JSON__\"#)\n    } else {\n        HashMap::new()\n    }\n}\n\nfn factory_default_display_settings() -> HashMap<String, String> {\n    if factory_settings_scope() == \"default\" {\n        parse_factory_map(r#\"__FACTORY_SETTINGS_JSON__\"#)\n    } else {\n        HashMap::new()\n    }\n}\n\nfn factory_overwrite_display_settings() -> HashMap<String, String> {\n    if factory_settings_scope() == \"override\" {\n        parse_factory_map(r#\"__FACTORY_SETTINGS_JSON__\"#)\n    } else {\n        HashMap::new()\n    }\n}\n\nfn factory_default_local_settings() -> HashMap<String, String> {\n    if factory_settings_scope() == \"default\" {\n        parse_factory_map(r#\"__FACTORY_SETTINGS_JSON__\"#)\n    } else {\n        HashMap::new()\n    }\n}\n\nfn factory_overwrite_local_settings() -> HashMap<String, String> {\n    if factory_settings_scope() == \"override\" {\n        parse_factory_map(r#\"__FACTORY_SETTINGS_JSON__\"#)\n    } else {\n        HashMap::new()\n    }\n}\n\nfn factory_hard_settings() -> HashMap<String, String> {\n    let mut map = parse_factory_map(r#\"__FACTORY_HARD_JSON__\"#);\n    if map.get(\"password\").map(|v| v.is_empty()).unwrap_or(false) {\n        map.remove(\"password\");\n    }\n    if map.get(\"conn-type\").map(|v| v == \"both\").unwrap_or(false) {\n        map.remove(\"conn-type\");\n    }\n    map\n}\n\nfn factory_builtin_settings() -> HashMap<String, String> {\n    parse_factory_map(r#\"__FACTORY_BUILTIN_JSON__\"#)\n}\n\nlazy_static::lazy_static! {\n    pub static ref HELPER_URL: HashMap<&'static str, &'static str> = HashMap::from([\n",
            True,
        ),
        (
            "libs/hbb_common/src/config.rs",
            "pub static ref DEFAULT_SETTINGS: RwLock<HashMap<String, String>> = Default::default();",
            "pub static ref DEFAULT_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new(factory_default_settings());",
            True,
        ),
        (
            "libs/hbb_common/src/config.rs",
            "pub static ref OVERWRITE_SETTINGS: RwLock<HashMap<String, String>> = Default::default();",
            "pub static ref OVERWRITE_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new(factory_overwrite_settings());",
            True,
        ),
        (
            "libs/hbb_common/src/config.rs",
            "pub static ref DEFAULT_DISPLAY_SETTINGS: RwLock<HashMap<String, String>> = Default::default();",
            "pub static ref DEFAULT_DISPLAY_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new(factory_default_display_settings());",
            True,
        ),
        (
            "libs/hbb_common/src/config.rs",
            "pub static ref OVERWRITE_DISPLAY_SETTINGS: RwLock<HashMap<String, String>> = Default::default();",
            "pub static ref OVERWRITE_DISPLAY_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new(factory_overwrite_display_settings());",
            True,
        ),
        (
            "libs/hbb_common/src/config.rs",
            "pub static ref DEFAULT_LOCAL_SETTINGS: RwLock<HashMap<String, String>> = Default::default();",
            "pub static ref DEFAULT_LOCAL_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new(factory_default_local_settings());",
            True,
        ),
        (
            "libs/hbb_common/src/config.rs",
            "pub static ref OVERWRITE_LOCAL_SETTINGS: RwLock<HashMap<String, String>> = Default::default();",
            "pub static ref OVERWRITE_LOCAL_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new(factory_overwrite_local_settings());",
            True,
        ),
        (
            "libs/hbb_common/src/config.rs",
            "pub static ref HARD_SETTINGS: RwLock<HashMap<String, String>> = Default::default();",
            "pub static ref HARD_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new(factory_hard_settings());",
            True,
        ),
        (
            "libs/hbb_common/src/config.rs",
            "pub static ref BUILTIN_SETTINGS: RwLock<HashMap<String, String>> = Default::default();",
            "pub static ref BUILTIN_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new(factory_builtin_settings());",
            True,
        ),
        (
            "libs/hbb_common/src/config.rs",
            'pub static ref APP_NAME: RwLock<String> = RwLock::new("RustDesk".to_owned());',
            f'pub static ref APP_NAME: RwLock<String> = RwLock::new("{app_name}".to_owned());',
            True,
        ),
        (
            "libs/hbb_common/src/config.rs",
            "__FACTORY_SETTINGS_SCOPE__",
            settings_scope,
            True,
        ),
        (
            "libs/hbb_common/src/config.rs",
            "__FACTORY_SETTINGS_JSON__",
            settings_json,
            True,
        ),
        (
            "libs/hbb_common/src/config.rs",
            "__FACTORY_HARD_JSON__",
            hard_json,
            True,
        ),
        (
            "libs/hbb_common/src/config.rs",
            "__FACTORY_BUILTIN_JSON__",
            builtin_json,
            True,
        ),
        (
            "libs/hbb_common/src/config.rs",
            'pub const RENDEZVOUS_SERVERS: &[&str] = &["rs-ny.rustdesk.com"];',
            f'pub const RENDEZVOUS_SERVERS: &[&str] = &["{rendezvous_server}"];',
            True,
        ),
        (
            "libs/hbb_common/src/config.rs",
            'pub const RS_PUB_KEY: &str = "OeVuKk5nlHiXp+APNn0Y3pC1Iwpwn44JGqrQCsWqmBw=";',
            f'pub const RS_PUB_KEY: &str = "{pub_key}";',
            True,
        ),
        (
            "src/common.rs",
            "pub fn load_custom_client() {\n",
            "const FACTORY_CUSTOM_CLIENT_B64: &str = \"__FACTORY_CUSTOM_CLIENT_B64__\";\n\npub fn load_custom_client() {\n    if !FACTORY_CUSTOM_CLIENT_B64.is_empty() {\n        read_custom_client(FACTORY_CUSTOM_CLIENT_B64);\n        return;\n    }\n",
            True,
        ),
        (
            "src/common.rs",
            """    const KEY: &str = "5Qbwsde3unUcJBtrx9ZkvUmwFNoExHzpryHuPUdqlWM=";
    let Some(pk) = get_rs_pk(KEY) else {
        log::error!("Failed to parse public key of custom client");
        return;
    };
    let Ok(data) = sign::verify(&data, &pk) else {
        log::error!("Failed to dec custom client config");
        return;
    };
""",
            """    // Factory mode: accept unsigned base64 custom payload (desktop rdgen compatibility).
""",
            True,
        ),
        (
            "src/common.rs",
            "__FACTORY_CUSTOM_CLIENT_B64__",
            custom_b64,
            True,
        ),
        (
            "src/common.rs",
            '"https://admin.rustdesk.com".to_owned()',
            f'"{api_server}".to_owned()',
            True,
        ),
        (
            "Cargo.toml",
            'authors = ["rustdesk <info@rustdesk.com>"]',
            f'authors = ["rustdesk <{support_email}>"]',
            True,
        ),
        (
            "libs/hbb_common/src/lib.rs",
            '    const URL: &str = "https://api.rustdesk.com/version/latest";',
            f'    const URL: &str = "{update_check_api_url}";',
            True,
        ),
        (
            "Cargo.toml",
            'description = "RustDesk Remote Desktop"',
            f'description = "{app_description}"',
            True,
        ),
        ("Cargo.toml", 'ProductName = "RustDesk"', f'ProductName = "{app_name}"', True),
        (
            "Cargo.toml",
            'FileDescription = "RustDesk Remote Desktop"',
            f'FileDescription = "{app_description}"',
            True,
        ),
        ("Cargo.toml", 'OriginalFilename = "rustdesk.exe"', f'OriginalFilename = "{exe_name}"', True),
        ("Cargo.toml", 'name = "RustDesk"', f'name = "{app_name}"', False),
        ("Cargo.toml", 'name = "service"', f'name = "{service_exe_stem}"', False),
        ("Cargo.toml", 'identifier = "com.carriez.rustdesk"', f'identifier = "{bundle_id}"', True),
        (
            "libs/portable/Cargo.toml",
            'description = "RustDesk Remote Desktop"',
            f'description = "{app_description}"',
            True,
        ),
        (
            "libs/portable/Cargo.toml",
            'ProductName = "RustDesk"',
            f'ProductName = "{app_name}"',
            True,
        ),
        (
            "libs/portable/Cargo.toml",
            'FileDescription = "RustDesk Remote Desktop"',
            f'FileDescription = "{app_description}"',
            True,
        ),
        (
            "libs/portable/Cargo.toml",
            'OriginalFilename = "rustdesk.exe"',
            f'OriginalFilename = "{exe_name}"',
            True,
        ),
        (
            "flutter/windows/runner/Runner.rc",
            'VALUE "CompanyName", "Purslane Ltd" "\\0"',
            f'VALUE "CompanyName", "{company_name}" "\\0"',
            True,
        ),
        (
            "flutter/windows/runner/Runner.rc",
            'VALUE "FileDescription", "RustDesk Remote Desktop" "\\0"',
            f'VALUE "FileDescription", "{app_description}" "\\0"',
            True,
        ),
        (
            "flutter/windows/runner/Runner.rc",
            'VALUE "InternalName", "rustdesk" "\\0"',
            f'VALUE "InternalName", "{exe_stem}" "\\0"',
            True,
        ),
        (
            "flutter/windows/runner/Runner.rc",
            'VALUE "LegalCopyright", "Copyright © 2025 Purslane Ltd. All rights reserved." "\\0"',
            f'VALUE "LegalCopyright", "Copyright © 2025 {company_name}. All rights reserved." "\\0"',
            True,
        ),
        (
            "flutter/windows/runner/Runner.rc",
            'VALUE "OriginalFilename", "rustdesk.exe" "\\0"',
            f'VALUE "OriginalFilename", "{exe_name}" "\\0"',
            True,
        ),
        (
            "flutter/windows/runner/Runner.rc",
            'VALUE "ProductName", "RustDesk" "\\0"',
            f'VALUE "ProductName", "{app_name}" "\\0"',
            True,
        ),
        (
            "flutter/windows/CMakeLists.txt",
            'set(BINARY_NAME "rustdesk")',
            f'set(BINARY_NAME "{exe_stem}")',
            False,
        ),
        (
            "flutter/linux/CMakeLists.txt",
            'set(BINARY_NAME "rustdesk")',
            f'set(BINARY_NAME "{exe_stem}")',
            False,
        ),
        (
            "flutter/linux/my_application.cc",
            'gtk_header_bar_set_title(header_bar, "rustdesk");',
            f'gtk_header_bar_set_title(header_bar, "{app_name}");',
            False,
        ),
        (
            "flutter/linux/my_application.cc",
            'gtk_window_set_title(window, "rustdesk");',
            f'gtk_window_set_title(window, "{app_name}");',
            False,
        ),
        (
            "flutter/macos/Runner/Configs/AppInfo.xcconfig",
            "PRODUCT_NAME = RustDesk",
            f"PRODUCT_NAME = {app_name}",
            False,
        ),
        (
            "res/rustdesk.desktop",
            "Name=RustDesk",
            f"Name={app_name}",
            False,
        ),
        (
            "res/rustdesk.desktop",
            "Exec=rustdesk %u",
            f"Exec={exe_stem} %u",
            False,
        ),
        (
            "res/rustdesk.desktop",
            "Icon=rustdesk",
            f"Icon={exe_stem}",
            False,
        ),
        (
            "res/rustdesk.desktop",
            "StartupWMClass=rustdesk",
            f"StartupWMClass={exe_stem}",
            False,
        ),
        (
            "res/rustdesk-link.desktop",
            "Name=RustDesk",
            f"Name={app_name}",
            False,
        ),
        (
            "res/rustdesk-link.desktop",
            "TryExec=rustdesk",
            f"TryExec={exe_stem}",
            False,
        ),
        (
            "res/rustdesk-link.desktop",
            "Exec=rustdesk %u",
            f"Exec={exe_stem} %u",
            False,
        ),
        (
            "res/rustdesk-link.desktop",
            "Icon=rustdesk",
            f"Icon={exe_stem}",
            False,
        ),
        (
            "res/rustdesk-link.desktop",
            "StartupWMClass=rustdesk",
            f"StartupWMClass={exe_stem}",
            False,
        ),
        (
            "res/rustdesk.service",
            "Description=RustDesk",
            f"Description={app_name}",
            False,
        ),
        (
            "res/rustdesk.service",
            "ExecStart=/usr/bin/rustdesk --service",
            f"ExecStart=/usr/bin/{exe_stem} --service",
            False,
        ),
        (
            "res/rustdesk.service",
            'ExecStop=pkill -f "rustdesk --"',
            f'ExecStop=pkill -f "{exe_stem} --"',
            False,
        ),
        (
            "res/rustdesk.service",
            "PIDFile=/run/rustdesk.pid",
            f"PIDFile=/run/{exe_stem}.pid",
            False,
        ),
        (
            "res/DEBIAN/postinst",
            "ln -f -s /usr/share/rustdesk/rustdesk /usr/bin/rustdesk",
            f"ln -f -s /usr/share/rustdesk/{exe_stem} /usr/bin/{exe_stem}\n\tln -f -s /usr/share/rustdesk/{exe_stem} /usr/bin/rustdesk",
            False,
        ),
        (
            "res/DEBIAN/prerm",
            "rm -f /usr/bin/rustdesk",
            f"rm -f /usr/bin/{exe_stem} /usr/bin/rustdesk",
            False,
        ),
        (
            "res/rpm-flutter.spec",
            "ln -sf /usr/share/rustdesk/rustdesk /usr/bin/rustdesk",
            f"ln -sf /usr/share/rustdesk/{exe_stem} /usr/bin/{exe_stem}\nln -sf /usr/share/rustdesk/{exe_stem} /usr/bin/rustdesk",
            False,
        ),
        (
            "res/rpm-flutter.spec",
            "    rm /usr/bin/rustdesk || true",
            f"    rm /usr/bin/{exe_stem} /usr/bin/rustdesk || true",
            False,
        ),
        (
            "res/rpm-flutter-suse.spec",
            "ln -sf /usr/share/rustdesk/rustdesk /usr/bin/rustdesk",
            f"ln -sf /usr/share/rustdesk/{exe_stem} /usr/bin/{exe_stem}\nln -sf /usr/share/rustdesk/{exe_stem} /usr/bin/rustdesk",
            False,
        ),
        (
            "res/rpm-flutter-suse.spec",
            "    rm /usr/bin/rustdesk || true",
            f"    rm /usr/bin/{exe_stem} /usr/bin/rustdesk || true",
            False,
        ),
        (
            "appimage/AppImageBuilder-x86_64.yml",
            "exec: usr/share/rustdesk/rustdesk",
            f"exec: usr/share/rustdesk/{exe_stem}",
            False,
        ),
        (
            "appimage/AppImageBuilder-aarch64.yml",
            "exec: usr/share/rustdesk/rustdesk",
            f"exec: usr/share/rustdesk/{exe_stem}",
            False,
        ),
        (
            "src/privacy_mode/win_topmost_window.rs",
            'pub const WIN_TOPMOST_INJECTED_PROCESS_EXE: &\'static str = "RuntimeBroker_rustdesk.exe";',
            f'pub const WIN_TOPMOST_INJECTED_PROCESS_EXE: &\'static str = "RuntimeBroker_{exe_stem}.exe";',
            False,
        ),
        (
            "libs/portable/src/main.rs",
            'const APP_PREFIX: &str = "rustdesk";',
            f'const APP_PREFIX: &str = "{portable_app_prefix}";',
            False,
        ),
        (
            "libs/portable/src/main.rs",
            'pub const WIN_TOPMOST_INJECTED_PROCESS_EXE: &\'static str = "RuntimeBroker_rustdesk.exe";',
            f'pub const WIN_TOPMOST_INJECTED_PROCESS_EXE: &\'static str = "RuntimeBroker_{exe_stem}.exe";',
            False,
        ),
        (
            "libs/portable/src/main.rs",
            '.args(&["/F", "/IM", "RuntimeBroker_rustdesk.exe"])',
            f'.args(&["/F", "/IM", "RuntimeBroker_{exe_stem}.exe"])',
            False,
        ),
        (
            "res/msi/Package/Components/RustDesk.wxs",
            'Value="RuntimeBroker_rustdesk.exe"',
            f'Value="RuntimeBroker_{exe_stem}.exe"',
            False,
        ),
        (
            "res/msi/Package/Language/Package.en-us.wxl",
            '<String Id="Service_DisplayName" Value="RustDesk Service" />',
            f'<String Id="Service_DisplayName" Value="{app_name} Service" />',
            False,
        ),
        (
            "res/msi/Package/Language/Package.en-us.wxl",
            '<String Id="Service_Description" Value="This service runs the RustDesk Server." />',
            f'<String Id="Service_Description" Value="This service runs the {app_name} Server." />',
            False,
        ),
        (
            "build.py",
            f'python3 ./generate.py -f ../../{{flutter_build_dir_2}} -o . -e ../../{{flutter_build_dir_2}}/rustdesk.exe',
            f'python3 ./generate.py -f ../../{{flutter_build_dir_2}} -o . -e ../../{{flutter_build_dir_2}}/{exe_name}',
            False,
        ),
        (
            "build.py",
            "hbb_name = 'rustdesk' + ('.exe' if windows else '')",
            f"hbb_name = '{exe_stem}' + ('.exe' if windows else '')",
            False,
        ),
        (
            "src/server/portable_service.rs",
            'let dst = dir.join("rustdesk.exe");',
            f'let dst = dir.join("{exe_name}");',
            False,
        ),
        (
            "build.py",
            "cp -rf ../target/release/service ./build/macos/Build/Products/Release/RustDesk.app/Contents/MacOS/",
            f'cp -rf ../target/release/{service_exe_stem} "$(ls -d ./build/macos/Build/Products/Release/*.app | head -n 1)/Contents/MacOS/"',
            False,
        ),
        (
            "src/platform/privileges_scripts/daemon.plist",
            "/Applications/RustDesk.app/Contents/MacOS/service",
            f"/Applications/{mac_app_bundle}/Contents/MacOS/{service_exe_stem}",
            False,
        ),
        (
            "src/platform/privileges_scripts/daemon.plist",
            "/Applications/RustDesk.app/Contents/MacOS/",
            f"/Applications/{mac_app_bundle}/Contents/MacOS/",
            False,
        ),
        (
            "src/platform/privileges_scripts/daemon.plist",
            "/tmp/rustdesk_service.err",
            f"/tmp/{exe_stem}_service.err",
            False,
        ),
        (
            "src/platform/privileges_scripts/daemon.plist",
            "/tmp/rustdesk_service.out",
            f"/tmp/{exe_stem}_service.out",
            False,
        ),
        ("Cargo.toml", "Purslane Ltd", company_name, False),
        ("libs/portable/Cargo.toml", "Purslane Ltd", company_name, False),
        ("src/main.rs", "Purslane Ltd", company_name, False),
        ("res/msi/Package/License.rtf", "Purslane Ltd", company_name, False),
        ("flutter/lib/desktop/pages/desktop_setting_page.dart", "Purslane Ltd", company_name, False),
        ("src/ui/index.tis", "Purslane Ltd", company_name, False),
        ("Cargo.toml", "info@rustdesk.com", support_email, False),
        ("src/main.rs", "info@rustdesk.com", support_email, False),
        ("build.py", "Homepage: https://rustdesk.com", f"Homepage: {website_url}", False),
        (
            "flutter/lib/common.dart",
            "launchUrl(Uri.parse('https://rustdesk.com'));",
            f"launchUrl(Uri.parse('{website_url}'));",
            False,
        ),
        (
            "flutter/lib/desktop/pages/desktop_setting_page.dart",
            "launchUrlString('https://rustdesk.com/privacy.html');",
            f"launchUrlString('{privacy_url}');",
            False,
        ),
        (
            "flutter/lib/desktop/pages/desktop_setting_page.dart",
            "launchUrlString('https://rustdesk.com');",
            f"launchUrlString('{website_url}');",
            False,
        ),
        (
            "flutter/lib/mobile/pages/settings_page.dart",
            "const url = 'https://rustdesk.com/';",
            f"const url = '{website_url}';",
            False,
        ),
        (
            "flutter/lib/mobile/pages/settings_page.dart",
            "launchUrlString('https://rustdesk.com/privacy.html'),",
            f"launchUrlString('{privacy_url}'),",
            False,
        ),
        (
            "flutter/lib/desktop/pages/install_page.dart",
            "'https://rustdesk.com/privacy.html'",
            f"'{privacy_url}'",
            False,
        ),
        ("src/ui/index.tis", '"https://rustdesk.com/privacy.html"', f'"{privacy_url}"', False),
        ("src/ui/index.tis", '"https://rustdesk.com/download"', f'"{download_url}"', False),
        ("src/ui/index.tis", '"https://rustdesk.com"', f'"{website_url}"', False),
        (
            "flutter/lib/desktop/pages/desktop_home_page.dart",
            "Uri.parse('https://rustdesk.com/download')",
            f"Uri.parse('{download_url}')",
            False,
        ),
        (
            "flutter/lib/mobile/pages/connection_page.dart",
            "final url = 'https://rustdesk.com/download';",
            f"final url = '{download_url}';",
            False,
        ),
        (
            "flutter/lib/desktop/pages/connection_page.dart",
            'const url = "https://rustdesk.com/pricing";',
            f'const url = "{pricing_url}";',
            False,
        ),
        (
            "flutter/lib/desktop/pages/desktop_setting_page.dart",
            """            // if (usePassword)
            //   hide_cm(!locked).marginOnly(left: _kContentHSubMargin - 6),""",
            """            if (usePassword)
              hide_cm(!locked).marginOnly(left: _kContentHSubMargin - 6),""",
            False,
        ),
        (
            "flutter/lib/main.dart",
            "  gFFI.serverModel.hideCm = hide;",
            "  // gFFI.serverModel.hideCm = hide;",
            False,
        ),
        (
            "flutter/lib/models/server_model.dart",
            "  bool hideCm = false;",
            "  bool _hideCm = false;",
            False,
        ),
        (
            "flutter/lib/models/server_model.dart",
            "  bool get clipboardOk => _clipboardOk;\n\n  bool get showElevation => _showElevation;",
            "  bool get clipboardOk => _clipboardOk;\n\n  bool get hideCm => _hideCm;\n\n  bool get showElevation => _showElevation;",
            False,
        ),
        (
            "flutter/lib/models/server_model.dart",
            """  setVerificationMethod(String method) async {
    await bind.mainSetOption(key: kOptionVerificationMethod, value: method);
    /*
    if (method != kUsePermanentPassword) {
      await bind.mainSetOption(
          key: 'allow-hide-cm', value: bool2option('allow-hide-cm', false));
    }
    */
  }""",
            """  setVerificationMethod(String method) async {
    await bind.mainSetOption(key: kOptionVerificationMethod, value: method);
    if (method == kUseTemporaryPassword) {
      await bind.mainSetOption(
          key: 'allow-hide-cm', value: bool2option('allow-hide-cm', false));
    }
  }""",
            False,
        ),
        (
            "flutter/lib/models/server_model.dart",
            """  setApproveMode(String mode) async {
    await bind.mainSetOption(key: kOptionApproveMode, value: mode);
    /*
    if (mode != 'password') {
      await bind.mainSetOption(
          key: 'allow-hide-cm', value: bool2option('allow-hide-cm', false));
    }
    */
  }""",
            """  setApproveMode(String mode) async {
    await bind.mainSetOption(key: kOptionApproveMode, value: mode);
    if (mode != 'password') {
      await bind.mainSetOption(
          key: 'allow-hide-cm', value: bool2option('allow-hide-cm', false));
    }
  }""",
            False,
        ),
        (
            "flutter/lib/models/server_model.dart",
            """    /*
    // initital _hideCm at startup
    final verificationMethod =
        bind.mainGetOptionSync(key: kOptionVerificationMethod);
    final approveMode = bind.mainGetOptionSync(key: kOptionApproveMode);
    _hideCm = option2bool(
        'allow-hide-cm', bind.mainGetOptionSync(key: 'allow-hide-cm'));
    if (!(approveMode == 'password' &&
        verificationMethod == kUsePermanentPassword)) {
      _hideCm = false;
    }
    */
""",
            """    // initital _hideCm at startup
    final verificationMethod =
        bind.mainGetOptionSync(key: kOptionVerificationMethod);
    final approveMode = bind.mainGetOptionSync(key: kOptionApproveMode);
    _hideCm = option2bool(
        'allow-hide-cm', bind.mainGetOptionSync(key: 'allow-hide-cm'));
    if (!(approveMode == 'password' &&
        verificationMethod != kUseTemporaryPassword)) {
      _hideCm = false;
    }
""",
            False,
        ),
        (
            "flutter/lib/models/server_model.dart",
            """    /*
    var hideCm = option2bool(
        'allow-hide-cm', await bind.mainGetOption(key: 'allow-hide-cm'));
    if (!(approveMode == 'password' &&
        verificationMethod == kUsePermanentPassword)) {
      hideCm = false;
    }
    */""",
            """    var hideCm = option2bool(
        'allow-hide-cm', await bind.mainGetOption(key: 'allow-hide-cm'));
    if (!(approveMode == 'password' &&
        verificationMethod != kUseTemporaryPassword)) {
      hideCm = false;
    }""",
            False,
        ),
        (
            "libs/hbb_common/src/password_security.rs",
            "        && verification_method() == VerificationMethod::OnlyUsePermanentPassword",
            "        && verification_method() != VerificationMethod::OnlyUseTemporaryPassword",
            False,
        ),
        (
            "flutter/lib/models/server_model.dart",
            """    /*
    if (_hideCm != hideCm) {
      _hideCm = hideCm;
      if (desktopType == DesktopType.cm) {
        if (hideCm) {
          await hideCmWindow();
        } else {
          await showCmWindow();
        }
      }
      update = true;
    }
    */""",
            """    if (_hideCm != hideCm) {
      _hideCm = hideCm;
      if (desktopType == DesktopType.cm) {
        if (hideCm) {
          await hideCmWindow();
        } else {
          await showCmWindow();
        }
      }
      update = true;
    }""",
            False,
        ),
        (
            "flutter/lib/desktop/pages/desktop_home_page.dart",
            """  final GlobalKey _childKey = GlobalKey();

  @override
""",
            """  final GlobalKey _childKey = GlobalKey();

  bool get _isMiniHostIdPasswordUi =>
      bind.mainGetBuildinOption(key: "custom-ui-mode") == "mini-host-id-password";

  @override
""",
            False,
        ),
        (
            "flutter/lib/desktop/pages/desktop_home_page.dart",
            """    final children = <Widget>[
      if (!isOutgoingOnly) buildPresetPasswordWarning(),
      if (bind.isCustomClient())
        Align(
          alignment: Alignment.center,
          child: loadPowered(context),
        ),
      Align(
        alignment: Alignment.center,
        child: loadLogo(),
      ),
      buildTip(context),
      if (!isOutgoingOnly) buildIDBoard(context),
      if (!isOutgoingOnly) buildPasswordBoard(context),
      FutureBuilder<Widget>(
        future: Future.value(
            Obx(() => buildHelpCards(stateGlobal.updateUrl.value))),
        builder: (_, data) {
          if (data.hasData) {
            if (isIncomingOnly) {
              if (isInHomePage()) {
                Future.delayed(Duration(milliseconds: 300), () {
                  _updateWindowSize();
                });
              }
            }
            return data.data!;
          } else {
            return const Offstage();
          }
        },
      ),
      buildPluginEntry(),
    ];
""",
            """    final children = _isMiniHostIdPasswordUi
        ? <Widget>[
            if (!isOutgoingOnly) buildIDBoard(context),
            if (!isOutgoingOnly) buildPasswordBoard(context),
          ]
        : <Widget>[
            if (!isOutgoingOnly) buildPresetPasswordWarning(),
            if (bind.isCustomClient())
              Align(
                alignment: Alignment.center,
                child: loadPowered(context),
              ),
            Align(
              alignment: Alignment.center,
              child: loadLogo(),
            ),
            buildTip(context),
            if (!isOutgoingOnly) buildIDBoard(context),
            if (!isOutgoingOnly) buildPasswordBoard(context),
            FutureBuilder<Widget>(
              future: Future.value(
                  Obx(() => buildHelpCards(stateGlobal.updateUrl.value))),
              builder: (_, data) {
                if (data.hasData) {
                  if (isIncomingOnly) {
                    if (isInHomePage()) {
                      Future.delayed(Duration(milliseconds: 300), () {
                        _updateWindowSize();
                      });
                    }
                  }
                  return data.data!;
                } else {
                  return const Offstage();
                }
              },
            ),
            buildPluginEntry(),
          ];
""",
            False,
        ),
        (
            "flutter/lib/desktop/pages/desktop_home_page.dart",
            """    if (isIncomingOnly) {
      children.addAll([
""",
            """    if (isIncomingOnly && !_isMiniHostIdPasswordUi) {
      children.addAll([
""",
            False,
        ),
        (
            "flutter/lib/desktop/pages/desktop_home_page.dart",
            """                        buildPopupMenu(context)
""",
            """                        if (!_isMiniHostIdPasswordUi && !bind.isDisableSettings())
                          buildPopupMenu(context)
""",
            False,
        ),
        (
            "flutter/lib/desktop/pages/connection_page.dart",
            """  final _menuOpen = false.obs;

  @override
""",
            """  final _menuOpen = false.obs;

  bool get _isControllerDesktopOnlyUi =>
      bind.mainGetBuildinOption(key: "custom-ui-mode") == "controller-desktop-only";

  @override
""",
            False,
        ),
        (
            "flutter/lib/desktop/pages/connection_page.dart",
            """            SizedBox(height: 12),
            Divider().paddingOnly(right: 12),
            Expanded(child: PeerTabPage()),
""",
            """            if (!_isControllerDesktopOnlyUi) ...[
              SizedBox(height: 12),
              Divider().paddingOnly(right: 12),
              Expanded(child: PeerTabPage()),
            ],
""",
            False,
        ),
        (
            "flutter/lib/desktop/pages/connection_page.dart",
            """                const SizedBox(width: 8),
                Container(
                  height: 28.0,
                  width: 28.0,
                  decoration: BoxDecoration(
                    border: Border.all(color: Theme.of(context).dividerColor),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Center(
                    child: StatefulBuilder(
                      builder: (context, setState) {
                        var offset = Offset(0, 0);
                        return Obx(() => InkWell(
                              child: _menuOpen.value
                                  ? Transform.rotate(
                                      angle: pi,
                                      child: Icon(IconFont.more, size: 14),
                                    )
                                  : Icon(IconFont.more, size: 14),
                              onTapDown: (e) {
                                offset = e.globalPosition;
                              },
                              onTap: () async {
                                _menuOpen.value = true;
                                final x = offset.dx;
                                final y = offset.dy;
                                await mod_menu
                                    .showMenu(
                                  context: context,
                                  position: RelativeRect.fromLTRB(x, y, x, y),
                                  items: [
                                    (
                                      'Transfer file',
                                      () => onConnect(isFileTransfer: true)
                                    ),
                                    (
                                      'View camera',
                                      () => onConnect(isViewCamera: true)
                                    ),
                                    (
                                      '${translate('Terminal')} (beta)',
                                      () => onConnect(isTerminal: true)
                                    ),
                                  ]
                                      .map((e) => MenuEntryButton<String>(
                                            childBuilder: (TextStyle? style) =>
                                                Text(
                                              translate(e.$1),
                                              style: style,
                                            ),
                                            proc: () => e.$2(),
                                            padding: EdgeInsets.symmetric(
                                                horizontal:
                                                    kDesktopMenuPadding.left),
                                            dismissOnClicked: true,
                                          ))
                                      .map((e) => e.build(
                                          context,
                                          const MenuConfig(
                                              commonColor: CustomPopupMenuTheme
                                                  .commonColor,
                                              height:
                                                  CustomPopupMenuTheme.height,
                                              dividerHeight:
                                                  CustomPopupMenuTheme
                                                      .dividerHeight)))
                                      .expand((i) => i)
                                      .toList(),
                                  elevation: 8,
                                )
                                    .then((_) {
                                  _menuOpen.value = false;
                                });
                              },
                            ));
                      },
                    ),
                  ),
                ),
""",
            """                if (!_isControllerDesktopOnlyUi) ...[
                  const SizedBox(width: 8),
                  Container(
                    height: 28.0,
                    width: 28.0,
                    decoration: BoxDecoration(
                      border: Border.all(color: Theme.of(context).dividerColor),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Center(
                      child: StatefulBuilder(
                        builder: (context, setState) {
                          var offset = Offset(0, 0);
                          return Obx(() => InkWell(
                                child: _menuOpen.value
                                    ? Transform.rotate(
                                        angle: pi,
                                        child: Icon(IconFont.more, size: 14),
                                      )
                                    : Icon(IconFont.more, size: 14),
                                onTapDown: (e) {
                                  offset = e.globalPosition;
                                },
                                onTap: () async {
                                  _menuOpen.value = true;
                                  final x = offset.dx;
                                  final y = offset.dy;
                                  await mod_menu
                                      .showMenu(
                                    context: context,
                                    position: RelativeRect.fromLTRB(x, y, x, y),
                                    items: [
                                      (
                                        'Transfer file',
                                        () => onConnect(isFileTransfer: true)
                                      ),
                                      (
                                        'View camera',
                                        () => onConnect(isViewCamera: true)
                                      ),
                                      (
                                        '${translate('Terminal')} (beta)',
                                        () => onConnect(isTerminal: true)
                                      ),
                                    ]
                                        .map((e) => MenuEntryButton<String>(
                                              childBuilder: (TextStyle? style) =>
                                                  Text(
                                                translate(e.$1),
                                                style: style,
                                              ),
                                              proc: () => e.$2(),
                                              padding: EdgeInsets.symmetric(
                                                  horizontal:
                                                      kDesktopMenuPadding.left),
                                              dismissOnClicked: true,
                                            ))
                                        .map((e) => e.build(
                                            context,
                                            const MenuConfig(
                                                commonColor: CustomPopupMenuTheme
                                                    .commonColor,
                                                height:
                                                    CustomPopupMenuTheme.height,
                                                dividerHeight:
                                                    CustomPopupMenuTheme
                                                        .dividerHeight)))
                                        .expand((i) => i)
                                        .toList(),
                                    elevation: 8,
                                  )
                                      .then((_) {
                                    _menuOpen.value = false;
                                  });
                                },
                              ));
                        },
                      ),
                    ),
                  ),
                ],
""",
            False,
        ),
        (
            "libs/hbb_common/src/config.rs",
            'pub const LINK_DOCS_HOME: &str = "https://rustdesk.com/docs/en/";',
            f'pub const LINK_DOCS_HOME: &str = "{docs_home_url}";',
            False,
        ),
        (
            "libs/hbb_common/src/config.rs",
            'pub const LINK_DOCS_X11_REQUIRED: &str = "https://rustdesk.com/docs/en/manual/linux/#x11-required";',
            f'pub const LINK_DOCS_X11_REQUIRED: &str = "{docs_x11_url}";',
            False,
        ),
        (
            "src/client.rs",
            'pub const SCRAP_X11_REF_URL: &str = "https://rustdesk.com/docs/en/manual/linux/#x11-required";',
            f'pub const SCRAP_X11_REF_URL: &str = "{docs_x11_url}";',
            False,
        ),
        (
            "src/client.rs",
            'link: "https://rustdesk.com/docs/en/manual/linux/#login-screen",',
            f'link: "{docs_login_screen_url}",',
            False,
        ),
        (
            "flutter/lib/desktop/pages/desktop_home_page.dart",
            "'https://rustdesk.com/docs/en/client/linux/#permissions-issue'",
            f"'{docs_permissions_url}'",
            False,
        ),
        (
            "flutter/lib/desktop/pages/desktop_home_page.dart",
            "'https://rustdesk.com/docs/en/client/linux/#x11-required'",
            f"'{docs_x11_url}'",
            False,
        ),
        (
            "flutter/lib/desktop/pages/desktop_home_page.dart",
            "'https://rustdesk.com/docs/en/client/linux/#login-screen'",
            f"'{docs_login_screen_url}'",
            False,
        ),
        (
            "src/lang/en.rs",
            '("doc_mac_permission", "https://rustdesk.com/docs/en/client/mac/#enable-permissions"),',
            f'("doc_mac_permission", "{docs_mac_permission_url}"),',
            False,
        ),
        (
            "src/lang/en.rs",
            '("doc_fix_wayland", "https://rustdesk.com/docs/en/client/linux/#x11-required"),',
            f'("doc_fix_wayland", "{docs_x11_url}"),',
            False,
        ),
        (
            "src/ui/index.tis",
            '"https://rustdesk.com/blog/id-relay-set/"',
            f'"{relay_setup_tutorial_url}"',
            False,
        ),
        (
            "src/lang/en.rs",
            '("Slogan_tip", "Made with heart in this chaotic world!"),',
            f'("Slogan_tip", "{slogan_en}"),',
            False,
        ),
        (
            "src/lang/cn.rs",
            '("Slogan_tip", "在这个混乱的世界中，用心制作！"),',
            f'("Slogan_tip", "{slogan_cn}"),',
            False,
        ),
        ("src/platform/privileges_scripts/daemon.plist", "com.carriez.rustdesk", bundle_id, False),
        ("src/platform/privileges_scripts/agent.plist", "com.carriez.rustdesk", bundle_id, False),
        ("src/platform/macos.rs", "com.carriez.rustdesk", bundle_id, False),
        ("flutter/macos/Runner/Info.plist", "com.carriez.rustdesk", bundle_id, False),
        ("flutter/ios/Runner/Info.plist", "com.carriez.rustdesk", bundle_id, False),
        ("flutter/macos/Runner.xcodeproj/project.pbxproj", "com.carriez.rustdesk", bundle_id, False),
        (
            ".github/workflows/flutter-build.yml",
            '      upload-tag:\n        type: string\n        default: "nightly"',
            f'      upload-tag:\n        type: string\n        default: "nightly"\n      build-targets:\n        type: string\n        default: "{build_targets}"',
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            '  TAG_NAME: "${{ inputs.upload-tag }}"',
            '  TAG_NAME: "${{ inputs.upload-tag }}"\n  FACTORY_BUILD_TARGETS: ",${{ inputs.build-targets }},"',
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "  build-RustDeskTempTopMostWindow:\n    uses: ./.github/workflows/third-party-RustDeskTempTopMostWindow.yml",
            "  build-RustDeskTempTopMostWindow:\n    if: ${{ contains(env.FACTORY_BUILD_TARGETS, ',all,') || contains(env.FACTORY_BUILD_TARGETS, ',windows,') }}\n    uses: ./.github/workflows/third-party-RustDeskTempTopMostWindow.yml",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "  build-for-windows-flutter:\n    name: ${{ matrix.job.target }}",
            "  build-for-windows-flutter:\n    if: ${{ contains(env.FACTORY_BUILD_TARGETS, ',all,') || contains(env.FACTORY_BUILD_TARGETS, ',windows,') }}\n    name: ${{ matrix.job.target }}",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "  build-for-windows-sciter:\n    name: ${{ matrix.job.target }} (${{ matrix.job.os }})",
            "  build-for-windows-sciter:\n    if: ${{ contains(env.FACTORY_BUILD_TARGETS, ',all,') || contains(env.FACTORY_BUILD_TARGETS, ',windows,') }}\n    name: ${{ matrix.job.target }} (${{ matrix.job.os }})",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "  build-rustdesk-ios:\n    if: ${{ inputs.upload-artifact }}\n    name: build rustdesk ios ipa",
            "  build-rustdesk-ios:\n    if: ${{ inputs.upload-artifact && (contains(env.FACTORY_BUILD_TARGETS, ',all,') || contains(env.FACTORY_BUILD_TARGETS, ',ios,')) }}\n    name: build rustdesk ios ipa",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "  build-for-macOS:\n    name: ${{ matrix.job.target }}",
            "  build-for-macOS:\n    if: ${{ contains(env.FACTORY_BUILD_TARGETS, ',all,') || contains(env.FACTORY_BUILD_TARGETS, ',macos,') }}\n    name: ${{ matrix.job.target }}",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "  publish_unsigned:\n    needs:\n      - build-for-macOS\n      - build-for-windows-flutter\n      - build-for-windows-sciter\n    runs-on: ubuntu-latest\n    if: ${{ inputs.upload-artifact }}",
            "  publish_unsigned:\n    needs:\n      - build-for-macOS\n      - build-for-windows-flutter\n      - build-for-windows-sciter\n    runs-on: ubuntu-latest\n    if: ${{ inputs.upload-artifact && (contains(env.FACTORY_BUILD_TARGETS, ',all,') || (contains(env.FACTORY_BUILD_TARGETS, ',windows,') && contains(env.FACTORY_BUILD_TARGETS, ',macos,'))) }}",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "  build-rustdesk-android:\n    needs: [generate-bridge]\n    name: build rustdesk android apk ${{ matrix.job.target }}",
            "  build-rustdesk-android:\n    if: ${{ contains(env.FACTORY_BUILD_TARGETS, ',all,') || contains(env.FACTORY_BUILD_TARGETS, ',android,') }}\n    needs: [generate-bridge]\n    name: build rustdesk android apk ${{ matrix.job.target }}",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "  build-rustdesk-android-universal:\n    needs: [build-rustdesk-android]\n    name: build rustdesk android universal apk\n    if: ${{ inputs.upload-artifact }}",
            "  build-rustdesk-android-universal:\n    needs: [build-rustdesk-android]\n    name: build rustdesk android universal apk\n    if: ${{ inputs.upload-artifact && (contains(env.FACTORY_BUILD_TARGETS, ',all,') || contains(env.FACTORY_BUILD_TARGETS, ',android,')) }}",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "  build-rustdesk-linux:\n    needs: [generate-bridge]\n    name: build rustdesk linux ${{ matrix.job.target }}",
            "  build-rustdesk-linux:\n    if: ${{ contains(env.FACTORY_BUILD_TARGETS, ',all,') || contains(env.FACTORY_BUILD_TARGETS, ',linux,') }}\n    needs: [generate-bridge]\n    name: build rustdesk linux ${{ matrix.job.target }}",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "  build-rustdesk-linux-sciter:\n    if: ${{ inputs.upload-artifact }}\n    runs-on: ${{ matrix.job.on }}",
            "  build-rustdesk-linux-sciter:\n    if: ${{ inputs.upload-artifact && (contains(env.FACTORY_BUILD_TARGETS, ',all,') || contains(env.FACTORY_BUILD_TARGETS, ',linux,')) }}\n    runs-on: ${{ matrix.job.on }}",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "  build-appimage:\n    name: Build appimage ${{ matrix.job.target }}\n    needs: [build-rustdesk-linux]\n    runs-on: ubuntu-22.04\n    if: ${{ inputs.upload-artifact }}",
            "  build-appimage:\n    name: Build appimage ${{ matrix.job.target }}\n    needs: [build-rustdesk-linux]\n    runs-on: ubuntu-22.04\n    if: ${{ inputs.upload-artifact && (contains(env.FACTORY_BUILD_TARGETS, ',all,') || contains(env.FACTORY_BUILD_TARGETS, ',linux,')) }}",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "  build-flatpak:\n    name: Build flatpak ${{ matrix.job.target }}${{ matrix.job.suffix }}\n    needs:\n      - build-rustdesk-linux\n      - build-rustdesk-linux-sciter\n    runs-on: ${{ matrix.job.on }}\n    if: ${{ inputs.upload-artifact }}",
            "  build-flatpak:\n    name: Build flatpak ${{ matrix.job.target }}${{ matrix.job.suffix }}\n    needs:\n      - build-rustdesk-linux\n      - build-rustdesk-linux-sciter\n    runs-on: ${{ matrix.job.on }}\n    if: ${{ inputs.upload-artifact && (contains(env.FACTORY_BUILD_TARGETS, ',all,') || contains(env.FACTORY_BUILD_TARGETS, ',linux,')) }}",
            False,
        ),
        (
            ".github/workflows/flutter-nightly.yml",
            "  workflow_dispatch:",
            f'  workflow_dispatch:\n    inputs:\n      build_targets:\n        description: "Build targets: all/windows/linux/android/macos/ios"\n        required: false\n        default: "{build_targets}"\n        type: string',
            False,
        ),
        (
            ".github/workflows/flutter-nightly.yml",
            '    with:\n      upload-artifact: true\n      upload-tag: "nightly"',
            f"    with:\n      upload-artifact: true\n      upload-tag: \"nightly\"\n      build-targets: ${{{{ github.event.inputs.build_targets || '{build_targets}' }}}}",
            False,
        ),
        (
            ".github/workflows/flutter-tag.yml",
            "on:\n  workflow_dispatch:",
            f'on:\n  workflow_dispatch:\n    inputs:\n      build_targets:\n        description: "Build targets: all/windows/linux/android/macos/ios"\n        required: false\n        default: "{build_targets}"\n        type: string',
            False,
        ),
        (
            ".github/workflows/flutter-tag.yml",
            "    with:\n      upload-artifact: true\n      upload-tag: ${{ github.ref_name }}",
            f"    with:\n      upload-artifact: true\n      upload-tag: ${{{{ github.ref_name }}}}\n      build-targets: ${{{{ github.event.inputs.build_targets || '{build_targets}' }}}}",
            False,
        ),
        (
            ".github/workflows/flutter-ci.yml",
            "on:\n  workflow_dispatch:",
            f'on:\n  workflow_dispatch:\n    inputs:\n      build_targets:\n        description: "Build targets: all/windows/linux/android/macos/ios"\n        required: false\n        default: "{build_targets}"\n        type: string',
            False,
        ),
        (
            ".github/workflows/flutter-ci.yml",
            "jobs:\n  run-ci:\n    uses: ./.github/workflows/flutter-build.yml\n    with:\n      upload-artifact: false",
            f"jobs:\n  run-ci:\n    uses: ./.github/workflows/flutter-build.yml\n    with:\n      upload-artifact: false\n      build-targets: ${{{{ github.event.inputs.build_targets || '{build_targets}' }}}}",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "          python preprocess.py --arp -d ../../rustdesk\n"
            "          nuget restore msi.sln\n"
            "          msbuild msi.sln -p:Configuration=Release -p:Platform=x64 /p:TargetVersion=Windows10",
            f'          python preprocess.py --arp -d ../../rustdesk --app-name "{exe_stem}" --manufacturer "{company_name}" --version "${{{{ env.VERSION }}}}"\n'
            "          nuget restore msi.sln\n"
            "          msbuild msi.sln -p:Configuration=Release -p:Platform=x64 /p:TargetVersion=Windows10",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            '          create-dmg --icon "RustDesk.app" 200 190 --hide-extension "RustDesk.app" --window-size 800 400 --app-drop-link 600 185 rustdesk-${{ env.VERSION }}-${{ matrix.job.arch }}.dmg ./flutter/build/macos/Build/Products/Release/RustDesk.app',
            f"          APP_BUNDLE=\"$(find ./flutter/build/macos/Build/Products/Release -maxdepth 1 -name '*.app' | head -n 1)\"\n"
            "          APP_BUNDLE_NAME=\"$(basename \"${APP_BUNDLE}\")\"\n"
            "          test -n \"${APP_BUNDLE}\" || { echo \"No .app bundle found\"; ls -la ./flutter/build/macos/Build/Products/Release; exit 1; }\n"
            f"          create-dmg --icon \"${{APP_BUNDLE_NAME}}\" 200 190 --hide-extension \"${{APP_BUNDLE_NAME}}\" --window-size 800 400 --app-drop-link 600 185 {exe_stem}-${{{{ env.VERSION }}}}-${{{{ matrix.job.arch }}}}.dmg \"${{APP_BUNDLE}}\"",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            '          codesign --force --options runtime -s ${{ secrets.MACOS_CODESIGN_IDENTITY }} --deep --strict ./flutter/build/macos/Build/Products/Release/RustDesk.app -vvv',
            """          APP_BUNDLE="$(find ./flutter/build/macos/Build/Products/Release -maxdepth 1 -name '*.app' | head -n 1)"
          APP_BUNDLE_NAME="$(basename "${APP_BUNDLE}")"
          test -n "${APP_BUNDLE}" || { echo "No .app bundle found"; ls -la ./flutter/build/macos/Build/Products/Release; exit 1; }
          codesign --force --options runtime -s ${{ secrets.MACOS_CODESIGN_IDENTITY }} --deep --strict "${APP_BUNDLE}" -vvv""",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            '          create-dmg --icon "RustDesk.app" 200 190 --hide-extension "RustDesk.app" --window-size 800 400 --app-drop-link 600 185 rustdesk-${{ env.VERSION }}.dmg ./flutter/build/macos/Build/Products/Release/RustDesk.app',
            f'          create-dmg --icon "${{APP_BUNDLE_NAME}}" 200 190 --hide-extension "${{APP_BUNDLE_NAME}}" --window-size 800 400 --app-drop-link 600 185 {exe_stem}-${{{{ env.VERSION }}}}.dmg "${{APP_BUNDLE}}"',
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "          python3 ./generate.py -f ../../rustdesk/ -o . -e ../../rustdesk/rustdesk.exe",
            f"          python3 ./generate.py -f ../../rustdesk/ -o . -e ../../rustdesk/{exe_name}",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "          python3 ./generate.py -f ../../Release/ -o . -e ../../Release/rustdesk.exe",
            f"          python3 ./generate.py -f ../../Release/ -o . -e ../../Release/{exe_name}",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "rustdesk-${{ env.VERSION }}",
            f"{exe_stem}-${{{{ env.VERSION }}}}",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "rustdesk-unsigned-",
            f"{exe_stem}-unsigned-",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "rustdesk*",
            f"{exe_stem}*",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "          sha256sum ../../SignOutput/rustdesk-*.msi",
            f"          sha256sum ../../SignOutput/{exe_stem}-*.msi",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "            ./SignOutput/rustdesk-*.msi\n"
            "            ./SignOutput/rustdesk-*.exe",
            f"            ./SignOutput/{exe_stem}-*.msi\n"
            f"            ./SignOutput/{exe_stem}-*.exe",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "            ./SignOutput/rustdesk-*.exe",
            f"            ./SignOutput/{exe_stem}-*.exe",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "            export DEB_ARCH=${{ matrix.job.deb_arch }}\n"
            "            python3 ./build.py --flutter --skip-cargo\n"
            f"            for name in {exe_stem}*??.deb; do\n"
            "              mv \"$name\" \"${name%%.deb}-${{ matrix.job.arch }}.deb\"\n"
            "            done\n"
            "\n"
            "            # rpm package\n"
            "            echo -e \"start packaging fedora package\"\n"
            "            pushd /workspace\n"
            "            case ${{ matrix.job.arch }} in\n"
            "              aarch64)\n"
            "                sed -i \"s/linux\\/x64/linux\\/arm64/g\" ./res/rpm-flutter.spec\n"
            "                ;;\n"
            "            esac\n"
            "            HBB=`pwd` rpmbuild ./res/rpm-flutter.spec -bb\n"
            "            pushd ~/rpmbuild/RPMS/${{ matrix.job.arch }}\n"
            f"            for name in {exe_stem}*??.rpm; do\n"
            "                mv \"$name\" /workspace/\"${name%%.rpm}.rpm\"\n"
            "            done\n"
            "\n"
            "            # rpm suse package\n"
            "            echo -e \"start packaging suse package\"\n"
            "            pushd /workspace\n"
            "            case ${{ matrix.job.arch }} in\n"
            "              aarch64)\n"
            "                sed -i \"s/linux\\/x64/linux\\/arm64/g\" ./res/rpm-flutter-suse.spec\n"
            "                ;;\n"
            "            esac\n"
            "            HBB=`pwd` rpmbuild ./res/rpm-flutter-suse.spec -bb\n"
            "            pushd ~/rpmbuild/RPMS/${{ matrix.job.arch }}\n"
            f"            for name in {exe_stem}*??.rpm; do\n"
            "                mv \"$name\" /workspace/\"${name%%.rpm}-suse.rpm\"\n"
            "            done",
            f"""            export DEB_ARCH=${{{{ matrix.job.deb_arch }}}}
            python3 ./build.py --flutter --skip-cargo
            shopt -s nullglob
            found_deb=0
            for name in {exe_stem}*.deb rustdesk*.deb; do
              mv "$name" "{exe_stem}-${{{{ env.VERSION }}}}-${{{{ matrix.job.arch }}}}.deb"
              found_deb=1
              break
            done
            if [ "${{found_deb}}" -eq 0 ]; then
              echo "No deb package found after build.py --flutter --skip-cargo"
              ls -la /workspace
              exit 1
            fi

            # rpm package
            echo -e "start packaging fedora package"
            pushd /workspace
            case ${{{{ matrix.job.arch }}}} in
              aarch64)
                sed -i "s/linux\\/x64/linux\\/arm64/g" ./res/rpm-flutter.spec
                ;;
            esac
            HBB=`pwd` rpmbuild ./res/rpm-flutter.spec -bb
            pushd ~/rpmbuild/RPMS/${{{{ matrix.job.arch }}}}
            found_rpm=0
            for name in {exe_stem}*.rpm rustdesk*.rpm; do
                mv "$name" /workspace/{exe_stem}-${{{{ env.VERSION }}}}-${{{{ matrix.job.arch }}}}.rpm
                found_rpm=1
                break
            done
            if [ "${{found_rpm}}" -eq 0 ]; then
              echo "No rpm package found after rpmbuild ./res/rpm-flutter.spec -bb"
              ls -la ~/rpmbuild/RPMS/${{{{ matrix.job.arch }}}}
              exit 1
            fi

            # rpm suse package
            echo -e "start packaging suse package"
            pushd /workspace
            case ${{{{ matrix.job.arch }}}} in
              aarch64)
                sed -i "s/linux\\/x64/linux\\/arm64/g" ./res/rpm-flutter-suse.spec
                ;;
            esac
            HBB=`pwd` rpmbuild ./res/rpm-flutter-suse.spec -bb
            pushd ~/rpmbuild/RPMS/${{{{ matrix.job.arch }}}}
            found_rpm_suse=0
            for name in {exe_stem}*.rpm rustdesk*.rpm; do
                mv "$name" /workspace/{exe_stem}-${{{{ env.VERSION }}}}-${{{{ matrix.job.arch }}}}-suse.rpm
                found_rpm_suse=1
                break
            done
            if [ "${{found_rpm_suse}}" -eq 0 ]; then
              echo "No suse rpm package found after rpmbuild ./res/rpm-flutter-suse.spec -bb"
              ls -la ~/rpmbuild/RPMS/${{{{ matrix.job.arch }}}}
              exit 1
            fi""",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "            rustdesk-*.deb\n"
            "            rustdesk-*.rpm",
            f"            {exe_stem}-${{{{ env.VERSION }}}}-${{{{ matrix.job.arch }}}}.deb\n"
            f"            {exe_stem}-${{{{ env.VERSION }}}}-${{{{ matrix.job.arch }}}}.rpm\n"
            f"            {exe_stem}-${{{{ env.VERSION }}}}-${{{{ matrix.job.arch }}}}-suse.rpm",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            f"          for name in {exe_stem}*??.deb; do\n"
            "              # use cp to duplicate deb files to fit other packages.\n"
            "              cp \"$name\" \"${name%%.deb}-${{ matrix.job.arch }}-sciter.deb\"\n"
            "          done",
            f"""          shopt -s nullglob
          found_sciter_deb=0
          for name in {exe_stem}*.deb rustdesk*.deb; do
              # use cp to duplicate deb files to fit other packages.
              cp "$name" "{exe_stem}-${{{{ env.VERSION }}}}-${{{{ matrix.job.arch }}}}-sciter.deb"
              found_sciter_deb=1
              break
          done
          if [ "${{found_sciter_deb}}" -eq 0 ]; then
            echo "No sciter deb package found in workspace"
            ls -la
            exit 1
          fi""",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            """      - name: Install LLVM and Clang
        uses: rustdesk-org/install-llvm-action-32bit@master
        with:
          version: ${{ env.LLVM_VERSION }}
""",
            """      - name: Install LLVM and Clang (attempt 1)
        id: install_llvm_1
        continue-on-error: true
        uses: rustdesk-org/install-llvm-action-32bit@master
        with:
          version: ${{ env.LLVM_VERSION }}

      - name: Install LLVM and Clang (attempt 2)
        if: steps.install_llvm_1.outcome == 'failure'
        id: install_llvm_2
        continue-on-error: true
        uses: rustdesk-org/install-llvm-action-32bit@master
        with:
          version: ${{ env.LLVM_VERSION }}

      - name: Ensure LLVM and Clang installed
        if: steps.install_llvm_1.outcome == 'failure' && steps.install_llvm_2.outcome == 'failure'
        run: |
          echo "Install LLVM and Clang failed twice."
          exit 1
""",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "            # build vcpkg helper executable with gcc-8 for arm-linux but use prebuilt one on x64-linux\n"
            "            if [ \"${{ matrix.job.vcpkg-triplet }}\" = \"arm-linux\" ]; then\n",
            """            # build vcpkg helper executable with gcc-8 for arm-linux but use prebuilt one on x64-linux
            bootstrap_vcpkg_with_retry() {
              local attempt=1
              local max_attempts=3
              while true; do
                if "$@"; then
                  return 0
                fi
                if [ "${attempt}" -ge "${max_attempts}" ]; then
                  echo "bootstrap-vcpkg failed after ${max_attempts} attempts"
                  return 1
                fi
                local wait_seconds=$((attempt * 20))
                echo "bootstrap-vcpkg failed (attempt ${attempt}/${max_attempts}), retry in ${wait_seconds}s..."
                sleep "${wait_seconds}"
                attempt=$((attempt + 1))
              done
            }
            if [ "${{ matrix.job.vcpkg-triplet }}" = "arm-linux" ]; then
""",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "              CC=/usr/bin/gcc-8 CXX=/usr/bin/g++-8 sh bootstrap-vcpkg.sh -disableMetrics",
            "              bootstrap_vcpkg_with_retry env CC=/usr/bin/gcc-8 CXX=/usr/bin/g++-8 sh bootstrap-vcpkg.sh -disableMetrics",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "              sh bootstrap-vcpkg.sh -disableMetrics",
            "              bootstrap_vcpkg_with_retry sh bootstrap-vcpkg.sh -disableMetrics",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "            wget --output-document rust.tar.gz https://static.rust-lang.org/dist/rust-${{env.RUST_TOOLCHAIN_VERSION}}-${{ matrix.job.target }}.tar.gz",
            "            wget --tries=5 --waitretry=8 --retry-connrefused --output-document rust.tar.gz https://static.rust-lang.org/dist/rust-${{env.RUST_TOOLCHAIN_VERSION}}-${{ matrix.job.target }}.tar.gz",
            False,
        ),
        (
            ".github/workflows/flutter-build.yml",
            "            wget --output-document nasm.deb \"http://ftp.us.debian.org/debian/pool/main/n/nasm/nasm_${{ env.SCITER_NASM_DEBVERSION }}_${{ matrix.job.deb_arch }}.deb\"",
            "            wget --tries=5 --waitretry=8 --retry-connrefused --output-document nasm.deb \"http://ftp.us.debian.org/debian/pool/main/n/nasm/nasm_${{ env.SCITER_NASM_DEBVERSION }}_${{ matrix.job.deb_arch }}.deb\"",
            False,
        ),
    ]

    if fix_third_party_api_latency:
        replacements.extend(
            [
                (
                    "src/common.rs",
                    "let to = std::time::Duration::from_secs(12);",
                    f"let to = std::time::Duration::from_secs({third_party_api_timeout_secs});",
                    True,
                ),
                (
                    "src/common.rs",
                    ".timeout(std::time::Duration::from_secs(12))",
                    f".timeout(std::time::Duration::from_secs({third_party_api_timeout_secs}))",
                    True,
                ),
                (
                    "src/hbbs_http/http_client.rs",
                    "if let Err(e) = client.head(url).send() {",
                    f"if let Err(e) = client.head(url).timeout(std::time::Duration::from_secs({third_party_api_probe_timeout_secs})).send() {{",
                    True,
                ),
                (
                    "src/hbbs_http/http_client.rs",
                    "if let Err(e) = client.head(url).send().await {",
                    f"if let Err(e) = client.head(url).timeout(std::time::Duration::from_secs({third_party_api_probe_timeout_secs})).send().await {{",
                    True,
                ),
            ]
        )

    replaced_total = 0
    file_stats: dict[str, int] = {}
    for path, old, new, required in replacements:
        count = replace_literal(path, old, new, required=required)
        if count > 0:
            file_stats[path] = file_stats.get(path, 0) + count
            replaced_total += count

    # Keep UI copy consistent with the custom brand name.
    if app_name != "RustDesk":
        lang_replaced = replace_glob_literal("src/lang/*.rs", "RustDesk", app_name)
        if lang_replaced > 0:
            file_stats["src/lang/*.rs"] = file_stats.get("src/lang/*.rs", 0) + lang_replaced
            replaced_total += lang_replaced

    # Validate critical runtime options are really embedded after patching.
    ensure_literal("libs/hbb_common/src/config.rs", f'RwLock::new("{app_name}".to_owned())')
    ensure_literal(
        "libs/hbb_common/src/config.rs",
        f'pub const RENDEZVOUS_SERVERS: &[&str] = &["{rendezvous_server}"];',
    )
    ensure_literal("libs/hbb_common/src/config.rs", f'pub const RS_PUB_KEY: &str = "{pub_key}";')
    ensure_literal("libs/hbb_common/src/config.rs", f'"api-server": "{api_server}"')
    ensure_literal(
        "libs/hbb_common/src/config.rs",
        f'"custom-rendezvous-server": "{effective_custom_rendezvous_server}"',
    )
    ensure_literal("libs/hbb_common/src/config.rs", f'"key": "{effective_custom_server_key}"')
    ensure_literal("libs/hbb_common/src/config.rs", f'"allow-hide-cm": "{yn(allow_hide_cm)}"')
    ensure_literal(
        "libs/hbb_common/src/password_security.rs",
        "verification_method() != VerificationMethod::OnlyUseTemporaryPassword",
    )
    ensure_literal(
        "libs/hbb_common/src/config.rs",
        f'"show-scam-warning": "{"N" if disable_android_scam_warning else "Y"}"',
    )
    ensure_literal("libs/hbb_common/src/config.rs", f'"custom-ui-mode": "{ui_preset}"')
    ensure_literal("Cargo.toml", f'name = "{service_exe_stem}"')
    ensure_literal(
        "libs/hbb_common/src/config.rs",
        "pub static ref DEFAULT_LOCAL_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new(factory_default_local_settings());",
    )
    ensure_literal(
        "libs/hbb_common/src/config.rs",
        "pub static ref OVERWRITE_LOCAL_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new(factory_overwrite_local_settings());",
    )
    ensure_literal("src/common.rs", "const FACTORY_CUSTOM_CLIENT_B64: &str = \"")
    ensure_literal("src/common.rs", "read_custom_client(FACTORY_CUSTOM_CLIENT_B64);")
    ensure_literal(
        "src/common.rs",
        "Factory mode: accept unsigned base64 custom payload (desktop rdgen compatibility).",
    )
    ensure_literal("flutter/lib/desktop/pages/desktop_setting_page.dart", "hide_cm(!locked)")
    ensure_literal(
        "src/platform/privileges_scripts/daemon.plist",
        f"/Applications/{mac_app_bundle}/Contents/MacOS/{service_exe_stem}",
    )
    ensure_literal(
        "src/platform/privileges_scripts/daemon.plist",
        f"/Applications/{mac_app_bundle}/Contents/MacOS/",
    )
    ensure_literal("libs/portable/src/main.rs", f'const APP_PREFIX: &str = "{portable_app_prefix}";')
    ensure_literal("flutter/windows/CMakeLists.txt", f'set(BINARY_NAME "{exe_stem}")')
    ensure_literal("src/privacy_mode/win_topmost_window.rs", f'RuntimeBroker_{exe_stem}.exe')
    ensure_literal("res/rustdesk.service", f"ExecStart=/usr/bin/{exe_stem} --service")
    ensure_literal("flutter/macos/Runner/Configs/AppInfo.xcconfig", f"PRODUCT_NAME = {app_name}")
    ensure_literal("appimage/AppImageBuilder-x86_64.yml", f"exec: usr/share/rustdesk/{exe_stem}")
    ensure_literal("appimage/AppImageBuilder-aarch64.yml", f"exec: usr/share/rustdesk/{exe_stem}")

    server_model = (ROOT / "flutter/lib/models/server_model.dart").read_text(encoding="utf-8")
    if "/*\n    var hideCm = option2bool(" in server_model:
        raise RuntimeError("allow-hide-cm runtime block is still commented in server_model.dart")
    if "/*\n    if (_hideCm != hideCm) {" in server_model:
        raise RuntimeError("allow-hide-cm update block is still commented in server_model.dart")

    print(json.dumps({"replacements": replaced_total, "files": file_stats}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[rustdesk-customize] {exc}", file=sys.stderr)
        raise SystemExit(1)
