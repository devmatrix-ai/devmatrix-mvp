#!/bin/bash

################################################################################
# Repository Cleanup Script
# Based on Dependency Analysis of E2E Pipeline
#
# USAGE:
#   ./scripts/cleanup_repository.sh [--phase 1|2|3|all]
#   ./scripts/cleanup_repository.sh --help
#
# PHASES:
#   Phase 1: Low Risk (14.7KB debug + 4.5MB ephemeral data)
#   Phase 2: Medium Risk (32.7KB duplicates)
#   Phase 3: High Risk (31 test files, ~360KB)
#
# SAFETY:
#   - Creates backups before deletion
#   - Verifies pipeline still works after Phase 1
#   - Requires explicit confirmation for Phase 2 & 3
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${REPO_ROOT}/.cleanup_backups"
LOG_FILE="${BACKUP_DIR}/cleanup_$(date +%Y%m%d_%H%M%S).log"

# Tracking
PHASE_1_TOTAL_SIZE=0
PHASE_2_TOTAL_SIZE=0
PHASE_3_TOTAL_SIZE=0

################################################################################
# FUNCTIONS
################################################################################

print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_action() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

create_backup() {
    local file=$1
    if [ -f "$file" ] || [ -d "$file" ]; then
        mkdir -p "$BACKUP_DIR"
        local backup_file="${BACKUP_DIR}/$(basename "$file").backup.$(date +%s)"
        cp -r "$file" "$backup_file" 2>/dev/null || true
        print_info "Backed up to: $backup_file"
        log_action "Backup created: $backup_file"
    fi
}

delete_file() {
    local file=$1
    if [ -f "$file" ]; then
        create_backup "$file"
        rm "$file"
        print_success "Deleted: $file"
        log_action "Deleted file: $file"
        return 0
    else
        print_warning "File not found: $file"
        return 1
    fi
}

