#!/bin/bash
# ============================================================
# sync-to-local.sh — 增量同步开发目录到本地已安装的 skill
# ============================================================
#
# 功能：
#   1. 只复制有变化的文件（比较内容哈希），跳过未修改文件
#   2. 保护用户数据目录（memory/, styles/, learning/samples/），升级时不覆盖
#   3. 支持首次安装（目标不存在时全量复制）和后续增量升级
#
# 用法：
#   bash scripts/sync-to-local.sh              # 使用默认路径
#   bash scripts/sync-to-local.sh [目标路径]    # 指定目标路径
# ============================================================

# ---- 颜色 ----
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; RED='\033[0;31m'; NC='\033[0m'
log_info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ---- 路径 ----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET_DIR="${1:-$HOME/.claude/skills/wechat-writer}"

# ---- 受保护目录 ----
is_protected() {
    case "$1" in
        memory/*|memory|styles/*|styles|learning/samples/*|learning/samples) return 0 ;;
        *) return 1 ;;
    esac
}

# ---- 跳过的目录 ----
is_skipped() {
    case "$1" in
        .git/*|.git|outputs/*|outputs) return 0 ;;
        *) return 1 ;;
    esac
}

file_hash() { md5sum "$1" 2>/dev/null | cut -d' ' -f1; }

# ---- 主流程 ----
echo ""
echo "======================================"
echo "  wechat-writer skill 增量同步工具"
echo "======================================"
echo ""
log_info "源目录：$SOURCE_DIR"
log_info "目标目录：$TARGET_DIR"
echo ""

if [ ! -f "$SOURCE_DIR/SKILL.md" ]; then
    log_err "源目录无效（找不到 SKILL.md）"
    exit 1
fi

FIRST_INSTALL=false
if [ ! -d "$TARGET_DIR" ]; then
    FIRST_INSTALL=true
    log_warn "目标目录不存在，执行首次全量安装"
    mkdir -p "$TARGET_DIR"
fi

# ---- 同步：源 → 目标 ----
log_info "扫描文件..."
echo ""

TMPLIST=$(mktemp)
find "$SOURCE_DIR" -type f > "$TMPLIST"

COPIED=0; SKIPPED_SAME=0; SKIPPED_PROT=0

while IFS= read -r src_file; do
    rel_path="${src_file#$SOURCE_DIR/}"
    is_skipped "$rel_path" && continue

    if [ "$FIRST_INSTALL" = "false" ] && is_protected "$rel_path"; then
        SKIPPED_PROT=$((SKIPPED_PROT + 1))
        continue
    fi

    target_file="$TARGET_DIR/$rel_path"
    mkdir -p "$(dirname "$target_file")"

    if [ -f "$target_file" ]; then
        if [ "$(file_hash "$src_file")" = "$(file_hash "$target_file")" ]; then
            SKIPPED_SAME=$((SKIPPED_SAME + 1))
            continue
        fi
    fi

    cp "$src_file" "$target_file"
    log_ok "已更新: $rel_path"
    COPIED=$((COPIED + 1))
done < "$TMPLIST"

# ---- 清理：目标中源已删除的文件 ----
DELETED=0
if [ "$FIRST_INSTALL" = "false" ] && [ -d "$TARGET_DIR" ]; then
    find "$TARGET_DIR" -type f > "$TMPLIST"
    while IFS= read -r tgt_file; do
        rel_path="${tgt_file#$TARGET_DIR/}"
        is_skipped "$rel_path" && continue
        is_protected "$rel_path" && continue

        if [ ! -f "$SOURCE_DIR/$rel_path" ]; then
            rm "$tgt_file"
            log_warn "已删除: $rel_path"
            DELETED=$((DELETED + 1))
        fi
    done < "$TMPLIST"
fi

rm -f "$TMPLIST"

# ---- 首次安装时确保数据目录存在 ----
if [ "$FIRST_INSTALL" = "true" ]; then
    for d in memory styles learning/samples; do
        mkdir -p "$TARGET_DIR/$d"
    done
fi

# ---- 报告 ----
echo ""
echo "======================================"
echo "  同步完成"
echo "======================================"
echo ""
[ "$FIRST_INSTALL" = "true" ] && log_info "模式：首次全量安装" || log_info "模式：增量更新"
log_info "已更新：$COPIED 个文件"
log_info "未修改跳过：$SKIPPED_SAME"
[ "$FIRST_INSTALL" = "false" ] && log_info "受保护跳过：$SKIPPED_PROT（memory/ styles/ learning/samples/）"
[ "$FIRST_INSTALL" = "false" ] && log_info "已清理：$DELETED"
echo ""
[ "$COPIED" -eq 0 ] && log_ok "所有文件已是最新" || log_ok "同步完成！共更新 $COPIED 个文件"
echo ""
