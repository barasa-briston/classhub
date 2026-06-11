// Bulk Actions Handler for Admin Dashboard
// Manages checkbox selection and bulk operations

class BulkActionsHandler {
    constructor(formId, checkboxClass, selectAllId) {
        this.form = document.getElementById(formId);
        this.checkboxes = document.querySelectorAll(`.${checkboxClass}`);
        this.selectAll = document.getElementById(selectAllId);
        this.selectedCount = 0;

        this.init();
    }

    init() {
        if (!this.form) return;

        // Select All functionality
        if (this.selectAll) {
            this.selectAll.addEventListener('change', (e) => {
                this.checkboxes.forEach(cb => {
                    cb.checked = e.target.checked;
                });
                this.updateSelectedCount();
            });
        }

        // Individual checkbox listeners
        this.checkboxes.forEach(cb => {
            cb.addEventListener('change', () => {
                this.updateSelectedCount();
                this.updateSelectAllState();
            });
        });

        this.updateSelectedCount();
    }

    updateSelectedCount() {
        this.selectedCount = Array.from(this.checkboxes).filter(cb => cb.checked).length;

        // Update UI to show count
        const countElements = document.querySelectorAll('.bulk-selected-count');
        countElements.forEach(el => {
            el.textContent = this.selectedCount;
        });

        // Enable/disable bulk action buttons
        const bulkButtons = document.querySelectorAll('.bulk-action-btn');
        bulkButtons.forEach(btn => {
            btn.disabled = this.selectedCount === 0;
            if (this.selectedCount === 0) {
                btn.classList.add('opacity-50', 'cursor-not-allowed');
            } else {
                btn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        });
    }

    updateSelectAllState() {
        if (!this.selectAll) return;

        const allChecked = Array.from(this.checkboxes).every(cb => cb.checked);
        const someChecked = Array.from(this.checkboxes).some(cb => cb.checked);

        this.selectAll.checked = allChecked;
        this.selectAll.indeterminate = someChecked && !allChecked;
    }

    getSelectedIds() {
        return Array.from(this.checkboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);
    }
}

// Initialize bulk actions when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    // Initialize for assignments
    if (document.getElementById('bulk-assignments-form')) {
        window.assignmentsBulkHandler = new BulkActionsHandler(
            'bulk-assignments-form',
            'assignment-checkbox',
            'select-all-assignments'
        );
    }

    // Initialize for grades
    if (document.getElementById('bulk-grades-form')) {
        window.gradesBulkHandler = new BulkActionsHandler(
            'bulk-grades-form',
            'grade-checkbox',
            'select-all-grades'
        );
    }
});

// Bulk action confirmation
function confirmBulkAction(action, count) {
    const messages = {
        'approve-assignments': `Are you sure you want to approve ${count} assignment(s)?`,
        'reject-assignments': `Are you sure you want to reject ${count} assignment(s)?`,
        'approve-grades': `Are you sure you want to lock ${count} grade(s)?`
    };

    return confirm(messages[action] || 'Are you sure?');
}

// Handle bulk reject with reason
function showBulkRejectForm() {
    const form = document.getElementById('bulk-reject-form');
    if (form) {
        form.classList.toggle('hidden');
    }
}
