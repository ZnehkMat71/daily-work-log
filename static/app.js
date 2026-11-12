document.addEventListener("DOMContentLoaded", function () {
    const databaseManagement = document.querySelector("[data-database-management]");
    if (databaseManagement) {
        const backupLink = databaseManagement.querySelector("[data-database-backup]");
        const backupFeedback = databaseManagement.querySelector(
            "[data-database-backup-feedback]"
        );
        const restoreForm = databaseManagement.querySelector("[data-database-restore]");
        const restoreFile = databaseManagement.querySelector("#backup_file");
        const selectedBackup = databaseManagement.querySelector("[data-selected-backup]");
        const restoreButton = restoreForm
            ? restoreForm.querySelector('button[type="submit"]')
            : null;

        if (backupLink) {
            backupLink.addEventListener("click", function (event) {
                if (backupLink.dataset.backupRequested === "true") {
                    event.preventDefault();
                    return;
                }

                backupLink.dataset.backupRequested = "true";
                backupLink.setAttribute("aria-disabled", "true");
                backupLink.setAttribute("aria-busy", "true");
                backupLink.textContent = "Preparing backup…";
                if (backupFeedback) {
                    backupFeedback.textContent =
                        "Backup requested. The download will begin once the snapshot is ready.";
                }

                window.setTimeout(function () {
                    delete backupLink.dataset.backupRequested;
                    backupLink.removeAttribute("aria-disabled");
                    backupLink.removeAttribute("aria-busy");
                    backupLink.textContent = "Download database backup";
                }, 2500);
            });
        }

        if (restoreFile && selectedBackup) {
            restoreFile.addEventListener("change", function () {
                const file = restoreFile.files && restoreFile.files[0];
                selectedBackup.textContent = file
                    ? `Selected backup: ${file.name}`
                    : "No backup file selected.";
            });
        }

        if (restoreForm && restoreButton) {
            restoreForm.addEventListener("submit", function (event) {
                if (event.defaultPrevented) {
                    return;
                }

                restoreButton.disabled = true;
                restoreButton.setAttribute("aria-busy", "true");
                restoreButton.textContent = "Restoring backup…";
            });
        }
    }

    const body = document.body;
    const sidebar = document.getElementById("app-sidebar");
    const mainContent = document.querySelector(".main-content");
    const collapseButton = document.querySelector("[data-sidebar-collapse]");
    const mobileMenuButton = document.querySelector("[data-mobile-menu-toggle]");
    const overlay = document.querySelector("[data-sidebar-overlay]");
    const mobileViewport = window.matchMedia("(max-width: 760px)");
    const collapsedStorageKey = "daily-work-log-sidebar-collapsed";

    if (!sidebar || !collapseButton || !mobileMenuButton || !overlay) {
        return;
    }

    let collapsed = false;
    try {
        collapsed = window.localStorage.getItem(collapsedStorageKey) === "true";
    } catch (error) {
        console.warn("Sidebar preference could not be loaded.", error);
    }

    function updateCollapseState() {
        body.classList.toggle("sidebar-collapsed", collapsed);
        collapseButton.setAttribute("aria-pressed", String(collapsed));
        collapseButton.setAttribute(
            "aria-label",
            collapsed ? "Expand sidebar" : "Collapse sidebar"
        );
        collapseButton.title = collapsed ? "Expand sidebar" : "Collapse sidebar";
    }

    function closeMobileNavigation(restoreFocus) {
        body.classList.remove("mobile-nav-open", "navigation-locked");
        overlay.hidden = true;
        sidebar.inert = true;
        sidebar.setAttribute("aria-hidden", "true");
        mainContent.inert = false;
        mobileMenuButton.setAttribute("aria-expanded", "false");
        mobileMenuButton.setAttribute("aria-label", "Open navigation");

        if (restoreFocus) {
            mobileMenuButton.focus();
        }
    }

    function openMobileNavigation() {
        body.classList.add("mobile-nav-open", "navigation-locked");
        overlay.hidden = false;
        sidebar.inert = false;
        sidebar.removeAttribute("aria-hidden");
        mainContent.inert = true;
        mobileMenuButton.setAttribute("aria-expanded", "true");
        mobileMenuButton.setAttribute("aria-label", "Close navigation");

        const activeLink = sidebar.querySelector(".nav-link.active");
        const firstLink = sidebar.querySelector(".nav-link");
        (activeLink || firstLink).focus();
    }

    function syncNavigationForViewport() {
        if (mobileViewport.matches) {
            if (!body.classList.contains("mobile-nav-open")) {
                closeMobileNavigation(false);
            }
            return;
        }

        body.classList.remove("mobile-nav-open", "navigation-locked");
        overlay.hidden = true;
        sidebar.inert = false;
        sidebar.removeAttribute("aria-hidden");
        mainContent.inert = false;
        mobileMenuButton.setAttribute("aria-expanded", "false");
        mobileMenuButton.setAttribute("aria-label", "Open navigation");
    }

    updateCollapseState();
    syncNavigationForViewport();

    collapseButton.addEventListener("click", function () {
        collapsed = !collapsed;
        updateCollapseState();
        try {
            window.localStorage.setItem(collapsedStorageKey, String(collapsed));
        } catch (error) {
            console.warn("Sidebar preference could not be saved.", error);
        }
    });

    mobileMenuButton.addEventListener("click", function () {
        if (body.classList.contains("mobile-nav-open")) {
            closeMobileNavigation(true);
        } else {
            openMobileNavigation();
        }
    });

    overlay.addEventListener("click", function () {
        closeMobileNavigation(true);
    });

    sidebar.querySelectorAll(".nav-link").forEach(function (link) {
        link.addEventListener("click", function () {
            if (mobileViewport.matches) {
                closeMobileNavigation(false);
            }
        });
    });

    document.addEventListener("keydown", function (event) {
        if (!body.classList.contains("mobile-nav-open")) {
            return;
        }

        if (event.key === "Escape") {
            closeMobileNavigation(true);
            return;
        }

        if (event.key === "Tab") {
            const focusableElements = Array.from(
                sidebar.querySelectorAll('a[href], button:not([disabled])')
            ).filter(function (element) {
                return element.getClientRects().length > 0;
            });
            const firstElement = focusableElements[0];
            const lastElement = focusableElements[focusableElements.length - 1];

            if (event.shiftKey && document.activeElement === firstElement) {
                event.preventDefault();
                lastElement.focus();
            } else if (!event.shiftKey && document.activeElement === lastElement) {
                event.preventDefault();
                firstElement.focus();
            }
        }
    });

    mobileViewport.addEventListener("change", syncNavigationForViewport);
});
