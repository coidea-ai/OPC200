#!/usr/bin/env bash
# Bootstrap: 从 GitHub Release 下载 opc200-agent-<ver>.zip + SHA256SUMS，校验后解压并执行 install.sh。
# 环境变量: OPC200_INSTALL_VERSION / OPC200_GITHUB_REPO / GITHUB_TOKEN（可选）
set -euo pipefail

E004=4

# 避免网络差时长时间无输出；需进度条时可设 OPC200_CURL_PROGRESS=1
_curl() {
    if [[ "${OPC200_CURL_PROGRESS:-}" == "1" ]]; then
        curl --connect-timeout 30 --max-time 600 --retry 2 -fSL "$@"
    else
        curl --connect-timeout 30 --max-time 600 --retry 2 -fsSL "$@"
    fi
}

err() { printf '%s\n' "opc200-install: $*" >&2; }

usage() {
    cat <<'EOF'
用法: opc200-install.sh [bootstrap 选项] [install.sh 透传参数...]

Bootstrap:
  --version <semver|latest>   默认: \$OPC200_INSTALL_VERSION 或 latest
  --github-repo <owner/repo>  默认: \$OPC200_GITHUB_REPO（须设置其一）
  --extract-parent <DIR>      解压根目录；默认 \$HOME/.opc200/agent-bundle/<ver>
  --download-only             仅下载并校验，不执行 install.sh
  -h, --help

示例:
  OPC200_GITHUB_REPO=org/OPC200 ./opc200-install.sh --silent --opc200-tenant-id t1 --opc200-api-key k
EOF
}

# latest：一行 TSV（tag / sem / zip 名 / zip URL）
parse_latest_release_tsv() {
    python3 -c '
import json, sys
def fail(m):
    print(m, file=sys.stderr)
    raise SystemExit(1)
try:
    raw = sys.stdin.read()
    if not raw.strip():
        fail("GitHub API 返回空内容")
    j = json.loads(raw)
except json.JSONDecodeError as e:
    fail("GitHub API 非 JSON: %s" % e)
if not isinstance(j, dict):
    fail("GitHub API 根类型异常")
msg = j.get("message")
if msg and not j.get("tag_name"):
    if "rate limit" in msg.lower():
        print("提示: 可设置环境变量 GITHUB_TOKEN（只读即可）解除 REST API 匿名限额", file=sys.stderr)
    fail("GitHub API: %s" % msg)
tag = j.get("tag_name") or ""
if not tag.startswith("v"):
    fail("tag_name 异常: %r（需要 vX.Y.Z）；若为 API 错误页请检查网络或 GITHUB_TOKEN" % tag)
sem = tag[1:]
zip_name = "opc200-agent-%s.zip" % (sem,)
url = ""
for a in j.get("assets") or []:
    if (a.get("name") or "") == zip_name:
        url = a.get("browser_download_url") or ""
        break
if not url:
    names = [a.get("name") for a in (j.get("assets") or [])]
    fail("Release 中无制品 %s；当前 assets: %s" % (zip_name, names))
sys.stdout.write("\t".join([tag, sem, zip_name, url]))
'
}

resolve_urls() {
    local ver="$1" repo="$2"
    local base="https://github.com/${repo}"
    local api="https://api.github.com/repos/${repo}"
    local hdr=(-H "Accept: application/vnd.github+json" -H "User-Agent: opc200-bootstrap" -H "X-GitHub-Api-Version: 2022-11-28")
    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        hdr+=(-H "Authorization: Bearer ${GITHUB_TOKEN}")
    fi

    if [[ -z "$ver" || "$ver" == "latest" ]]; then
        local js
        printf '%s\n' "opc200-install: 正在查询 GitHub Release（latest）…" >&2
        js="$(_curl "${hdr[@]}" "${api}/releases/latest")" || {
            err "无法获取 releases/latest"
            exit "$E004"
        }
        local tsv
        if ! tsv="$(printf '%s' "$js" | parse_latest_release_tsv)"; then
            err "解析 latest Release 或 zip 资源失败（见上方说明；匿名 GitHub API 易触发 rate limit，可 export GITHUB_TOKEN 后重试，或改用 --version 2.5.2）"
            exit "$E004"
        fi
        IFS=$'\t' read -r TAG SEM ZIP_NAME ZIP_URL <<< "$tsv"
        SUMS_URL="${base}/releases/download/${TAG}/SHA256SUMS"
        return 0
    fi

    SEM="$ver"
    TAG="v${ver}"
    ZIP_NAME="opc200-agent-${ver}.zip"
    ZIP_URL="${base}/releases/download/${TAG}/${ZIP_NAME}"
    SUMS_URL="${base}/releases/download/${TAG}/SHA256SUMS"
}

verify_sha256sums() {
    local sums_path="$1" zip_path="$2" zip_name="$3"
    local expected actual
    expected="$(awk -v z="$zip_name" '
      $1 ~ /^[A-Fa-f0-9]{64}$/ {
        fn=$NF
        sub(/^\*/, "", fn)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", fn)
        if (fn == z) { print tolower($1); exit }
      }' "$sums_path")"

    [[ -n "$expected" ]] || {
        err "SHA256SUMS: 无条目 $zip_name"
        exit "$E004"
    }

    if command -v sha256sum &>/dev/null; then
        actual="$(sha256sum -b "$zip_path" 2>/dev/null | awk '{print $1}' | tr '[:upper:]' '[:lower:]')"
    elif command -v shasum &>/dev/null; then
        actual="$(shasum -a 256 "$zip_path" | awk '{print $1}' | tr '[:upper:]' '[:lower:]')"
    else
        err "需要 sha256sum 或 shasum"
        exit "$E004"
    fi

    [[ "$actual" == "$expected" ]] || {
        err "SHA256 不匹配: $zip_name (期望 $expected, 实际 $actual)"
        exit "$E004"
    }
}

