# Known Issues

This document tracks known issues and limitations in the FDA CRL Explorer.

## UI/UX Issues

### Multi-Select Dropdown Focus Loss
**Status:** Open
**Priority:** Low
**Component:** `frontend/src/components/MultiSelectDropdown.jsx`

**Description:**
When clicking on checkboxes within multi-select dropdowns, the dropdown loses focus and closes, requiring users to reopen it for each selection.

**Attempted Fixes:**
- Added `event.stopPropagation()` to prevent event bubbling
- Changed from `<label>` to `<div>` with `onMouseDown` handler
- Added `e.preventDefault()` and made checkbox `pointer-events-none`

**Workaround:**
Users can use the "Select All" and "Select None" buttons, or use the search functionality to narrow down options before selecting.

**Next Steps:**
May require deeper investigation into React state updates and dropdown component lifecycle. Consider using a third-party multi-select library if this becomes a significant UX issue.

---

## Future Enhancements

(Add future enhancement ideas here)
