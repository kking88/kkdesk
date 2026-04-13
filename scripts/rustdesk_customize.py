#!/usr/bin/env python3
"""Apply deterministic RustDesk customizations from typed workflow inputs."""

from __future__ import annotations

import argparse
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

    exe_name = exe_name_raw if exe_name_raw.lower().endswith(".exe") else f"{exe_name_raw}.exe"
    exe_stem = exe_name[:-4] if exe_name.lower().endswith(".exe") else exe_name
    app_description = f"{app_name} Remote Desktop"

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
        "allow-remove-wallpaper": yn(allow_remove_wallpaper),
        "allow-auto-update": yn(auto_update_enabled),
    }
    if custom_rendezvous_server:
        factory_settings["custom-rendezvous-server"] = custom_rendezvous_server
    if custom_server_key:
        factory_settings["key"] = custom_server_key
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

    replacements = [
        (
            "libs/hbb_common/src/config.rs",
            "pub const LINK_HEADLESS_LINUX_SUPPORT: &str =\n    \"https://github.com/rustdesk/rustdesk/wiki/Headless-Linux-Support\";\n\nlazy_static::lazy_static! {\n    pub static ref HELPER_URL: HashMap<&'static str, &'static str> = HashMap::from([\n",
            "pub const LINK_HEADLESS_LINUX_SUPPORT: &str =\n    \"https://github.com/rustdesk/rustdesk/wiki/Headless-Linux-Support\";\n\nfn parse_factory_map(raw: &str) -> HashMap<String, String> {\n    serde_json::from_str(raw).unwrap_or_default()\n}\n\nfn factory_settings_scope() -> &'static str {\n    \"__FACTORY_SETTINGS_SCOPE__\"\n}\n\nfn factory_default_settings() -> HashMap<String, String> {\n    if factory_settings_scope() == \"default\" {\n        parse_factory_map(r#\"__FACTORY_SETTINGS_JSON__\"#)\n    } else {\n        HashMap::new()\n    }\n}\n\nfn factory_overwrite_settings() -> HashMap<String, String> {\n    if factory_settings_scope() == \"override\" {\n        parse_factory_map(r#\"__FACTORY_SETTINGS_JSON__\"#)\n    } else {\n        HashMap::new()\n    }\n}\n\nfn factory_hard_settings() -> HashMap<String, String> {\n    let mut map = parse_factory_map(r#\"__FACTORY_HARD_JSON__\"#);\n    if map.get(\"password\").map(|v| v.is_empty()).unwrap_or(false) {\n        map.remove(\"password\");\n    }\n    if map.get(\"conn-type\").map(|v| v == \"both\").unwrap_or(false) {\n        map.remove(\"conn-type\");\n    }\n    map\n}\n\nfn factory_builtin_settings() -> HashMap<String, String> {\n    parse_factory_map(r#\"__FACTORY_BUILTIN_JSON__\"#)\n}\n\nlazy_static::lazy_static! {\n    pub static ref HELPER_URL: HashMap<&'static str, &'static str> = HashMap::from([\n",
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

    print(json.dumps({"replacements": replaced_total, "files": file_stats}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[rustdesk-customize] {exc}", file=sys.stderr)
        raise SystemExit(1)