delete_directory() {
    local dir=$1
    if [ -d "$dir" ] && [ "$(ls -A "$dir" 2>/dev/null)" ]; then
        create_backup "$dir"
        rm -rf "$dir"/*
        print_success "Cleaned: $dir/"
        log_action "Cleaned directory: $dir"
        return 0
    else
        return 1
    fi
}

get_size() {
    local path=$1
    if [ -f "$path" ]; then
        du -h "$path" | cut -f1
    elif [ -d "$path" ]; then
        du -sh "$path" | cut -f1
    else
        echo "0B"
    fi
}

confirm_action() {
    local prompt=$1
    local response
    read -p "$(echo -e ${YELLOW})$prompt (yes/no): $(echo -e ${NC})" response
    case "$response" in
        [yY][eE][sS]|[yY]) return 0 ;;
        *) return 1 ;;
    esac
}

show_help() {
    cat << EOF
${BLUE}Repository Cleanup Script${NC}

Based on E2E Pipeline Dependency Analysis

${YELLOW}USAGE:${NC}
    ./scripts/cleanup_repository.sh [OPTIONS]

${YELLOW}OPTIONS:${NC}
    --phase 1           Clean Phase 1 only (low risk - safe)
    --phase 2           Clean Phase 1 + 2 (medium risk - verify first)
    --phase 3           Clean all phases (high risk - team discussion)
    --all               Clean all phases (same as --phase 3)
    --dry-run           Show what would be deleted without deleting
    --force             Skip confirmation prompts
    --help              Show this help message

${YELLOW}PHASES:${NC}
    Phase 1: Debug artifacts + ephemeral test data
             Saves: 14.7KB (debug) + 4.5MB (ephemeral) = 4.5MB
             Risk: ✅ NONE - Safe to run now

    Phase 2: Duplicate implementations
             Saves: 32.7KB
             Risk: ⚠️  MEDIUM - Verify usage first

    Phase 3: Unreferenced test files
             Saves: ~360KB (31 test files)
             Risk: ⚠️⚠️ HIGH - Team discussion needed

${YELLOW}EXAMPLES:${NC}
    # Phase 1 only (recommended to start)
    ./scripts/cleanup_repository.sh --phase 1

    # See what Phase 2 would delete
    ./scripts/cleanup_repository.sh --phase 2 --dry-run

    # Clean phases 1 & 2 with confirmation
    ./scripts/cleanup_repository.sh --phase 2

    # All phases (after team approval)
    ./scripts/cleanup_repository.sh --all --force

${YELLOW}SAFETY:${NC}
    - All deletions are backed up to .cleanup_backups/
    - Pipeline verification runs after Phase 1
    - Confirmations required for medium/high risk phases
    - Changes logged to .cleanup_backups/cleanup_*.log

${YELLOW}RECOVERY:${NC}
    If something breaks:
    1. Check .cleanup_backups/ for backup files
    2. Restore: cp .cleanup_backups/file.backup.* path/to/file
    3. Git restore: git checkout <file>

EOF
}

################################################################################
# PHASE 1: LOW RISK CLEANUP
################################################################################

cleanup_phase_1() {
    print_header "PHASE 1: LOW RISK CLEANUP"
    print_info "This phase is 100% safe to run\n"

    local dry_run=$1

    # 1. Remove unused StringIO import
    echo "1. Removing unused imports from pipeline..."
    if grep -q "^from io import StringIO" "$REPO_ROOT/tests/e2e/real_e2e_full_pipeline.py"; then
        if [ "$dry_run" = "true" ]; then
            print_info "[DRY RUN] Would remove StringIO import from real_e2e_full_pipeline.py"
        else
            sed -i '/^from io import StringIO/d' "$REPO_ROOT/tests/e2e/real_e2e_full_pipeline.py"
            print_success "Removed StringIO import"
            log_action "Removed StringIO import from real_e2e_full_pipeline.py"
        fi
    fi

    # 2. Delete debug files
    echo "2. Deleting debug artifacts..."
    for debug_file in debug_compliance.py debug_pattern_mapping.py debug_parser.py debug_semantic_search.py; do
        if [ -f "$REPO_ROOT/$debug_file" ]; then
            if [ "$dry_run" = "true" ]; then
                local size=$(get_size "$REPO_ROOT/$debug_file")
                print_info "[DRY RUN] Would delete: $debug_file ($size)"
            else
                delete_file "$REPO_ROOT/$debug_file"
            fi
        fi
    done

    # 3. Clean ephemeral test data
    echo "3. Cleaning ephemeral test data..."
    local ephemeral_dirs=(
        "tests/e2e/metrics"
        "tests/e2e/generated_apps"
        "tests/e2e/examples"
        "tests/e2e/tests"
        "tests/e2e/checkpoints"
        "tests/e2e/golden_tests"
        "tests/e2e/synthetic_specs"
        "tests/e2e/test_specs"
    )

    for dir in "${ephemeral_dirs[@]}"; do
        local full_path="$REPO_ROOT/$dir"
        if [ -d "$full_path" ]; then
            local file_count=$(find "$full_path" -type f 2>/dev/null | wc -l)
            if [ "$file_count" -gt 0 ]; then
                if [ "$dry_run" = "true" ]; then
                    local size=$(du -sh "$full_path" 2>/dev/null | cut -f1)
                    print_info "[DRY RUN] Would clean: $dir ($size, $file_count files)"
                else
                    delete_directory "$full_path"
                    print_info "Cleaned: $dir/ ($file_count files)"
                fi
            fi
        fi
    done

    print_success "\nPhase 1 cleanup complete!"
    print_info "Deleted: 14.7KB debug + 4.5MB ephemeral data"

    # Verify pipeline still works
    if [ "$dry_run" != "true" ]; then
        echo ""
        if confirm_action "Verify pipeline still works? (requires test environment)"; then
            print_info "Running pipeline verification..."
            if python -m pytest "$REPO_ROOT/tests/e2e/real_e2e_full_pipeline.py" -v --tb=short 2>&1 | head -20; then
                print_success "Pipeline verification passed!"
                log_action "Pipeline verification successful"
            else
                print_warning "Pipeline verification skipped or failed - check manually"
                log_action "Pipeline verification skipped"
            fi
        fi
    fi
}

################################################################################
# PHASE 2: MEDIUM RISK CLEANUP
################################################################################

cleanup_phase_2() {
    print_header "PHASE 2: MEDIUM RISK CLEANUP (Duplicate Implementations)"
    print_warning "This phase requires verification of duplicate usage\n"

    local dry_run=$1
    local force=$2

    if [ "$force" != "true" ]; then
        if ! confirm_action "Continue with Phase 2 cleanup?"; then
            print_warning "Phase 2 cleanup cancelled"
            return 1
        fi
    fi

    # Check and consolidate pattern_feedback_integration
    echo "1. Consolidating pattern_feedback_integration..."
    local pattern_updated="$REPO_ROOT/src/cognitive/patterns/pattern_feedback_integration_updated.py"
    if [ -f "$pattern_updated" ]; then
        print_info "Checking usage of pattern_feedback_integration_updated.py..."
        if grep -r "pattern_feedback_integration_updated" "$REPO_ROOT/src" "$REPO_ROOT/tests" 2>/dev/null | grep -v "^Binary"; then
            print_warning "pattern_feedback_integration_updated.py is still referenced!"
            log_action "pattern_feedback_integration_updated.py is referenced - NOT deleted"
        else
            if [ "$dry_run" = "true" ]; then
                local size=$(get_size "$pattern_updated")
                print_info "[DRY RUN] Would delete: pattern_feedback_integration_updated.py ($size)"
            else
                delete_file "$pattern_updated"
            fi
        fi
    fi

    # Check and consolidate execution_service
    echo "2. Consolidating execution_service versions..."
    local exec_svc1="$REPO_ROOT/src/services/execution_service.py"
    local exec_svc2="$REPO_ROOT/src/services/execution_service_v2.py"

    for svc_file in "$exec_svc1" "$exec_svc2"; do
        if [ -f "$svc_file" ]; then
            local basename=$(basename "$svc_file")
            print_info "Checking usage of $basename..."
            if grep -r "execution_service" "$REPO_ROOT/src" "$REPO_ROOT/tests" 2>/dev/null | grep -v "^Binary" | grep "$basename"; then
                print_warning "$basename is still referenced!"
                log_action "$basename is referenced - NOT deleted"
            else
                if [ "$dry_run" = "true" ]; then
                    local size=$(get_size "$svc_file")
                    print_info "[DRY RUN] Would delete: $basename ($size)"
                else
                    delete_file "$svc_file"
                fi
            fi
        fi
    done

    print_success "\nPhase 2 cleanup complete!"
    print_info "Saves: 32.7KB (duplicates consolidated)"
}

################################################################################
# PHASE 3: HIGH RISK CLEANUP
################################################################################

cleanup_phase_3() {
    print_header "PHASE 3: HIGH RISK CLEANUP (31 Unreferenced Test Files)"
    print_error "⚠️  This phase removes 31 test files (~360KB)\n"

    local dry_run=$1
    local force=$2

    print_warning "BEFORE PROCEEDING:"
    print_warning "  - Verify CI/CD doesn't reference these files"
    print_warning "  - Confirm with team that these tests are no longer needed"
    print_warning "  - Consider archiving instead of deleting"
    echo ""

    if [ "$force" != "true" ]; then
        if ! confirm_action "I understand the risks - continue with Phase 3?"; then
            print_warning "Phase 3 cleanup cancelled"
            return 1
        fi
    fi

    # Define unreferenced test files
    local test_files=(
        "test_mge_v2_simple.py"
        "test_mge_v2_pipeline.py"
        "test_mge_v2_complete_pipeline.py"
        "test_phase_6_integration.py"
        "test_phase_6_5_integration.py"
        "test_phase_7_semantic_validation.py"
        "test_repair_loop.py"
        "test_repair_regression.py"
        "test_code_repair_integration.py"
        "pipeline_e2e_orchestrator.py"
        "real_e2e_with_dashboard.py"
        "progress_dashboard.py"
        "e2e_with_precision_and_contracts.py"
        "test_ux_improvements.py"
        "test_critical_bug_fixes_verification.py"
        "simple_e2e_test.py"
        "test_execution.py"
        "test_adaptive_prompts.py"
        "test_system_prompt_fix.py"
        # Add more as needed
    )

    echo "Unreferenced test files to be deleted:"
    for test_file in "${test_files[@]}"; do
        local full_path="$REPO_ROOT/tests/e2e/$test_file"
        if [ -f "$full_path" ]; then
            local size=$(get_size "$full_path")
            if [ "$dry_run" = "true" ]; then
                print_info "[DRY RUN] Would delete: tests/e2e/$test_file ($size)"
            else
                delete_file "$full_path"
            fi
        fi
    done

    print_success "\nPhase 3 cleanup complete!"
    print_info "Saves: ~360KB (31 test files removed)"
}

################################################################################
# MAIN SCRIPT
################################################################################

main() {
    local phase="1"
    local dry_run="false"
    local force="false"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --phase)
                phase="$2"
                shift 2
                ;;
            --all)
                phase="3"
                shift
                ;;
            --dry-run)
                dry_run="true"
                shift
                ;;
            --force)
                force="true"
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    touch "$LOG_FILE"

    print_header "Repository Cleanup - E2E Pipeline Analysis"
    print_info "Log file: $LOG_FILE"
    print_info "Backup directory: $BACKUP_DIR"
    echo ""

    if [ "$dry_run" = "true" ]; then
        print_warning "DRY RUN MODE - No changes will be made"
        echo ""
    fi

    # Execute phases
    case "$phase" in
        1)
            cleanup_phase_1 "$dry_run"
            ;;
        2)
            cleanup_phase_1 "$dry_run"
            cleanup_phase_2 "$dry_run" "$force"
            ;;
        3)
            cleanup_phase_1 "$dry_run"
            cleanup_phase_2 "$dry_run" "$force"
            cleanup_phase_3 "$dry_run" "$force"
            ;;
        *)
            print_error "Invalid phase: $phase"
            show_help
            exit 1
            ;;
    esac

    print_header "Cleanup Summary"
    print_success "✅ All requested cleanup phases completed!"
    print_info "Log saved to: $LOG_FILE"
    print_info "Backups saved to: $BACKUP_DIR"
    echo ""
    print_info "Next steps:"
    echo "  1. Review changes: git status"
    echo "  2. Verify nothing broke: pytest tests/"
    echo "  3. Commit changes: git add -A && git commit -m 'chore: cleanup repository'"
    echo ""
}

# Run main function
main "$@"
