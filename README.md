# GitHub Project Factory (Vue + Vite)

这套配置用于自动化流程：

1. 克隆 Vue/Vite 模板仓库
2. 按输入参数替换占位符
3. 推送到新仓库
4. 新仓库自动执行构建（可选自动部署 GitHub Pages）
5. 支持 RustDesk 专用可视化定制（服务器、key、品牌信息等）

## 目录

- `.github/workflows/create-project.yml`: 通用模板工厂工作流
- `.github/workflows/create-rustdesk-project.yml`: RustDesk 专用工厂工作流
- `scripts/customize.sh`: 占位符替换脚本
- `scripts/rustdesk_customize.py`: RustDesk 定制脚本（按字段改写源码）
- `examples/vue-vite-template/`: Vue + Vite 模板仓库示例（含 CI/CD）

## 快速开始

1. 创建“工厂仓库”，复制本目录全部内容到该仓库。
2. 在工厂仓库添加 Actions Secret：
   - `FACTORY_TOKEN`（至少 `repo` + `workflow` 权限；组织下还需创建仓库权限）
3. 创建你的“模板仓库”，把 `examples/vue-vite-template/` 下的文件复制到模板仓库根目录。
4. 在工厂仓库 Actions 手动触发 `Create Project From Template`，填写：
   - `request_id`: 可留空（给外部系统做请求追踪）
   - `template_repo`: `owner/template-repo`
   - `template_ref`: 模板分支或标签（如 `main` / `v1.2.0`）
   - `new_repo`: 新仓库名（会用于 npm package name）
   - `project_name`: 页面展示项目名
   - `visibility`: `private` 或 `public`
   - `default_branch`: 一般 `main`
   - `custom_replacements`: 可留空；如需定制，传 JSON 数组字符串：
     - `[{"key":"__API_BASE__","value":"https://api.demo.local"}]`

## RustDesk 定制工作流

手动触发 `Create RustDesk Project`，推荐参数：

- `version`: `1.4.6`（或 `master`）
- `source_repo`: `rustdesk/rustdesk`
- `source_ref`: 留空（默认跟随 `version`）
- `new_repo`: 新仓库名
- `default_branch`: 推荐 `master`（RustDesk 上游 CI 默认监听 `master`）
- `app_name`: 客户端显示名称
- `exe_name`: Windows 文件名（不带 `.exe` 也可）
- `company_name`: 公司名
- `rendezvous_server`: 中继/ID 服务器
- `pub_key`: 服务器公钥
- `api_server`: API 地址（例如 `https://admin.example.com`）
- `website_url`: 官网地址
- `download_url`: 下载地址
- `privacy_url` / `pricing_url`: 隐私页与定价页
- `docs_home_url` / `docs_x11_url` / `docs_permissions_url` / `docs_login_screen_url` / `docs_mac_permission_url`: 文档链接组
- `relay_setup_tutorial_url`: “搭建中继/ID 服务器”引导链接
- `bundle_id`: 包标识（macOS/iOS 元数据）
- `support_email`: 支持邮箱
- `slogan_en` / `slogan_cn`: 客户端口号文案
- `update_check_api_url`: 自动更新检查接口（返回最新版本发布地址）
- `auto_update_enabled`: 默认启用后台自动更新（`true` / `false`）
- `hide_powered_by`: 是否隐藏 Powered By 区域（`true` / `false`）
- `ui_preset`: 主界面预设（`standard` / `mini-host-id-password` / `controller-desktop-only`）
  - `mini-host-id-password`: 主界面裁剪为仅显示 ID 与密码（被控端极简）
  - `controller-desktop-only`: 主界面裁剪为仅保留远程桌面连接入口（控制端极简）
  - 这两个极简预设会自动联动连接方向：被控端=`incoming`，控制端=`outgoing`
- 安全选项：
  - `settings_scope`: 写入 `default` 或 `override`
  - `connection_direction`: `both` / `incoming` / `outgoing`
  - `access_mode`: `full` / `view` / `custom`
  - `approve_mode`: `password` / `click` / `password-click`
  - `verification_method`: `use-temporary-password` / `use-permanent-password` / `use-both-passwords`
  - `permanent_password`: 可选，固定密码
- 权限设置（布尔）：
  - `enable_keyboard` / `enable_clipboard` / `enable_file_transfer` / `enable_audio`
  - `enable_tunnel` / `enable_remote_restart` / `enable_record_session` / `enable_block_input`
  - `allow_remote_config_modification` / `enable_remote_printer` / `enable_camera` / `enable_terminal`
- 其他选项（布尔）：
  - `disable_installation` / `disable_settings`
  - `enable_lan_discovery` / `direct_server`
  - `allow_auto_disconnect` / `allow_remove_wallpaper`
  - `disable_change_permanent_password` / `disable_change_id`

说明：

- 该工作流会克隆 RustDesk 指定版本源码并执行字段化定制，不需要你手改源码。
- 结果会推送到新仓库，后续你可以直接在新仓库继续维护。
- `update_check_api_url` 需返回 RustDesk 兼容 JSON：`{"url":"https://github.com/<owner>/<repo>/releases/tag/<version>"}`。

## 模板占位符

创建时会自动替换：

- `__PROJECT_NAME__`
- `__REPO_NAME__`
- `__OWNER__`
- `__NPM_PACKAGE_NAME__`

## Vue/Vite 模板内置工作流

- `.github/workflows/ci.yml`: push / PR 自动安装依赖并构建
- `.github/workflows/deploy-pages.yml`: push 到 `main` 自动发布到 GitHub Pages

使用 Pages 前，请在仓库 `Settings -> Pages` 中把 Source 设为 `GitHub Actions`。

## API 触发工厂工作流

```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer <GITHUB_TOKEN>" \
  https://api.github.com/repos/<owner>/<factory-repo>/actions/workflows/create-project.yml/dispatches \
  -d '{
    "ref": "main",
    "inputs": {
      "request_id": "web-req-001",
      "template_repo": "your-org/vue-vite-template",
      "template_ref": "main",
      "new_repo": "demo-vue-app",
      "project_name": "Demo Vue App",
      "visibility": "private",
      "default_branch": "main",
      "custom_replacements": "[{\"key\":\"__API_BASE__\",\"value\":\"https://api.demo.local\"}]"
    }
  }'
```