# 优先 unzip；无则使用 python3（与脚本其余部分一致，避免最小化系统未装 unzip）
extract_zip() {
    local zip_path="$1" dest="$2"
    if command -v unzip &>/dev/null; then
        unzip -oq "$zip_path" -d "$dest"
        return
    fi
    python3 -c '
import sys, zipfile
zp, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(zp, "r") as z:
    z.extractall(out)
' "$zip_path" "$dest"
}

VERSION="${OPC200_INSTALL_VERSION:-}"
REPO="${OPC200_GITHUB_REPO:-}"
EXTRACT_PARENT=""
DOWNLOAD_ONLY=0
PASS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --version)
            VERSION="$2"
            shift 2
            ;;
        --github-repo)
            REPO="$2"
            shift 2
            ;;
        --extract-parent)
            EXTRACT_PARENT="$2"
            shift 2
            ;;
        --download-only)
            DOWNLOAD_ONLY=1
            shift
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            PASS+=("$1")
            shift
            ;;
    esac
done

# 引号内的 "~/foo" 不会经 shell 展开，这里补展开为 $HOME/foo
if [[ -n "${EXTRACT_PARENT:-}" ]]; then
    if [[ "$EXTRACT_PARENT" == "~" ]]; then
        EXTRACT_PARENT="$HOME"
    elif [[ "$EXTRACT_PARENT" == "~/"* ]]; then
        EXTRACT_PARENT="${HOME}/${EXTRACT_PARENT:2}"
    fi
fi

[[ -n "$VERSION" ]] || VERSION="latest"
[[ -n "$REPO" ]] || {
    err "请设置 --github-repo 或环境变量 OPC200_GITHUB_REPO (owner/repo)"
    exit "$E004"
}
if [[ ! "$REPO" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
    err "无效的 GitHub repo: $REPO"
    exit "$E004"
fi

command -v python3 &>/dev/null || {
    err "需要 python3（用于解析 GitHub API JSON）"
    exit "$E004"
}
command -v curl &>/dev/null || {
    err "需要 curl"
    exit "$E004"
}

TAG=""
SEM=""
ZIP_NAME=""
ZIP_URL=""
SUMS_URL=""

resolve_urls "$VERSION" "$REPO"

if [[ -n "$EXTRACT_PARENT" ]]; then
    DEST_ROOT="$EXTRACT_PARENT"
else
    DEST_ROOT="${HOME}/.opc200/agent-bundle/${SEM}"
fi
mkdir -p "$DEST_ROOT"

printf '%s\n' "opc200-install: 将使用版本 ${SEM:-?}，解压根目录: ${DEST_ROOT}" >&2

SUMS_PATH="${DEST_ROOT}/SHA256SUMS"
ZIP_PATH="${DEST_ROOT}/${ZIP_NAME}"

printf '%s\n' "opc200-install: 正在下载 SHA256SUMS …" >&2
_curl -o "$SUMS_PATH" "$SUMS_URL" || {
    err "下载 SHA256SUMS 失败"
    exit "$E004"
}
printf '%s\n' "opc200-install: 正在下载 ${ZIP_NAME} …" >&2
_curl -L -o "$ZIP_PATH" "$ZIP_URL" || {
    err "下载 $ZIP_NAME 失败"
    exit "$E004"
}

verify_sha256sums "$SUMS_PATH" "$ZIP_PATH" "$ZIP_NAME"

AGENT_DIR="${DEST_ROOT}/agent"
if [[ -d "$AGENT_DIR" ]]; then
    rm -rf "$AGENT_DIR"
fi
extract_zip "$ZIP_PATH" "$DEST_ROOT"

INSTALL_SH="${DEST_ROOT}/agent/scripts/install.sh"
if [[ ! -f "$INSTALL_SH" ]]; then
    err "未找到 ${INSTALL_SH}（制品包应含 agent/scripts/install.sh）"
    exit "$E004"
fi
chmod +x "$INSTALL_SH" 2>/dev/null || true

if [[ "$DOWNLOAD_ONLY" -eq 1 ]]; then
    printf '%s\n' "Download OK; RepoRoot=${DEST_ROOT}"
    exit 0
fi

if [[ "$(uname -s | tr '[:upper:]' '[:lower:]')" == "linux" ]] && [[ $EUID -ne 0 ]]; then
    printf '%s\n' "opc200-install: 即将执行第二阶段 install.sh（可能需要输入 sudo 密码）…" >&2
    exec sudo -E "$INSTALL_SH" --repo-root "$DEST_ROOT" "${PASS[@]}"
else
    printf '%s\n' "opc200-install: 即将执行第二阶段 install.sh …" >&2
    exec "$INSTALL_SH" --repo-root "$DEST_ROOT" "${PASS[@]}"
fi
